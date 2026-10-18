// OMORI resource adapter for the proven native VN Revival Windows installer shell.
// Native helper avoids requiring a PowerShell engine inside CrossOver.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <bcrypt.h>
#include <tlhelp32.h>
#include <filesystem>
#include <fstream>
#include <vector>
#include <set>
#include <iostream>
#include <zlib.h>
#include "../vendor/json.hpp"
using json=nlohmann::json;namespace fs=std::filesystem;
using Bytes=std::vector<unsigned char>;
static void require(bool condition,const std::string& message){if(!condition)throw std::runtime_error(message);}
static Bytes read(const fs::path& p){std::ifstream f(p,std::ios::binary);require(bool(f),"Could not read "+p.u8string());return Bytes(std::istreambuf_iterator<char>(f),{});}
static void checkHash(const std::string& h){require(h.size()==64 && h.find_first_not_of("0123456789abcdef")==std::string::npos,"Invalid checksum");}
static std::string hashBytes(const Bytes& b){
 BCRYPT_ALG_HANDLE alg=nullptr;BCRYPT_HASH_HANDLE hash=nullptr;unsigned char result[32];
 require(BCryptOpenAlgorithmProvider(&alg,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0,"SHA256 unavailable");
 auto status=BCryptCreateHash(alg,&hash,nullptr,0,nullptr,0,0);
 if(status>=0)status=BCryptHashData(hash,const_cast<unsigned char*>(b.data()),static_cast<ULONG>(b.size()),0);
 if(status>=0)status=BCryptFinishHash(hash,result,32,0);
 if(hash)BCryptDestroyHash(hash);BCryptCloseAlgorithmProvider(alg,0);require(status>=0,"SHA256 failed");
 static const char digits[]="0123456789abcdef";std::string s;for(auto c:result){s+=digits[c>>4];s+=digits[c&15];}return s;
}
static std::string hashFile(const fs::path& p){if(!fs::exists(p))return "-";require(fs::is_regular_file(p),"File path is occupied by a folder");return hashBytes(read(p));}
static void checkPath(const fs::path& p,const fs::path& root){
 auto full=fs::absolute(p).lexically_normal();auto base=fs::absolute(root).lexically_normal();auto relative=full.lexically_relative(base);
 require(full==base || (!relative.empty() && *relative.begin()!=L".."),"Path leaves game folder");
 for(auto cursor=full;!cursor.empty();){if(cursor==cursor.root_path())break;DWORD a=GetFileAttributesW(cursor.c_str());require(a==INVALID_FILE_ATTRIBUTES || !(a&FILE_ATTRIBUTE_REPARSE_POINT),"A link blocks safe installation: "+cursor.u8string());auto parent=cursor.parent_path();if(parent==cursor)break;cursor=parent;}
}
static void relativePath(const std::string& s){
 require(!s.empty() && s.find_first_of("\\:\0",0,3)==std::string::npos,"Unsafe package path");
 require(s=="index.html" || s.rfind("data/",0)==0 || s.rfind("js/",0)==0 || s.rfind("fonts/",0)==0 || s.rfind("languages/en/",0)==0,"Unsafe game resource path");
 size_t start=0;while(true){auto end=s.find('/',start);auto part=s.substr(start,end==std::string::npos?end:end-start);require(!part.empty()&&part!="."&&part!="..","Unsafe path segment");if(end==std::string::npos)break;start=end+1;}
}
static void atomicWrite(const fs::path& p,const Bytes& bytes){
 fs::create_directories(p.parent_path());auto temp=p;temp+=L".vnrevival-new-"+std::to_wstring(GetCurrentProcessId())+L"-"+std::to_wstring(GetTickCount64());
 HANDLE h=CreateFileW(temp.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);require(h!=INVALID_HANDLE_VALUE,"Could not create staged file");
 DWORD written=0;bool ok=WriteFile(h,bytes.data(),static_cast<DWORD>(bytes.size()),&written,nullptr)&&written==bytes.size()&&FlushFileBuffers(h);CloseHandle(h);
 if(!ok){DeleteFileW(temp.c_str());throw std::runtime_error("Could not write staged file");}
 if(!MoveFileExW(temp.c_str(),p.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)){DeleteFileW(temp.c_str());throw std::runtime_error("Could not replace file; close the game and retry");}
}
static json load(const fs::path& p){auto raw=read(p);return json::parse(raw);}
static void save(const fs::path& p,const json& j){auto s=j.dump();atomicWrite(p,Bytes(s.begin(),s.end()));}
static void status(const fs::path& p,const std::string& s){if(!p.empty())atomicWrite(p,Bytes(s.begin(),s.end()));}
static Bytes unbase64(const std::string& s){
 static const std::string chars="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";Bytes out;unsigned int val=0;int bits=-8;
 for(unsigned char c:s){if(c=='=')break;auto at=chars.find(c);require(at!=std::string::npos,"Invalid IV encoding");val=(val<<6)|static_cast<int>(at);bits+=6;if(bits>=0){out.push_back(static_cast<unsigned char>((val>>bits)&255));bits-=8;}}return out;
}
static Bytes unpack(const Bytes& z,size_t length){
 require(length<=64*1024*1024,"Object too large");Bytes b(length?length:1);z_stream s{};s.next_in=const_cast<Bytef*>(z.data());s.avail_in=static_cast<uInt>(z.size());s.next_out=b.data();s.avail_out=static_cast<uInt>(b.size());
 require(inflateInit2(&s,31)==Z_OK,"Cannot initialize decompression");int r=inflate(&s,Z_FINISH);bool ok=r==Z_STREAM_END&&s.total_out==length&&s.avail_in==0;inflateEnd(&s);require(ok,"Object decompression failed");b.resize(length);return b;
}
static Bytes encode(const Bytes& plain,const Bytes& iv){
 if(iv.empty())return plain;require(iv.size()==16,"Invalid native IV");
 BCRYPT_ALG_HANDLE alg=nullptr;BCRYPT_KEY_HANDLE key=nullptr;const char nativeKey[]="6bdb2e585882fbd48826ef9cffd4c511";
 require(BCryptOpenAlgorithmProvider(&alg,BCRYPT_AES_ALGORITHM,nullptr,0)>=0,"AES unavailable");
 auto r=BCryptSetProperty(alg,BCRYPT_CHAINING_MODE,reinterpret_cast<PUCHAR>(const_cast<wchar_t*>(BCRYPT_CHAIN_MODE_ECB)),sizeof(BCRYPT_CHAIN_MODE_ECB),0);
 if(r>=0)r=BCryptGenerateSymmetricKey(alg,&key,nullptr,0,reinterpret_cast<PUCHAR>(const_cast<char*>(nativeKey)),32,0);
 size_t size=((plain.size()+15)/16)*16;Bytes counters(size),stream(size),counter=iv;
 for(size_t p=0;p<size;p+=16){std::copy(counter.begin(),counter.end(),counters.begin()+p);for(int i=15;i>=0;i--){counter[i]++;if(counter[i])break;}}
 ULONG done=0;if(r>=0&&size)r=BCryptEncrypt(key,counters.data(),static_cast<ULONG>(size),nullptr,nullptr,0,stream.data(),static_cast<ULONG>(size),&done,0);
 if(key)BCryptDestroyKey(key);BCryptCloseAlgorithmProvider(alg,0);require(r>=0 && done==size,"Native encryption failed");
 Bytes output=iv;for(size_t i=0;i<plain.size();i++)output.push_back(plain[i]^stream[i]);return output;
}
static std::string putBlob(const fs::path& store,const Bytes& b){auto h=hashBytes(b);auto p=store/fs::u8path(h);checkPath(p,store);if(fs::exists(p))require(hashFile(p)==h,"A recovery backup is damaged");else atomicWrite(p,b);return h;}
static Bytes blob(const fs::path& store,const std::string& h){checkHash(h);auto p=store/fs::u8path(h);checkPath(p,store);auto b=read(p);require(hashBytes(b)==h,"A recovery backup is damaged");return b;}
static void setFile(const fs::path& p,const std::string& h,const fs::path& store){if(h=="-"){if(fs::exists(p))fs::remove(p);}else{atomicWrite(p,blob(store,h));require(hashFile(p)==h,"Installed file readback failed");}}
static void assertClosed(){
 HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);require(snapshot!=INVALID_HANDLE_VALUE,"Could not check running games");PROCESSENTRY32W e{};e.dwSize=sizeof(e);bool running=false;
 if(Process32FirstW(snapshot,&e))do{if(_wcsicmp(e.szExeFile,L"OMORI.exe")==0)running=true;}while(Process32NextW(snapshot,&e));CloseHandle(snapshot);require(!running,"Close OMORI before installing or changing the language.");
}
static void validateState(const json& s,const fs::path& root){
 require(s.at("schemaVersion")==1 && s.at("gameRoot")==root.u8string() && s.at("runtimeCode")=="en","Install record belongs to another game folder");
 for(auto i=s.at("originals").begin();i!=s.at("originals").end();++i){relativePath(i.key());if(i.value()!="-")checkHash(i.value());}
 for(auto i=s.at("owned").begin();i!=s.at("owned").end();++i){relativePath(i.key());checkHash(i.value());require(s.at("originals").contains(i.key()),"Invalid ownership record");}
}
static void recover(const fs::path& journal,const fs::path& root,const fs::path& store,const fs::path& state){
 if(!fs::exists(journal))return;auto j=load(journal);require(j.at("schemaVersion")==1&&j.at("gameRoot")==root.u8string(),"Invalid recovery journal");if(!j.at("previous").is_null())validateState(j["previous"],root);std::set<std::string> seen;
 for(auto& o:j.at("operations")){std::string p=o.at("path"),before=o.at("before"),after=o.at("after");relativePath(p);require(seen.insert(p).second,"Duplicate recovery path");if(before!="-")checkHash(before);if(after!="-")checkHash(after);auto target=root/fs::u8path(p);checkPath(target,root);auto current=hashFile(target);require(current==before||current==after,p+" changed after interrupted installation. Your file was preserved.");if(before!="-")blob(store,before);}
 for(auto& o:j["operations"])setFile(root/fs::u8path(o.at("path").get<std::string>()),o.at("before"),store);
 if(j["previous"].is_null()){if(fs::exists(state))fs::remove(state);}else save(state,j["previous"]);fs::remove(journal);
}
static json readCatalog(const fs::path& payload,const std::string& expected){
 checkHash(expected);auto raw=read(payload/L"catalog.json");require(hashBytes(raw)==expected,"Language package checksum mismatch");auto c=json::parse(raw);
 require(c.at("schemaVersion")==1&&c.at("game")=="OMORI"&&c.at("steamAppID")=="1150690"&&c.at("runtimeCode")=="en","Invalid OMORI package");std::set<std::string> codes;
 for(auto& l:c.at("locales")){require(codes.insert(l.at("code")).second,"Duplicate language");std::set<std::wstring> paths;for(auto i=l.at("files").begin();i!=l.at("files").end();++i){relativePath(i.key());std::wstring lower=fs::u8path(i.key()).wstring();std::transform(lower.begin(),lower.end(),lower.begin(),towlower);require(paths.insert(lower).second,"Colliding paths");checkHash(i.value().at("object"));checkHash(i.value().at("sha256"));require(c.at("objects").contains(i.value().at("object")),"Missing object");auto iv=unbase64(i.value().at("iv"));require(iv.empty()||iv.size()==16,"Invalid IV");}}
 require(!codes.empty(),"Empty language package");
 for(auto i=c.at("objects").begin();i!=c.at("objects").end();++i){checkHash(i.key());checkHash(i.value().at("sha256"));auto p=payload/L"objects"/fs::u8path(i.key());checkPath(p,payload);auto b=read(p);require(b.size()==i.value().at("bytes").get<size_t>()&&hashBytes(b)==i.value().at("sha256"),"Damaged language object");}
 return c;
}
static void install(const fs::path& payload,const std::string& expected,const fs::path& root,const std::string& code,int failAfter=0){
 assertClosed();checkPath(root,root);auto c=readCatalog(payload,expected);json selected;for(auto& l:c.at("locales"))if(l.at("code")==code)selected=l;require(!selected.is_null(),"Selected language is unavailable");
 auto meta=root/L".vnrevival-omori";checkPath(meta,root);fs::create_directories(meta);auto lockpath=meta/L"install.lock";checkPath(lockpath,root);
 HANDLE lock=CreateFileW(lockpath.c_str(),GENERIC_READ|GENERIC_WRITE,0,nullptr,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);require(lock!=INVALID_HANDLE_VALUE,"Another OMORI installer is already working");
 struct Lock{HANDLE h;~Lock(){CloseHandle(h);}} guard{lock};
 auto store=meta/L"backups",statepath=meta/L"state.json",journal=meta/L"journal.json";for(auto& p:{store,statepath,journal})checkPath(p,root);fs::create_directories(store);recover(journal,root,store,statepath);
 // Install the complete compressed set in an owned cache; only one locale is active.
 auto cache=meta/L"packages"/fs::u8path(expected);checkPath(cache,root);fs::create_directories(cache/L"objects");
 for(auto i=c["objects"].begin();i!=c["objects"].end();++i){auto dest=cache/L"objects"/fs::u8path(i.key());checkPath(dest,root);if(fs::exists(dest))require(hashFile(dest)==i.value()["sha256"],"Cached package changed");else atomicWrite(dest,read(payload/L"objects"/fs::u8path(i.key())));}
 auto cachedCatalog=cache/L"catalog.json";checkPath(cachedCatalog,root);if(fs::exists(cachedCatalog))require(hashFile(cachedCatalog)==expected,"Cached catalog changed");else atomicWrite(cachedCatalog,read(payload/L"catalog.json"));
 json previous=nullptr;if(fs::exists(statepath)){previous=load(statepath);validateState(previous,root);}
 json next={{"schemaVersion",1},{"gameRoot",root.u8string()},{"locale",code},{"runtimeCode","en"},{"catalog",expected},{"originals",previous.is_null()?json::object():previous.at("originals")},{"owned",json::object()}};
 std::set<std::string> paths;for(auto i=selected["files"].begin();i!=selected["files"].end();++i)paths.insert(i.key());if(!previous.is_null())for(auto i=previous["owned"].begin();i!=previous["owned"].end();++i)paths.insert(i.key());json ops=json::array();
 for(auto& p:paths){auto target=root/fs::u8path(p);checkPath(target,root);auto current=hashFile(target);
  if(!previous.is_null()&&previous["owned"].contains(p))require(current==previous["owned"][p],p+" was changed by another mod or update. Your file was preserved.");
  else{std::string original=next["originals"].value(p,c["originals"].value(p,std::string("-")));require(current==original,p+" differs from the supported original game. Restore it through Steam first; your file was preserved.");next["originals"][p]=current;}
  if(current!="-")putBlob(store,read(target));std::string original=next["originals"][p];if(original!="-"&&!previous.is_null()&&previous["originals"].contains(p))blob(store,original);
  std::string desired=original;
  if(selected["files"].contains(p)){auto f=selected["files"][p];auto o=c["objects"].at(f["object"]);auto plain=unpack(read(cache/L"objects"/fs::u8path(f["object"].get<std::string>())),o.at("unpackedBytes"));require(hashBytes(plain)==f["object"],"Plaintext object checksum mismatch");auto raw=encode(plain,unbase64(f.at("iv")));require(hashBytes(raw)==f["sha256"]&&raw.size()==f.at("bytes").get<size_t>(),"Native file checksum mismatch");desired=putBlob(store,raw);next["owned"][p]=desired;}
  if(desired!=current)ops.push_back({{"path",p},{"before",current},{"after",desired}});
 }
 assertClosed();save(journal,{{"schemaVersion",1},{"gameRoot",root.u8string()},{"previous",previous},{"operations",ops}});int count=0;
 for(auto& o:ops){auto target=root/fs::u8path(o.at("path").get<std::string>());checkPath(target,root);require(hashFile(target)==o["before"],"A game file changed during installation; recovery is pending");setFile(target,o.at("after"),store);if(failAfter>0&&++count==failAfter)throw std::runtime_error("Simulated test interruption");}
 save(statepath,next);if(failAfter==-1)throw std::runtime_error("Simulated state-commit interruption");fs::remove(journal);
}
static fs::path resolve(const fs::path& candidate){
 // Steam also ships duplicate data outside www. Follow the NW.js entry point.
 for(auto& p:{candidate,candidate/L"www"}) {
  if(!fs::is_regular_file(p/L"package.json")||!fs::is_regular_file(p/L"index.html")||!fs::is_regular_file(p/L"data/System.KEL"))continue;
  if(!fs::is_regular_file(p/L"OMORI.exe")&&!fs::is_regular_file(p.parent_path()/L"OMORI.exe"))continue;
  auto j=load(p/L"package.json");auto name=j.value("name",std::string());
  if((name.find("OMORI")!=std::string::npos||name.find("omori")!=std::string::npos)&&j.value("main",std::string())=="index.html")return fs::absolute(p).lexically_normal();
 }
 return {};
}
static fs::path detect(){
 std::vector<fs::path> libraries;
 for(auto keyname:{L"SOFTWARE\\Valve\\Steam",L"SOFTWARE\\WOW6432Node\\Valve\\Steam"})for(auto hive:{HKEY_CURRENT_USER,HKEY_LOCAL_MACHINE})for(auto name:{L"SteamPath",L"InstallPath"}){wchar_t value[4096];DWORD n=sizeof(value);if(RegGetValueW(hive,keyname,name,RRF_RT_REG_SZ,nullptr,value,&n)==ERROR_SUCCESS)libraries.emplace_back(value);}
 for(auto name:{L"ProgramFiles(x86)",L"ProgramFiles"}){wchar_t value[4096];if(GetEnvironmentVariableW(name,value,4096))libraries.push_back(fs::path(value)/L"Steam");}
 auto roots=libraries;for(auto& root:roots){auto vdf=root/L"steamapps/libraryfolders.vdf";if(!fs::exists(vdf))continue;auto b=read(vdf);std::string s(b.begin(),b.end());size_t at=0;while((at=s.find("\"path\"",at))!=std::string::npos){auto start=s.find('"',at+6);if(start==std::string::npos)break;auto end=s.find('"',start+1);if(end==std::string::npos)break;auto path=s.substr(start+1,end-start-1);std::string normalized;for(size_t i=0;i<path.size();i++){normalized+=path[i];if(path[i]=='\\'&&i+1<path.size()&&path[i+1]=='\\')i++;}libraries.push_back(fs::u8path(normalized));at=end+1;}}
 for(auto& lib:libraries){auto found=resolve(lib/L"steamapps/common/OMORI");if(!found.empty())return found;}return {};
}
int wmain(int argc,wchar_t** argv){
 fs::path statuspath;
 try{
  // UI contract: BASE STATUS GAMEPATH REQUESTED_GAME LOCALE [test interruption].
  require(argc>=6,"Invalid installer invocation");fs::path base=argv[1];statuspath=argv[2];fs::path gamepathfile=argv[3];std::wstring requested=argv[4];auto code=fs::path(argv[5]).u8string();
  status(statuspath,"Finding OMORI...");auto root=requested.empty()?detect():resolve(fs::path(requested));require(!root.empty(),"OMORI was not found. Choose the Windows game folder.");
  auto resources=base/L"Resources";auto config=load(resources/L"PackageConfig.json");status(statuspath,"Installing language packs and saving original files...");
  install(resources/L"Payload",config.at("catalogSha256"),root,code,argc>6?std::stoi(argv[6]):0);
  status(gamepathfile,root.u8string());status(statuspath,"Translation installed. You can change the language here whenever OMORI is closed.");return 0;
 }catch(const std::exception& e){try{status(statuspath,e.what());}catch(...){}std::cerr<<e.what()<<std::endl;return 1;}
}
