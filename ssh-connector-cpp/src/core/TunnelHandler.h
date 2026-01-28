#ifndef TUNNEL_HANDLER_H
#define TUNNEL_HANDLER_H

#include <atomic>
#include <functional>
#include <string>
#include <thread>
#include <libssh/libssh.h>

namespace sshconn {

class TunnelHandler {
public:
    using ErrorCallback = std::function<void(const std::string&)>;
    using StartedCallback = std::function<void(int)>;
    using StoppedCallback = std::function<void(int)>;

    TunnelHandler(ssh_session session, int localPort, int remotePort);
    ~TunnelHandler();

    void start();
    void stop();
    void join();
    bool isRunning() const { return m_running.load(); }

    void setErrorCallback(ErrorCallback cb) { m_errorCallback = std::move(cb); }
    void setStartedCallback(StartedCallback cb) { m_startedCallback = std::move(cb); }
    void setStoppedCallback(StoppedCallback cb) { m_stoppedCallback = std::move(cb); }

private:
    void run();
    void forwardData(ssh_channel channel, int localSocket);
    int connectToLocalPort();

    ssh_session m_session;
    int m_localPort;
    int m_remotePort;
    std::atomic<bool> m_running{false};
    std::atomic<bool> m_stopRequested{false};
    std::thread m_thread;

    ErrorCallback m_errorCallback;
    StartedCallback m_startedCallback;
    StoppedCallback m_stoppedCallback;
};

} // namespace sshconn

#endif // TUNNEL_HANDLER_H
