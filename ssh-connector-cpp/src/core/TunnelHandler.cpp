#include "TunnelHandler.h"

#include <QDebug>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
#include <cerrno>
#endif

namespace sshconn {

TunnelHandler::TunnelHandler(ssh_session session, int localPort, int remotePort, QObject* parent)
    : QThread(parent)
    , m_session(session)
    , m_localPort(localPort)
    , m_remotePort(remotePort)
{
}

TunnelHandler::~TunnelHandler()
{
    stop();
    wait();
}

void TunnelHandler::stop()
{
    m_stopRequested.store(true);
}

int TunnelHandler::connectToLocalPort()
{
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        return -1;
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(m_localPort);
    addr.sin_addr.s_addr = inet_addr("127.0.0.1");

    if (::connect(sock, reinterpret_cast<struct sockaddr*>(&addr), sizeof(addr)) < 0) {
#ifdef _WIN32
        closesocket(sock);
#else
        close(sock);
#endif
        return -1;
    }

    return sock;
}

void TunnelHandler::forwardData(ssh_channel channel, int localSocket)
{
    constexpr int BUFFER_SIZE = 32768;
    char buffer[BUFFER_SIZE];

    // Set socket to non-blocking
#ifdef _WIN32
    u_long mode = 1;
    ioctlsocket(localSocket, FIONBIO, &mode);
#else
    int flags = fcntl(localSocket, F_GETFL, 0);
    fcntl(localSocket, F_SETFL, flags | O_NONBLOCK);
#endif

    while (!m_stopRequested.load() && ssh_channel_is_open(channel) && !ssh_channel_is_eof(channel)) {
        // Channel -> Socket
        int nbytes = ssh_channel_read_nonblocking(channel, buffer, BUFFER_SIZE, 0);
        if (nbytes > 0) {
            int total_sent = 0;
            while (total_sent < nbytes) {
                int sent = send(localSocket, buffer + total_sent, nbytes - total_sent, 0);
                if (sent <= 0) break;
                total_sent += sent;
            }
        } else if (nbytes == SSH_ERROR) {
            break;
        }

        // Socket -> Channel
        int received = recv(localSocket, buffer, BUFFER_SIZE, 0);
        if (received > 0) {
            int written = ssh_channel_write(channel, buffer, received);
            if (written < 0) break;
        } else if (received == 0) {
            // Connection closed
            break;
#ifdef _WIN32
        } else if (WSAGetLastError() != WSAEWOULDBLOCK) {
#else
        } else if (errno != EAGAIN && errno != EWOULDBLOCK) {
#endif
            break;
        }

        // Small sleep to avoid busy-waiting
        QThread::msleep(1);
    }

    // Cleanup
    ssh_channel_send_eof(channel);
    ssh_channel_close(channel);
    ssh_channel_free(channel);

#ifdef _WIN32
    closesocket(localSocket);
#else
    close(localSocket);
#endif
}

void TunnelHandler::run()
{
    m_running.store(true);

    // Request remote port forwarding
    int rc = ssh_channel_listen_forward(m_session, "127.0.0.1", m_remotePort, nullptr);
    if (rc != SSH_OK) {
        QString error = QString("Failed to request port forward: %1").arg(ssh_get_error(m_session));
        emit tunnelError(error);
        m_running.store(false);
        return;
    }

    emit tunnelStarted(m_remotePort);
    qInfo() << "Reverse tunnel started: remote:" << m_remotePort << "-> local:" << m_localPort;

    // Accept loop
    while (!m_stopRequested.load()) {
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
        ssh_channel channel = ssh_channel_accept_forward(m_session, 1000, nullptr);
#pragma GCC diagnostic pop
        if (channel == nullptr) {
            // Timeout or no connection, check if we should continue
            if (m_stopRequested.load()) break;
            continue;
        }

        // Connect to local port
        int localSocket = connectToLocalPort();
        if (localSocket < 0) {
            qWarning() << "Failed to connect to local port" << m_localPort;
            ssh_channel_close(channel);
            ssh_channel_free(channel);
            continue;
        }

        // Forward data in the current thread (sequential handling)
        // For production, consider spawning a new thread per connection
        forwardData(channel, localSocket);
    }

    // Cancel port forwarding
    ssh_channel_cancel_forward(m_session, "127.0.0.1", m_remotePort);

    m_running.store(false);
    emit tunnelStopped(m_remotePort);
    qInfo() << "Reverse tunnel stopped: remote:" << m_remotePort;
}

} // namespace sshconn
