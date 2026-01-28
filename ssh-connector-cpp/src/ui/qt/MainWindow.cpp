#include "MainWindow.h"
#include "../../config/Config.h"

#include <QApplication>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGroupBox>
#include <QCloseEvent>
#include <QThread>
#include <thread>

namespace sshconn {

MainWindow::MainWindow(QWidget* parent)
    : QMainWindow(parent)
    , m_sshClient(std::make_unique<SSHClient>())
{
    // Load configuration
    m_configManager.load();

    setupUi();
    connectSignals();
}

MainWindow::~MainWindow() = default;

void MainWindow::setupUi()
{
    setWindowTitle("SSH Tunnel Connector");
    setFixedSize(350, 250);

    QWidget* central = new QWidget(this);
    setCentralWidget(central);

    QVBoxLayout* layout = new QVBoxLayout(central);

    // Server info (read-only)
    QGroupBox* serverGroup = new QGroupBox("Server", central);
    QVBoxLayout* serverLayout = new QVBoxLayout(serverGroup);

    m_serverLabel = new QLabel(
        QString("%1@%2").arg(ServerConfig::SSH_USER).arg(ServerConfig::SSH_HOST),
        serverGroup
    );
    m_serverLabel->setStyleSheet("font-weight: bold;");
    serverLayout->addWidget(m_serverLabel);
    layout->addWidget(serverGroup);

    // Port configuration
    QGroupBox* portGroup = new QGroupBox("Port Forwarding", central);
    QVBoxLayout* portLayout = new QVBoxLayout(portGroup);

    // Local port
    QHBoxLayout* localLayout = new QHBoxLayout();
    localLayout->addWidget(new QLabel("Local Port:", portGroup));
    m_localPortSpin = new QSpinBox(portGroup);
    m_localPortSpin->setRange(PortRange::LOCAL_PORT_MIN, PortRange::LOCAL_PORT_MAX);
    m_localPortSpin->setValue(m_configManager.config().tunnel.localPort);
    localLayout->addWidget(m_localPortSpin);
    portLayout->addLayout(localLayout);

    // Remote port
    QHBoxLayout* remoteLayout = new QHBoxLayout();
    remoteLayout->addWidget(new QLabel("Remote Port:", portGroup));
    m_remotePortSpin = new QSpinBox(portGroup);
    m_remotePortSpin->setRange(PortRange::REMOTE_PORT_MIN, PortRange::REMOTE_PORT_MAX);
    m_remotePortSpin->setValue(m_configManager.config().tunnel.remotePort);
    remoteLayout->addWidget(m_remotePortSpin);
    portLayout->addLayout(remoteLayout);

    layout->addWidget(portGroup);

    // Status
    m_statusLabel = new QLabel("Status: Disconnected", central);
    m_statusLabel->setAlignment(Qt::AlignCenter);
    layout->addWidget(m_statusLabel);

    // Connect button
    m_connectBtn = new QPushButton("Connect", central);
    m_connectBtn->setMinimumHeight(40);
    layout->addWidget(m_connectBtn);
}

void MainWindow::connectSignals()
{
    // Button click
    QObject::connect(m_connectBtn, &QPushButton::clicked,
                     this, &MainWindow::toggleConnection);

    // SSH state changes - use a lambda to bridge std::function callback to Qt slot
    m_sshClient->setStateCallback([this](ConnectionState state, const std::string& error) {
        // Use QMetaObject::invokeMethod for thread-safe slot invocation
        QMetaObject::invokeMethod(this, [this, state, error]() {
            onStateChanged(state, error);
        }, Qt::QueuedConnection);
    });
}

void MainWindow::toggleConnection()
{
    if (m_sshClient->isConnected()) {
        doDisconnect();
    } else {
        doConnect();
    }
}

void MainWindow::doConnect()
{
    int localPort = m_localPortSpin->value();
    int remotePort = m_remotePortSpin->value();

    // Save config
    m_configManager.config().tunnel.localPort = localPort;
    m_configManager.config().tunnel.remotePort = remotePort;
    m_configManager.save();

    m_stopReconnect.store(false);

    // Connect in background thread
    std::thread([this, localPort, remotePort]() {
        m_sshClient->connect();
        if (m_sshClient->isConnected()) {
            m_sshClient->startReverseTunnel(localPort, remotePort);
        }
    }).detach();
}

void MainWindow::doDisconnect()
{
    m_stopReconnect.store(true);
    int remotePort = m_remotePortSpin->value();

    // Disconnect in background thread
    std::thread([this, remotePort]() {
        m_sshClient->stopReverseTunnel(remotePort);
        m_sshClient->disconnect();
    }).detach();
}

void MainWindow::onStateChanged(ConnectionState state, const std::string& error)
{
    updateUiState(state, error);
}

void MainWindow::updateUiState(ConnectionState state, const std::string& error)
{
    switch (state) {
        case ConnectionState::Connected:
            m_statusLabel->setText("Status: Connected");
            m_statusLabel->setStyleSheet("color: green; font-weight: bold;");
            m_connectBtn->setText("Disconnect");
            m_connectBtn->setEnabled(true);
            m_localPortSpin->setEnabled(false);
            m_remotePortSpin->setEnabled(false);
            break;

        case ConnectionState::Disconnected:
            m_statusLabel->setText("Status: Disconnected");
            m_statusLabel->setStyleSheet("color: gray;");
            m_connectBtn->setText("Connect");
            m_connectBtn->setEnabled(true);
            m_localPortSpin->setEnabled(true);
            m_remotePortSpin->setEnabled(true);
            break;

        case ConnectionState::Connecting:
            m_statusLabel->setText("Status: Connecting...");
            m_statusLabel->setStyleSheet("color: orange;");
            m_connectBtn->setEnabled(false);
            break;

        case ConnectionState::Error:
            m_statusLabel->setText(QString("Status: Error - %1").arg(QString::fromStdString(error)));
            m_statusLabel->setStyleSheet("color: red;");
            m_connectBtn->setText("Connect");
            m_connectBtn->setEnabled(true);
            m_localPortSpin->setEnabled(true);
            m_remotePortSpin->setEnabled(true);
            break;
    }
}

void MainWindow::closeEvent(QCloseEvent* event)
{
    m_stopReconnect.store(true);

    if (m_sshClient->isConnected()) {
        m_sshClient->stopReverseTunnel(m_remotePortSpin->value());
        m_sshClient->disconnect();
    }

    m_configManager.save();
    event->accept();
}

} // namespace sshconn
