#define WIN32_LEAN_AND_MEAN

#include <windows.h>
#include <commctrl.h>
#include <shellapi.h>
#include <shlobj.h>
#include <stdio.h>
#include <wchar.h>

#define APP_TITLE L"VN Revival Languages for OMORI"
#define WM_INSTALL_FINISHED (WM_APP + 1)
#define ID_RETRY 1001
#define ID_CHOOSE 1002
#define ID_LAUNCH 1003

static HWND languageCombo;
static WCHAR languageCodes[40][20];
static WCHAR activeCode[20] = L"ru";
static HWND statusLabel;
static HWND progressBar;
static HWND retryButton;
static HWND chooseButton;
static HWND launchButton;
static HFONT uiFont;
static HFONT titleFont;
static volatile LONG installationRunning;
static WCHAR applicationDirectory[MAX_PATH * 4];
static WCHAR selectedGamePath[MAX_PATH * 4];
static WCHAR installedGamePath[MAX_PATH * 4];
static WCHAR statusFile[MAX_PATH * 4];
static WCHAR gamePathFile[MAX_PATH * 4];
static WCHAR settingsFile[MAX_PATH * 4];

static void loadSettings(void) {
    WCHAR local[MAX_PATH * 2], parent[MAX_PATH * 4];
    if (SHGetFolderPathW(NULL, CSIDL_LOCAL_APPDATA, NULL, SHGFP_TYPE_CURRENT, local) != S_OK) return;
    swprintf(parent, _countof(parent), L"%ls\\VNRevival", local); CreateDirectoryW(parent, NULL);
    swprintf(parent, _countof(parent), L"%ls\\VNRevival\\OMORI", local); CreateDirectoryW(parent, NULL);
    swprintf(settingsFile, _countof(settingsFile), L"%ls\\settings.ini", parent);
    GetPrivateProfileStringW(L"Installer", L"Language", L"ru", activeCode, _countof(activeCode), settingsFile);
    GetPrivateProfileStringW(L"Installer", L"GamePath", L"", selectedGamePath, _countof(selectedGamePath), settingsFile);
}

static void saveSettings(void) {
    if (!settingsFile[0]) return;
    if (GetFileAttributesW(settingsFile) == INVALID_FILE_ATTRIBUTES) {
        HANDLE file = CreateFileW(settingsFile, GENERIC_WRITE, 0, NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, NULL);
        if (file != INVALID_HANDLE_VALUE) { unsigned char bom[2] = {255, 254}; DWORD n; WriteFile(file, bom, 2, &n, NULL); CloseHandle(file); }
    }
    WritePrivateProfileStringW(L"Installer", L"Language", activeCode, settingsFile);
    WritePrivateProfileStringW(L"Installer", L"GamePath", installedGamePath, settingsFile);
    wcscpy(selectedGamePath, installedGamePath);
}

static void setControlFont(HWND control) {
    SendMessageW(control, WM_SETFONT, (WPARAM)uiFont, TRUE);
}

static void showInstallingState(void) {
    SetWindowTextW(statusLabel, L"Installing language packs and saving original files…");
    ShowWindow(progressBar, SW_SHOW);
    SendMessageW(progressBar, PBM_SETMARQUEE, TRUE, 35);
    EnableWindow(languageCombo, FALSE);
    ShowWindow(retryButton, SW_HIDE);
    ShowWindow(chooseButton, SW_HIDE);
    ShowWindow(launchButton, SW_HIDE);
}

static void showFailureState(const WCHAR *message) {
    EnableWindow(languageCombo, TRUE);
    SetWindowTextW(statusLabel, message && message[0] ? message : L"Installation did not finish. Your original files are preserved; see the message below.");
    SendMessageW(progressBar, PBM_SETMARQUEE, FALSE, 0);
    ShowWindow(progressBar, SW_HIDE);
    ShowWindow(retryButton, SW_SHOW);
    ShowWindow(chooseButton, SW_SHOW);
    ShowWindow(launchButton, SW_HIDE);
}

static void showSuccessState(void) {
    EnableWindow(languageCombo, TRUE);
    SetWindowTextW(statusLabel, L"Translation installed");
    SendMessageW(progressBar, PBM_SETMARQUEE, FALSE, 0);
    ShowWindow(progressBar, SW_HIDE);
    ShowWindow(retryButton, SW_SHOW);
    ShowWindow(chooseButton, SW_SHOW);
    ShowWindow(launchButton, SW_SHOW);
}

