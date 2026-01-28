#include "ui/qt/MainWindow.h"

#include <QApplication>

int main(int argc, char* argv[])
{
    QApplication app(argc, argv);
    app.setApplicationName("SSH Tunnel Connector");
    app.setOrganizationName("SSH Connector");

    sshconn::MainWindow window;
    window.show();

    return app.exec();
}
