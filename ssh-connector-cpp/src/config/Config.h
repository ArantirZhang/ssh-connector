#ifndef CONFIG_H
#define CONFIG_H

#include <cstdint>

namespace sshconn {

// Fixed SSH server configuration
namespace ServerConfig {
    inline const char* const SSH_HOST = "we3d.com.cn";
    inline const int SSH_PORT = 22;
    inline const char* const SSH_USER = "tunneluser";
    inline const char* const SSH_KEY_PATH = "~/.ssh/tunnel_key";
    inline const int KEEPALIVE_INTERVAL = 60;
    inline const int KEEPALIVE_COUNT_MAX = 3;
}

// Remote port range constraints
namespace PortRange {
    constexpr int REMOTE_PORT_MIN = 12000;
    constexpr int REMOTE_PORT_MAX = 13000;
    constexpr int LOCAL_PORT_MIN = 1;
    constexpr int LOCAL_PORT_MAX = 65535;
}

// Tunnel configuration
struct TunnelConfig {
    int localPort = 80;
    int remotePort = 12000;
    bool enabled = false;

    bool operator==(const TunnelConfig& other) const {
        return localPort == other.localPort &&
               remotePort == other.remotePort &&
               enabled == other.enabled;
    }
};

// Application configuration
struct AppConfig {
    TunnelConfig tunnel;
    bool autoReconnect = true;
    double reconnectDelay = 5.0;
    double maxReconnectDelay = 300.0;

    bool operator==(const AppConfig& other) const {
        return tunnel == other.tunnel &&
               autoReconnect == other.autoReconnect &&
               reconnectDelay == other.reconnectDelay &&
               maxReconnectDelay == other.maxReconnectDelay;
    }
};

} // namespace sshconn

#endif // CONFIG_H
