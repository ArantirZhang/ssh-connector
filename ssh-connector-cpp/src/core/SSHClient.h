#ifndef SSH_CLIENT_H
#define SSH_CLIENT_H

#include "ConnectionState.h"
#include "TunnelHandler.h"
#include "../config/Config.h"

#include <QObject>
#include <QMutex>
#include <QString>
#include <memory>
#include <libssh/libssh.h>

namespace sshconn {

class SSHClient : public QObject {
    Q_OBJECT

public:
    explicit SSHClient(QObject* parent = nullptr);
    ~SSHClient() override;

    // Connection management
    void connect();
    void disconnect();

    // State queries
    ConnectionState state() const { return m_state; }
    QString errorMessage() const { return m_errorMessage; }
    bool isConnected() const;

    // Tunnel management
    bool startReverseTunnel(int localPort, int remotePort);
    void stopReverseTunnel(int remotePort);

    // Connection health
    bool checkConnection();

signals:
    void stateChanged(sshconn::ConnectionState state, const QString& error);

private:
    void setState(ConnectionState state, const QString& errorMessage = QString());
    bool loadKey(const QString& keyPath);
    void cleanup();
    bool isTransportActive() const;

    ssh_session m_session = nullptr;
    ssh_key m_privateKey = nullptr;
    ConnectionState m_state = ConnectionState::Disconnected;
    QString m_errorMessage;
    mutable QMutex m_mutex;

    std::unique_ptr<TunnelHandler> m_tunnelHandler;
};

} // namespace sshconn

#endif // SSH_CLIENT_H