static BOOL readUtf8File(const WCHAR *path, WCHAR *destination, DWORD capacity) {
    HANDLE file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return FALSE;

    char buffer[4096];
    DWORD bytesRead = 0;
    BOOL read = ReadFile(file, buffer, sizeof(buffer) - 1, &bytesRead, NULL);
    CloseHandle(file);
    if (!read || bytesRead == 0) return FALSE;
    buffer[bytesRead] = '\0';

    int converted = MultiByteToWideChar(CP_UTF8, 0, buffer, -1, destination, (int)capacity);
    return converted > 0;
}

static BOOL readStatusMessage(WCHAR *destination, DWORD capacity) {
    return readUtf8File(statusFile, destination, capacity);
}

static DWORD WINAPI installWorker(LPVOID parameter) {
    HWND window = (HWND)parameter;
    WCHAR helperPath[MAX_PATH * 4];
    WCHAR commandLine[MAX_PATH * 16];
    swprintf(helperPath, _countof(helperPath), L"%ls\\Resources\\OmoriInstallHelper.exe", applicationDirectory);
    swprintf(commandLine, _countof(commandLine), L"\"%ls\" \"%ls\" \"%ls\" \"%ls\" \"%ls\" \"%ls\"", helperPath, applicationDirectory, statusFile, gamePathFile, selectedGamePath, activeCode);
    DeleteFileW(statusFile);
    DeleteFileW(gamePathFile);
    installedGamePath[0] = L'\0';
    STARTUPINFOW startup = {0};
    PROCESS_INFORMATION process = {0};
    startup.cb = sizeof(startup);
    BOOL started = CreateProcessW(
        helperPath,
        commandLine,
        NULL,
        NULL,
        FALSE,
        CREATE_NO_WINDOW,
        NULL,
        applicationDirectory,
        &startup,
        &process
    );

    DWORD exitCode = 1;
    if (started) {
        WaitForSingleObject(process.hProcess, INFINITE);
        GetExitCodeProcess(process.hProcess, &exitCode);
        CloseHandle(process.hThread);
        CloseHandle(process.hProcess);
    } else {
        FILE *status = _wfopen(statusFile, L"wb");
        if (status) {
            fputs("The OMORI installation helper could not be started. Extract the complete installer ZIP first.", status);
            fclose(status);
        }
    }

    InterlockedExchange(&installationRunning, 0);
    PostMessageW(window, WM_INSTALL_FINISHED, (WPARAM)exitCode, 0);
    return 0;
}

static void startInstallation(HWND window) {
    if (InterlockedCompareExchange(&installationRunning, 1, 0) != 0) return;
    LRESULT selected = SendMessageW(languageCombo, CB_GETCURSEL, 0, 0);
    if (selected == CB_ERR || selected >= 40) { InterlockedExchange(&installationRunning, 0); return; }
    wcscpy(activeCode, languageCodes[selected]);
    showInstallingState();
    HANDLE thread = CreateThread(NULL, 0, installWorker, window, 0, NULL);
    if (!thread) {
        InterlockedExchange(&installationRunning, 0);
        showFailureState(L"The installer worker could not be started.");
        return;
    }
    CloseHandle(thread);
}

static BOOL chooseGameFolder(HWND owner) {
    BROWSEINFOW browse = {0};
    browse.hwndOwner = owner;
    browse.lpszTitle = L"Choose the OMORI folder";
    browse.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE;
    PIDLIST_ABSOLUTE item = SHBrowseForFolderW(&browse);
    if (!item) return FALSE;
    BOOL resolved = SHGetPathFromIDListW(item, selectedGamePath);
    CoTaskMemFree(item);
    return resolved;
}

