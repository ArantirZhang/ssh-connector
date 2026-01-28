#ifndef MAIN_WINDOW_H
#define MAIN_WINDOW_H

#include "../../core/SSHClient.h"
#include "../../config/ConfigManager.h"

#include <FL/Fl.H>
#include <FL/Fl_Window.H>
#include <FL/Fl_Box.H>
#include <FL/Fl_Button.H>
#include <FL/Fl_Spinner.H>
#include <FL/Fl_Group.H>

#include <memory>
#include <thread>
#include <atomic>
#include <mutex>

namespace sshconn {

class MainWindow : public Fl_Window {
public:
    MainWindow();
    ~MainWindow() override;

    // FLTK event handler
    int handle(int event) override;

private:
    void setupUi();
    void connectSignals();
    void doConnect();
    void doDisconnect();
    void updateUiState(ConnectionState state, const std::string& error);

    // Schedule UI update from worker thread
    void scheduleUiUpdate(ConnectionState state, const std::string& error);

    // Static callbacks (FLTK pattern)
    static void onConnectClick(Fl_Widget* w, void* data);
    static void onAwake(void* data);

    // Configuration
    ConfigManager m_configManager;

    // SSH client
    std::unique_ptr<SSHClient> m_sshClient;

    // UI elements
    Fl_Box* m_serverLabel = nullptr;
    Fl_Spinner* m_localPortSpin = nullptr;
    Fl_Spinner* m_remotePortSpin = nullptr;
    Fl_Box* m_statusLabel = nullptr;
    Fl_Button* m_connectBtn = nullptr;

    // Threading
    std::atomic<bool> m_stopReconnect{false};

    // Pending UI update state (for thread-safe updates)
    std::mutex m_pendingStateMutex;
    ConnectionState m_pendingState = ConnectionState::Disconnected;
    std::string m_pendingError;
    bool m_hasPendingUpdate = false;
};

} // namespace sshconn

#endif // MAIN_WINDOW_H
