#ifndef CONNECTION_STATE_H
#define CONNECTION_STATE_H

#include <QString>

namespace sshconn {

enum class ConnectionState {
    Disconnected,
    Connecting,
    Connected,
    Error
};

inline QString connectionStateToString(ConnectionState state)
{
    switch (state) {
        case ConnectionState::Disconnected: return "Disconnected";
        case ConnectionState::Connecting: return "Connecting";
        case ConnectionState::Connected: return "Connected";
        case ConnectionState::Error: return "Error";
        default: return "Unknown";
    }
}

} // namespace sshconn

#endif // CONNECTION_STATE_H