static void loadLanguages(void) {
    WCHAR path[MAX_PATH * 4], text[4096];
    swprintf(path, _countof(path), L"%ls\\Resources\\languages.tsv", applicationDirectory);
    if (!readUtf8File(path, text, _countof(text))) return;
    WCHAR *line = text; int index = 0; int initial = 0;
    while (line && *line && index < 40) {
        WCHAR *end = wcschr(line, L'\n'); if (end) *end = 0;
        WCHAR *tab = wcschr(line, L'\t');
        if (tab) {
            *tab = 0; BOOL safe = wcslen(line) > 0 && wcslen(line) < 20;
            for (WCHAR *p = line; *p; p++) if (!((*p >= L'a' && *p <= L'z') || (*p >= L'A' && *p <= L'Z') || (*p >= L'0' && *p <= L'9') || *p == L'-')) safe = FALSE;
            if (safe) { if (!wcscmp(activeCode, line)) initial = index; wcscpy(languageCodes[index], line); SendMessageW(languageCombo, CB_ADDSTRING, 0, (LPARAM)(tab + 1)); index++; }
        }
        line = end ? end + 1 : NULL;
    }
    SendMessageW(languageCombo, CB_SETCURSEL, (WPARAM)initial, 0);
}

static LRESULT CALLBACK windowProcedure(HWND window, UINT message, WPARAM wParam, LPARAM lParam) {
    (void)lParam;
    switch (message) {
        case WM_CREATE: {
            uiFont = CreateFontW(-18, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
                OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Segoe UI");
            HWND title = CreateWindowW(L"STATIC", APP_TITLE, WS_CHILD | WS_VISIBLE,
                36, 30, 520, 36, window, NULL, NULL, NULL);
            titleFont = CreateFontW(-25, 0, 0, 0, FW_SEMIBOLD, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
                OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Segoe UI");
            SendMessageW(title, WM_SETFONT, (WPARAM)titleFont, TRUE);

            statusLabel = CreateWindowW(L"STATIC", L"Choose a language, then click Install. OMORI will be found automatically.", WS_CHILD | WS_VISIBLE,
                38, 77, 500, 92, window, NULL, NULL, NULL);
            progressBar = CreateWindowW(PROGRESS_CLASSW, NULL, WS_CHILD | WS_VISIBLE | PBS_MARQUEE,
                38, 224, 500, 12, window, NULL, NULL, NULL);
            retryButton = CreateWindowW(L"BUTTON", L"Install / Apply language", WS_CHILD | BS_PUSHBUTTON,
                38, 253, 180, 38, window, (HMENU)ID_RETRY, NULL, NULL);
            chooseButton = CreateWindowW(L"BUTTON", L"Choose game…", WS_CHILD | BS_PUSHBUTTON,
                232, 253, 160, 38, window, (HMENU)ID_CHOOSE, NULL, NULL);
            launchButton = CreateWindowW(L"BUTTON", L"Launch game", WS_CHILD | BS_DEFPUSHBUTTON,
                38, 302, 180, 40, window, (HMENU)ID_LAUNCH, NULL, NULL);
            HWND hint = CreateWindowW(L"STATIC", L"This may take a few minutes", WS_CHILD | WS_VISIBLE,
                38, 352, 500, 26, window, NULL, NULL, NULL);

            languageCombo = CreateWindowW(WC_COMBOBOXW, L"", WS_CHILD | WS_VISIBLE | CBS_DROPDOWNLIST | WS_VSCROLL | WS_TABSTOP, 38, 180, 500, 400, window, NULL, NULL, NULL);
            setControlFont(languageCombo);
            loadLanguages();
            setControlFont(statusLabel);
            setControlFont(retryButton);
            setControlFont(chooseButton);
            setControlFont(launchButton);
            setControlFont(hint);
            ShowWindow(retryButton, SW_SHOW);
            ShowWindow(chooseButton, SW_SHOW);
            ShowWindow(progressBar, SW_HIDE);
            return 0;
        }
        case WM_APP:
            startInstallation(window);
            return 0;
        case WM_INSTALL_FINISHED: {
            DWORD exitCode = (DWORD)wParam;
            if (exitCode == 0) {
                if (readUtf8File(gamePathFile, installedGamePath, _countof(installedGamePath))) {
                    saveSettings();
                    showSuccessState();
                } else {
                    showFailureState(L"The game path was not recorded. Retry the installation.");
                }
            } else {
                WCHAR details[2048] = {0};
                if (!readStatusMessage(details, _countof(details)) && exitCode == 2) {
                    wcscpy(details, L"OMORI was not found. Choose the game folder.");
                }
                showFailureState(details);
            }
            return 0;
        }
        case WM_COMMAND:
            if ((HWND)lParam == languageCombo && HIWORD(wParam) == CBN_SELCHANGE) {
                ShowWindow(launchButton, SW_HIDE);
                SetWindowTextW(statusLabel, L"Language selected. Click Install / Apply language before launching OMORI.");
                return 0;
            }
            switch (LOWORD(wParam)) {
                case ID_RETRY:
                    startInstallation(window);
                    return 0;
                case ID_CHOOSE:
                    if (chooseGameFolder(window)) SetWindowTextW(statusLabel, L"Game folder selected. Choose a language and click Install.");
                    return 0;
                case ID_LAUNCH:
                    if (installedGamePath[0]) {
                        if ((INT_PTR)ShellExecuteW(window, L"open", L"steam://rungameid/1150690", NULL, NULL, SW_SHOWNORMAL) <= 32) {
                            showFailureState(L"Steam could not be opened. Launch OMORI from your Steam library.");
                        }
                    } else {
                        showFailureState(L"Install a language before launching the game.");
                    }
                    return 0;
            }
            break;
        case WM_CLOSE:
            if (InterlockedCompareExchange(&installationRunning, 0, 0) != 0) {
                MessageBoxW(window, L"Installation is still in progress.", APP_TITLE, MB_OK | MB_ICONINFORMATION);
                return 0;
            }
            DestroyWindow(window);
            return 0;
        case WM_DESTROY:
            if (uiFont) DeleteObject(uiFont);
            if (titleFont) DeleteObject(titleFont);
            DeleteFileW(statusFile);
            DeleteFileW(gamePathFile);
            PostQuitMessage(0);
            return 0;
    }
    return DefWindowProcW(window, message, wParam, lParam);
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR commandLine, int showCommand) {
    (void)previous;
    (void)commandLine;

    INITCOMMONCONTROLSEX controls = {sizeof(controls), ICC_PROGRESS_CLASS};
    InitCommonControlsEx(&controls);
    CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);

    WCHAR executablePath[MAX_PATH * 4];
    DWORD length = GetModuleFileNameW(NULL, executablePath, _countof(executablePath));
    if (length == 0 || length >= _countof(executablePath)) return 1;
    WCHAR *separator = wcsrchr(executablePath, L'\\');
    if (!separator) return 1;
    *separator = L'\0';
    wcscpy(applicationDirectory, executablePath);
    loadSettings();

    WCHAR temporaryDirectory[MAX_PATH * 2];
    GetTempPathW(_countof(temporaryDirectory), temporaryDirectory);
    swprintf(statusFile, _countof(statusFile), L"%lsVNRevival-Omori-Installer-%lu.txt", temporaryDirectory, GetCurrentProcessId());
    swprintf(gamePathFile, _countof(gamePathFile), L"%lsVNRevival-Omori-GamePath-%lu.txt", temporaryDirectory, GetCurrentProcessId());

    WNDCLASSEXW windowClass = {0};
    windowClass.cbSize = sizeof(windowClass);
    windowClass.lpfnWndProc = windowProcedure;
    windowClass.hInstance = instance;
    windowClass.hIcon = LoadIconW(instance, MAKEINTRESOURCEW(1));
    windowClass.hIconSm = windowClass.hIcon;
    windowClass.hCursor = LoadCursorW(NULL, IDC_ARROW);
    windowClass.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    windowClass.lpszClassName = L"VNRevivalOmoriInstallerWindow";
    if (!RegisterClassExW(&windowClass)) return 1;

    const int width = 590;
    const int height = 440;
    RECT desktop;
    SystemParametersInfoW(SPI_GETWORKAREA, 0, &desktop, 0);
    int x = desktop.left + (desktop.right - desktop.left - width) / 2;
    int y = desktop.top + (desktop.bottom - desktop.top - height) / 2;
    HWND window = CreateWindowExW(
        0,
        windowClass.lpszClassName,
        APP_TITLE,
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
        x,
        y,
        width,
        height,
        NULL,
        NULL,
        instance,
        NULL
    );
    if (!window) return 1;

    ShowWindow(window, showCommand);
    UpdateWindow(window);
    MSG message;
    while (GetMessageW(&message, NULL, 0, 0) > 0) {
        TranslateMessage(&message);
        DispatchMessageW(&message);
    }
    CoUninitialize();
    return (int)message.wParam;
}
