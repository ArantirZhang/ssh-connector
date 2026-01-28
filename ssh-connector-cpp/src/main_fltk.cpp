#include "ui/fltk/MainWindow.h"
#include "config/ConfigManager.h"

#include <FL/Fl.H>
#include <FL/fl_ask.H>
#include <libssh/libssh.h>
#include <filesystem>
#include <iostream>
#include <sstream>

#ifdef _WIN32
#include <winsock2.h>
#include <windows.h>
#endif

int main(int argc, char* argv[])
{
#ifdef _WIN32
    // Initialize Winsock (required on Windows, especially Windows 7)
    WSADATA wsaData;
    int wsaResult = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (wsaResult != 0) {
        std::ostringstream oss;
        oss << "Winsock initialization failed with error: " << wsaResult;
        std::cerr << oss.str() << std::endl;
        fl_alert("%s", oss.str().c_str());
        return 1;
    }
    std::cout << "Winsock initialized: version "
              << (int)LOBYTE(wsaData.wVersion) << "."
              << (int)HIBYTE(wsaData.wVersion) << std::endl;
#endif

    // Initialize libssh
    int sshResult = ssh_init();
    if (sshResult != SSH_OK) {
        std::ostringstream oss;
        oss << "libssh initialization failed with error code: " << sshResult;
        std::cerr << oss.str() << std::endl;
#ifdef _WIN32
        fl_alert("%s\n\nThis may be caused by missing Visual C++ Runtime.\nPlease install VC++ Redistributable.", oss.str().c_str());
        WSACleanup();
#else
        fl_alert("%s", oss.str().c_str());
#endif
        return 1;
    }
    std::cout << "libssh initialized: version " << ssh_version(0) << std::endl;

    // Set executable directory for portable key search
    if (argc > 0 && argv[0]) {
        std::filesystem::path exePath(argv[0]);
        sshconn::ConfigManager::setExecutableDir(exePath.parent_path().string());
    }

    // Enable multithreading support for Fl::awake()
    Fl::lock();

    sshconn::MainWindow window;
    window.show(argc, argv);

    int result = Fl::run();

    // Cleanup libssh
    ssh_finalize();

#ifdef _WIN32
    WSACleanup();
#endif

    return result;
}
