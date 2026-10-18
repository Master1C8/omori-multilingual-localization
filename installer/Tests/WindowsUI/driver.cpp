// Bounded Win32 UI driver for the delivered installer inside CrossOver.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include "../../vendor/json.hpp"
using json=nlohmann::json; namespace fs=std::filesystem;
static std::string utf8(const std::wstring& w){int n=WideCharToMultiByte(CP_UTF8,0,w.c_str(),-1,nullptr,0,nullptr,nullptr);std::string s(n,0);WideCharToMultiByte(CP_UTF8,0,w.c_str(),-1,s.data(),n,nullptr,nullptr);s.pop_back();return s;}
static std::wstring text(HWND h){wchar_t b[4096]{};SendMessageW(h,WM_GETTEXT,4096,(LPARAM)b);return b;}
static void require(bool c,const char* m){if(!c)throw std::runtime_error(m);}
int wmain(int argc,wchar_t** argv){try{
 require(argc>=4,"Pass expected EXE, action, and evidence output");auto window=FindWindowW(L"VNRevivalOmoriInstallerWindow",nullptr);require(window!=nullptr,"Installer window missing");DWORD pid=0;GetWindowThreadProcessId(window,&pid);HANDLE process=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,FALSE,pid);require(process!=nullptr,"Cannot identify installer");wchar_t exe[4096];DWORD length=4096;bool known=QueryFullProcessImageNameW(process,0,exe,&length);CloseHandle(process);require(known&&fs::equivalent(fs::path(exe),fs::path(argv[1])),"Unexpected installer identity");
 auto combo=FindWindowExW(window,nullptr,L"ComboBox",nullptr);require(combo!=nullptr,"Language selector missing");std::wstring action=argv[2];
 if(action==L"select"){require(argc==5,"Pass locale index");auto index=std::stoi(argv[4]);auto count=SendMessageW(combo,CB_GETCOUNT,0,0);require(index>=0&&index<count,"Language index outside list");SendMessageW(combo,CB_SETCURSEL,index,0);SendMessageW(window,WM_COMMAND,MAKEWPARAM(0,CBN_SELCHANGE),(LPARAM)combo);}
 else if(action==L"apply"){auto b=GetDlgItem(window,1001);require(IsWindowVisible(b)&&IsWindowEnabled(b),"Install action unavailable");SendMessageW(window,WM_COMMAND,1001,(LPARAM)b);}
 else if(action==L"launch"){auto b=GetDlgItem(window,1003);require(IsWindowVisible(b)&&IsWindowEnabled(b),"Launch action unavailable");SendMessageW(window,WM_COMMAND,1003,(LPARAM)b);}
 else require(action==L"inspect"||action==L"close","Unknown driver action");
 json controls=json::array();for(auto c=GetWindow(window,GW_CHILD);c;c=GetWindow(c,GW_HWNDNEXT)){wchar_t cls[100];GetClassNameW(c,cls,100);controls.push_back({{"class",utf8(cls)},{"text",utf8(text(c))},{"id",GetDlgCtrlID(c)},{"visible",bool(IsWindowVisible(c))},{"enabled",bool(IsWindowEnabled(c))}});}
 auto result=json{{"pid",pid},{"executable",utf8(exe)},{"action",utf8(action)},{"title",utf8(text(window))},{"selectedIndex",SendMessageW(combo,CB_GETCURSEL,0,0)},{"languageCount",SendMessageW(combo,CB_GETCOUNT,0,0)},{"controls",controls}};
 fs::path out=argv[3];require(!fs::exists(out),"Preserve existing evidence");std::ofstream(out)<<result.dump(2);SetForegroundWindow(window);
 if(action==L"close"){require(IsWindowEnabled(combo),"Refuse to close during installation");SendMessageW(window,WM_CLOSE,0,0);}return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}}
