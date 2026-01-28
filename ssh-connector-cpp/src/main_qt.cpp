#include "ui/qt/MainWindow.h"
#include "config/ConfigManager.h"

#include <QApplication>
#include <filesystem>

int main(int argc, char* argv[])
{
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

    return app.exec();
}
