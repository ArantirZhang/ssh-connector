#include "SSHClient.h"
#include "../config/ConfigManager.h"

#include <QDebug>
#include <QFile>
#include <QFileInfo>

namespace sshconn {

SSHClient::SSHClient(QObject* parent)
    : QObject(parent)
{
}

SSHClient::~SSHClient()
{
    disconnect();
}

bool SSHClient::isConnected() const
{
    QMutexLocker locker(&m_mutex);
    return m_state == ConnectionState::Connected && isTransportActive();
}

bool SSHClient::isTransportActive() const
{
    return m_session != nullptr && ssh_is_connected(m_session);
}

void SSHClient::setState(ConnectionState state, const QString& errorMessage)
{
    m_state = state;
    m_errorMessage = errorMessage;
    emit stateChanged(state, errorMessage);
}

bool SSHClient::loadKey(const QString& keyPath)
{
    // Free any existing key
    if (m_privateKey != nullptr) {
        ssh_key_free(m_privateKey);
        m_privateKey = nullptr;
    }

    // Try loading key (libssh auto-detects key type)
    int rc = ssh_pki_import_privkey_file(keyPath.toUtf8().constData(), nullptr, nullptr, nullptr, &m_privateKey);
    if (rc != SSH_OK) {
        qWarning() << "Failed to load SSH key:" << keyPath;
        return false;
    }

    return true;
}

void SSHClient::connect()
{
    {
        QMutexLocker locker(&m_mutex);
        if (m_state == ConnectionState::Connecting || m_state == ConnectionState::Connected) {
            return;
        }
    }

    setState(ConnectionState::Connecting);

    // Get key path
    ConfigManager configManager;
    QString keyPath = configManager.sshKeyPath();

    // Check if key exists
    QFileInfo keyInfo(keyPath);
    if (!keyInfo.exists()) {
        QString error = QString("SSH key not found: %1").arg(keyPath);
        cleanup();
        setState(ConnectionState::Error, error);
        qWarning() << error;
        return;
    }

    // Load the private key
    if (!loadKey(keyPath)) {
        QString error = QString("Failed to load SSH key: %1").arg(keyPath);
        cleanup();
        setState(ConnectionState::Error, error);
        qWarning() << error;
        return;
    }

    // Create SSH session
    m_session = ssh_new();
    if (m_session == nullptr) {
        QString error = "Failed to create SSH session";
        cleanup();
        setState(ConnectionState::Error, error);
        qWarning() << error;
        return;
    }

    // Configure session
    ssh_options_set(m_session, SSH_OPTIONS_HOST, ServerConfig::SSH_HOST);
    int port = ServerConfig::SSH_PORT;
    ssh_options_set(m_session, SSH_OPTIONS_PORT, &port);
    ssh_options_set(m_session, SSH_OPTIONS_USER, ServerConfig::SSH_USER);

    // Set connection timeout
    int timeout = 30;
    ssh_options_set(m_session, SSH_OPTIONS_TIMEOUT, &timeout);

    qInfo() << "Connecting to" << ServerConfig::SSH_USER << "@" << ServerConfig::SSH_HOST << ":" << ServerConfig::SSH_PORT;

    // Connect to server
    int rc = ssh_connect(m_session);
    if (rc != SSH_OK) {
        QString error = QString("Connection failed: %1").arg(ssh_get_error(m_session));
        cleanup();
        setState(ConnectionState::Error, error);
        qWarning() << error;
        return;
    }

    // Authenticate with public key
    rc = ssh_userauth_publickey(m_session, nullptr, m_privateKey);
    if (rc != SSH_AUTH_SUCCESS) {
        QString error = QString("Authentication failed: %1").arg(ssh_get_error(m_session));
        cleanup();
        setState(ConnectionState::Error, error);
        qWarning() << error;
        return;
    }

    setState(ConnectionState::Connected);
    qInfo() << "Connected successfully";
}

void SSHClient::disconnect()
{
    {
        QMutexLocker locker(&m_mutex);
        if (m_state == ConnectionState::Disconnected) {
            return;
        }
    }

    cleanup();
    setState(ConnectionState::Disconnected);
    qInfo() << "Disconnected";
}

void SSHClient::cleanup()
{
    // Stop tunnel handler first
    if (m_tunnelHandler) {
        m_tunnelHandler->stop();
        m_tunnelHandler->wait();
        m_tunnelHandler.reset();
    }

    // Free SSH session
    if (m_session != nullptr) {
        if (ssh_is_connected(m_session)) {
            ssh_disconnect(m_session);
        }
        ssh_free(m_session);
        m_session = nullptr;
    }

    // Free private key
    if (m_privateKey != nullptr) {
        ssh_key_free(m_privateKey);
        m_privateKey = nullptr;
    }
}

bool SSHClient::checkConnection()
{
    if (!isTransportActive()) {
        return false;
    }

    // Send a keep-alive message to verify connection
    int rc = ssh_send_ignore(m_session, "keepalive");
    return rc == SSH_OK;
}

bool SSHClient::startReverseTunnel(int localPort, int remotePort)
{
    if (!isTransportActive()) {
        qWarning() << "Cannot start tunnel: not connected";
        return false;
    }

    // Stop any existing tunnel
    stopReverseTunnel(remotePort);

    // Create and start tunnel handler
    m_tunnelHandler = std::make_unique<TunnelHandler>(m_session, localPort, remotePort);

    // Connect signals
    QObject::connect(m_tunnelHandler.get(), &TunnelHandler::tunnelError,
                     this, [this](const QString& error) {
        qWarning() << "Tunnel error:" << error;
    });

    m_tunnelHandler->start();

    qInfo() << "Starting reverse tunnel: remote:" << remotePort << "-> local:" << localPort;
    return true;
}

void SSHClient::stopReverseTunnel(int remotePort)
{
    Q_UNUSED(remotePort);

    if (m_tunnelHandler) {
        m_tunnelHandler->stop();
        m_tunnelHandler->wait();
        m_tunnelHandler.reset();
        qInfo() << "Tunnel stopped";
    }
}

} // namespace sshconn
