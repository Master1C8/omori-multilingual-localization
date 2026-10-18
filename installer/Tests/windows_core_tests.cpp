#define wmain omori_helper_entry
#include "../Windows/OmoriInstallHelper.cpp"
#undef wmain
static void check(bool x,const std::string& m){require(x,"TEST: "+m);}
static void reject(const std::function<void()>& action,const std::string& message){bool caught=false;try{action();}catch(const std::exception& e){caught=std::string(e.what()).find(message)!=std::string::npos;if(!caught)throw;}check(caught,"expected rejection: "+message);}
int wmain(int argc,wchar_t** argv){
 try{
  require(argc==3,"Pass fixture and test output directories");fs::path fixture=argv[1],work=argv[2];require(!fs::exists(work),"Preserve existing test output");fs::create_directories(work);
  auto expectedBytes=read(fixture/L"expected.sha256");std::string expected(expectedBytes.begin(),expectedBytes.end());auto root=work/L"game";fs::create_directories(root/L"data");atomicWrite(root/L"data/System.KEL",Bytes{'o','f','f','i','c','i','a','l',' ','s','y','s','t','e','m'});atomicWrite(root/L"save/file1.rpgsave",Bytes{'s','a','v','e'});
  auto official=read(root/L"data/System.KEL");auto call=[&](const std::string& code,int fail=0){install(fixture,expected,root,code,fail);};
  call("es");auto spanish=read(root/L"data/System.KEL");check(spanish!=official,"first application changes actual bytes");check(load(root/L".vnrevival-omori/state.json")["locale"]=="es","locale persisted");
  call("es");check(read(root/L"data/System.KEL")==spanish,"repeat stable");call("fr");check(!fs::exists(root/L"fonts/Only-ES.ttf")&&fs::exists(root/L"fonts/Only-FR.ttf"),"old-only font removed");check(read(root/L"save/file1.rpgsave")==Bytes({'s','a','v','e'}),"save preserved");
  call("es");reject([&]{call("fr",1);},"Simulated test interruption");check(fs::exists(root/L".vnrevival-omori/journal.json"),"journal survives failure");call("fr");check(load(root/L".vnrevival-omori/state.json")["locale"]=="fr","real partial-state continuation");
  reject([&]{call("es",-1);},"state-commit interruption");check(load(root/L".vnrevival-omori/state.json")["locale"]=="es","failure after state write exercised");call("fr");check(load(root/L".vnrevival-omori/state.json")["locale"]=="fr","commit-boundary recovery");
  reject([&]{call("unknown");},"unavailable");reject([&]{install(fixture,std::string(64,'0'),root,"es");},"checksum mismatch");
  reject([&]{call("es",1);},"Simulated test interruption");atomicWrite(root/L"data/System.KEL",Bytes{'u','s','e','r'});reject([&]{call("es");},"changed after interrupted");check(read(root/L"data/System.KEL")==Bytes({'u','s','e','r'}),"owner edit retained");
  auto other=work/L"other";fs::create_directories(other/L"data");atomicWrite(other/L"data/System.KEL",Bytes{'m','o','d'});reject([&]{install(fixture,expected,other,"es");},"differs from the supported original");check(read(other/L"data/System.KEL")==Bytes({'m','o','d'}),"foreign original retained");
  reject([&]{relativePath("data/../../outside");},"Unsafe path segment");reject([&]{relativePath("save/file1.rpgsave");},"Unsafe game resource path");
  auto nested=work/L"nested";fs::create_directories(nested/L"www/data");atomicWrite(nested/L"OMORI.exe",Bytes{'m'});save(nested/L"www/package.json",{{"name","OMORI"},{"main","index.html"}});atomicWrite(nested/L"www/index.html",Bytes{'h'});atomicWrite(nested/L"www/data/System.KEL",official);
  save(nested/L"package.json",{{"name","OMORI"},{"main","www/index.html"}});atomicWrite(nested/L"data/System.KEL",official);
  check(resolve(nested)==fs::absolute(nested/L"www"),"root folder discovery");check(resolve(nested/L"www")==fs::absolute(nested/L"www"),"persisted www resource folder discovery");
  atomicWrite(nested/L"index.html",Bytes{'h'});check(resolve(nested)==fs::absolute(nested/L"www"),"outer duplicate data and index cannot override main entry point");
  auto direct=work/L"direct";atomicWrite(direct/L"OMORI.exe",Bytes{'m'});save(direct/L"package.json",{{"name","OMORI"},{"main","index.html"}});atomicWrite(direct/L"index.html",Bytes{'h'});atomicWrite(direct/L"data/System.KEL",official);check(resolve(direct)==fs::absolute(direct),"direct resource root positive control");
  auto report=json{{"status","passed"},{"groups",9},{"boundaries",{"native AES-CTR and gzip hashes","first application and repeat","locale persistence and old-only file removal","save isolation","mid-file interruption continuation","state-commit interruption recovery","unknown edits preserved","package and path rejection","root and persisted www discovery"}}};save(work/L"result.json",report);return 0;
 }catch(const std::exception& e){try{if(argc>2)status(fs::path(argv[2])/L"failure.txt",e.what());}catch(...){}std::cerr<<e.what()<<std::endl;return 1;}
}
