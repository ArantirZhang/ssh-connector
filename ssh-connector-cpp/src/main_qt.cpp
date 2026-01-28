#include "ui/qt/MainWindow.h"
#include "config/ConfigManager.h"

#include <QApplication>
#include <libssh/libssh.h>
#include <filesystem>

#ifdef _WIN32
#include <winsock2.h>
#endif

int main(int argc, char* argv[])
{
#ifdef _WIN32
    // Initialize Winsock (required on Windows, especially Windows 7)
    WSADATA wsaData;
    WSAStartup(MAKEWORD(2, 2), &wsaData);
#endif

    // Initialize libssh
    ssh_init();

    // Set executable directory for portable key search
    if (argc > 0 && argv[0]) {
        std::filesystem::path exePath(argv[0]);
        sshconn::ConfigManager::setExecutableDir(exePath.parent_path().string());
    }

    QApplication app(argc, argv);
    app.setApplicationName("SSH Tunnel Connector");
    app.setOrganizationName("SSH Connector");

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
