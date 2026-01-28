#ifndef TUNNEL_HANDLER_H
#define TUNNEL_HANDLER_H

#include <QThread>
#include <QMutex>
#include <atomic>
#include <libssh/libssh.h>

namespace sshconn {

class TunnelHandler : public QThread {
    Q_OBJECT

public:
    TunnelHandler(ssh_session session, int localPort, int remotePort, QObject* parent = nullptr);
    ~TunnelHandler() override;

    void stop();
    bool isRunning() const { return m_running.load(); }

signals:
    void tunnelError(const QString& error);
    void tunnelStarted(int remotePort);
    void tunnelStopped(int remotePort);

protected:
    void run() override;

private:
    void forwardData(ssh_channel channel, int localSocket);
    int connectToLocalPort();

    ssh_session m_session;
    int m_localPort;
    int m_remotePort;
    std::atomic<bool> m_running{false};
    std::atomic<bool> m_stopRequested{false};
};

} // namespace sshconn

#endif // TUNNEL_HANDLER_H
