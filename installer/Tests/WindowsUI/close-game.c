// Close only the exact game executable launched by this installer smoke test.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wchar.h>
#include <stdio.h>
static const wchar_t* expected;
static HWND found;
static BOOL CALLBACK identify(HWND window,LPARAM p){(void)p;wchar_t title[100];GetWindowTextW(window,title,100);if(wcscmp(title,L"OMORI"))return TRUE;DWORD pid;GetWindowThreadProcessId(window,&pid);HANDLE h=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,FALSE,pid);if(!h)return TRUE;wchar_t path[4096];DWORD n=4096;BOOL ok=QueryFullProcessImageNameW(h,0,path,&n);CloseHandle(h);if(ok&&!_wcsicmp(path,expected))found=window;return TRUE;}
int wmain(int argc,wchar_t** argv){if(argc!=2)return 1;expected=argv[1];EnumWindows(identify,0);if(!found){fputs("Exact test game window not found\n",stderr);return 2;}PostMessageW(found,WM_CLOSE,0,0);return 0;}
