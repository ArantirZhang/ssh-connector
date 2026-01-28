#include "SSHClient.h"
#include "../config/ConfigManager.h"

#include <iostream>
#include <filesystem>

namespace fs = std::filesystem;

namespace sshconn {

SSHClient::SSHClient()
{
}

SSHClient::~SSHClient()
{
    disconnect();
}

bool SSHClient::isConnected() const
{
    std::lock_guard<std::mutex> locker(m_mutex);
    return m_state == ConnectionState::Connected && isTransportActive();
}

bool SSHClient::isTransportActive() const
{
    return m_session != nullptr && ssh_is_connected(m_session);
}

void SSHClient::setState(ConnectionState state, const std::string& errorMessage)
{
    m_state = state;
    m_errorMessage = errorMessage;
    if (m_stateCallback) {
        m_stateCallback(state, errorMessage);
    }
}

bool SSHClient::loadKey(const std::string& keyPath)
{
    // Free any existing key
    if (m_privateKey != nullptr) {
        ssh_key_free(m_privateKey);
        m_privateKey = nullptr;
    }

    // Try loading key (libssh auto-detects key type)
    int rc = ssh_pki_import_privkey_file(keyPath.c_str(), nullptr, nullptr, nullptr, &m_privateKey);
    if (rc != SSH_OK) {
        std::cerr << "Failed to load SSH key: " << keyPath << std::endl;
        return false;
    }

    return true;
}

void SSHClient::connect()
{
    {
        std::lock_guard<std::mutex> locker(m_mutex);
        if (m_state == ConnectionState::Connecting || m_state == ConnectionState::Connected) {
            return;
        }
    }

    setState(ConnectionState::Connecting);

    // Get key path
    ConfigManager configManager;
    std::string keyPath = configManager.sshKeyPath();

    // Check if key exists
    if (!fs::exists(keyPath)) {
        std::string error = "SSH key not found: " + keyPath;
        cleanup();
        setState(ConnectionState::Error, error);
        std::cerr << error << std::endl;
        return;
    }

    // Load the private key
    if (!loadKey(keyPath)) {
        std::string error = "Failed to load SSH key: " + keyPath;
        cleanup();
        setState(ConnectionState::Error, error);
        std::cerr << error << std::endl;
        return;
    }

    // Create SSH session
    m_session = ssh_new();
    if (m_session == nullptr) {
        std::string error = "Failed to create SSH session";
        cleanup();
        setState(ConnectionState::Error, error);
        std::cerr << error << std::endl;
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

    std::cout << "Connecting to " << ServerConfig::SSH_USER << "@" << ServerConfig::SSH_HOST << ":" << ServerConfig::SSH_PORT << std::endl;

    // Connect to server
    int rc = ssh_connect(m_session);
    if (rc != SSH_OK) {
        std::string error = "Connection failed: " + std::string(ssh_get_error(m_session));
        cleanup();
        setState(ConnectionState::Error, error);
        std::cerr << error << std::endl;
        return;
    }

    // Authenticate with public key
    rc = ssh_userauth_publickey(m_session, nullptr, m_privateKey);
    if (rc != SSH_AUTH_SUCCESS) {
        std::string error = "Authentication failed: " + std::string(ssh_get_error(m_session));
        cleanup();
        setState(ConnectionState::Error, error);
        std::cerr << error << std::endl;
        return;
    }

    setState(ConnectionState::Connected);
    std::cout << "Connected successfully" << std::endl;
}

void SSHClient::disconnect()
{
    {
        std::lock_guard<std::mutex> locker(m_mutex);
        if (m_state == ConnectionState::Disconnected) {
            return;
        }
    }

    cleanup();
    setState(ConnectionState::Disconnected);
    std::cout << "Disconnected" << std::endl;
}

void SSHClient::cleanup()
{
    // Stop tunnel handler first
    if (m_tunnelHandler) {
        m_tunnelHandler->stop();
        m_tunnelHandler->join();
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
        std::cerr << "Cannot start tunnel: not connected" << std::endl;
        return false;
    }

    // Stop any existing tunnel
    stopReverseTunnel(remotePort);

    // Create and start tunnel handler
    m_tunnelHandler = std::make_unique<TunnelHandler>(m_session, localPort, remotePort);

    // Connect callbacks
    m_tunnelHandler->setErrorCallback([](const std::string& error) {
        std::cerr << "Tunnel error: " << error << std::endl;
    });

    m_tunnelHandler->start();

    std::cout << "Starting reverse tunnel: remote:" << remotePort << " -> local:" << localPort << std::endl;
    return true;
}

void SSHClient::stopReverseTunnel(int remotePort)
{
    (void)remotePort; // Unused parameter

    if (m_tunnelHandler) {
        m_tunnelHandler->stop();
        m_tunnelHandler->join();
        m_tunnelHandler.reset();
        std::cout << "Tunnel stopped" << std::endl;
    }
}

} // namespace sshconn
