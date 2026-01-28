#include "ui/qt/MainWindow.h"
#include "config/ConfigManager.h"

#include <QApplication>
#include <QMessageBox>
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
    QApplication app(argc, argv);
    app.setApplicationName("SSH Tunnel Connector");
    app.setOrganizationName("SSH Connector");

#ifdef _WIN32
    // Initialize Winsock (required on Windows, especially Windows 7)
    WSADATA wsaData;
    int wsaResult = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (wsaResult != 0) {
        std::ostringstream oss;
        oss << "Winsock initialization failed with error: " << wsaResult;
        std::cerr << oss.str() << std::endl;
        QMessageBox::critical(nullptr, "Initialization Error", QString::fromStdString(oss.str()));
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
        QMessageBox::critical(nullptr, "Initialization Error",
            QString::fromStdString(oss.str()) + "\n\nThis may be caused by missing Visual C++ Runtime.\nPlease install VC++ Redistributable.");
        WSACleanup();
#else
        QMessageBox::critical(nullptr, "Initialization Error", QString::fromStdString(oss.str()));
#endif
        return 1;
    }
    std::cout << "libssh initialized: version " << ssh_version(0) << std::endl;

    // Set executable directory for portable key search
    if (argc > 0 && argv[0]) {
        std::filesystem::path exePath(argv[0]);
        sshconn::ConfigManager::setExecutableDir(exePath.parent_path().string());
    }

    sshconn::MainWindow window;
    window.show();

    int result = app.exec();

    // Cleanup libssh
    ssh_finalize();

#ifdef _WIN32
    WSACleanup();
#endif

    return result;
}
