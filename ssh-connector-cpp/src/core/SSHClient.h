#ifndef SSH_CLIENT_H
#define SSH_CLIENT_H

#include "ConnectionState.h"
#include "TunnelHandler.h"
#include "../config/Config.h"

#include <functional>
#include <mutex>
#include <string>
#include <memory>
#include <libssh/libssh.h>

namespace sshconn {

class SSHClient {
public:
    using StateCallback = std::function<void(ConnectionState, const std::string&)>;

    SSHClient();
    ~SSHClient();

    // Prevent copying
    SSHClient(const SSHClient&) = delete;
    SSHClient& operator=(const SSHClient&) = delete;

    // Connection management
    void connect();
    void disconnect();

    // State queries
    ConnectionState state() const { return m_state; }
    std::string errorMessage() const { return m_errorMessage; }
    bool isConnected() const;

    // Tunnel management
    bool startReverseTunnel(int localPort, int remotePort);
    void stopReverseTunnel(int remotePort);

    // Connection health
    bool checkConnection();

    // Callback registration
    void setStateCallback(StateCallback cb) { m_stateCallback = std::move(cb); }

private:
    void setState(ConnectionState state, const std::string& errorMessage = std::string());
    bool loadKey(const std::string& keyPath);
    void cleanup();
    bool isTransportActive() const;

    ssh_session m_session = nullptr;
    ssh_key m_privateKey = nullptr;
    ConnectionState m_state = ConnectionState::Disconnected;
    std::string m_errorMessage;
    mutable std::mutex m_mutex;

    std::unique_ptr<TunnelHandler> m_tunnelHandler;
    StateCallback m_stateCallback;
};

} // namespace sshconn

#endif // SSH_CLIENT_H
