#include "MainWindow.h"
#include "../../config/Config.h"

#include <FL/Fl.H>
#include <FL/fl_draw.H>

#include <iostream>
#include <sstream>

namespace sshconn {

// Window dimensions
constexpr int WINDOW_WIDTH = 360;
constexpr int WINDOW_HEIGHT = 280;
constexpr int MARGIN = 15;
constexpr int LABEL_HEIGHT = 20;
constexpr int INPUT_HEIGHT = 25;
constexpr int BUTTON_HEIGHT = 35;
constexpr int GROUP_LABEL_HEIGHT = 20;
constexpr int ROW_SPACING = 8;

MainWindow::MainWindow()
    : Fl_Window(WINDOW_WIDTH, WINDOW_HEIGHT, "SSH Tunnel Connector")
    , m_sshClient(std::make_unique<SSHClient>())
{
    // Load configuration
    m_configManager.load();

    setupUi();
    connectSignals();

    // Center window on screen
    position((Fl::w() - w()) / 2, (Fl::h() - h()) / 2);
}

MainWindow::~MainWindow()
{
    m_stopReconnect.store(true);

    if (m_sshClient->isConnected()) {
        m_sshClient->stopReverseTunnel(static_cast<int>(m_remotePortSpin->value()));
        m_sshClient->disconnect();
    }

    m_configManager.save();
}

void MainWindow::setupUi()
{
    int y = MARGIN;
    int contentWidth = WINDOW_WIDTH - 2 * MARGIN;

    // Server section label
    Fl_Box* serverLabel = new Fl_Box(MARGIN, y, contentWidth, GROUP_LABEL_HEIGHT, "Server");
    serverLabel->align(FL_ALIGN_LEFT | FL_ALIGN_INSIDE);
    serverLabel->labelfont(FL_BOLD);
    serverLabel->labelsize(12);
    y += GROUP_LABEL_HEIGHT;

    // Server value (user@host)
    std::ostringstream serverText;
    serverText << ServerConfig::SSH_USER << "@" << ServerConfig::SSH_HOST;
    m_serverLabel = new Fl_Box(MARGIN, y, contentWidth, LABEL_HEIGHT);
    m_serverLabel->copy_label(serverText.str().c_str());
    m_serverLabel->align(FL_ALIGN_CENTER | FL_ALIGN_INSIDE);
    m_serverLabel->labelsize(13);
    m_serverLabel->labelcolor(FL_DARK2);
    y += LABEL_HEIGHT + MARGIN;

    // Port Forwarding section label
    Fl_Box* portLabel = new Fl_Box(MARGIN, y, contentWidth, GROUP_LABEL_HEIGHT, "Port Forwarding");
    portLabel->align(FL_ALIGN_LEFT | FL_ALIGN_INSIDE);
    portLabel->labelfont(FL_BOLD);
    portLabel->labelsize(12);
    y += GROUP_LABEL_HEIGHT + 5;

    int labelWidth = 90;
    int spinnerWidth = 80;
    int inputX = MARGIN + labelWidth;

    // Local port row
    Fl_Box* localLabel = new Fl_Box(MARGIN, y, labelWidth, INPUT_HEIGHT, "Local Port:");
    localLabel->align(FL_ALIGN_LEFT | FL_ALIGN_INSIDE);
    localLabel->labelsize(12);

    m_localPortSpin = new Fl_Spinner(inputX, y, spinnerWidth, INPUT_HEIGHT);
    m_localPortSpin->type(FL_INT_INPUT);
    m_localPortSpin->minimum(PortRange::LOCAL_PORT_MIN);
    m_localPortSpin->maximum(PortRange::LOCAL_PORT_MAX);
    m_localPortSpin->value(m_configManager.config().tunnel.localPort);
    m_localPortSpin->textsize(12);
    y += INPUT_HEIGHT + ROW_SPACING;

    // Remote port row
    Fl_Box* remoteLabel = new Fl_Box(MARGIN, y, labelWidth, INPUT_HEIGHT, "Remote Port:");
    remoteLabel->align(FL_ALIGN_LEFT | FL_ALIGN_INSIDE);
    remoteLabel->labelsize(12);

    m_remotePortSpin = new Fl_Spinner(inputX, y, spinnerWidth, INPUT_HEIGHT);
    m_remotePortSpin->type(FL_INT_INPUT);
    m_remotePortSpin->minimum(PortRange::REMOTE_PORT_MIN);
    m_remotePortSpin->maximum(PortRange::REMOTE_PORT_MAX);
    m_remotePortSpin->value(m_configManager.config().tunnel.remotePort);
    m_remotePortSpin->textsize(12);
    y += INPUT_HEIGHT + MARGIN;

    // Status label (taller to fit error messages)
    int statusHeight = 40;
    m_statusLabel = new Fl_Box(MARGIN, y, contentWidth, statusHeight, "Disconnected");
    m_statusLabel->align(FL_ALIGN_CENTER | FL_ALIGN_INSIDE | FL_ALIGN_WRAP);
    m_statusLabel->labelcolor(FL_DARK3);
    m_statusLabel->labelsize(11);
    y += statusHeight + ROW_SPACING;

    // Connect button
    int buttonWidth = 120;
    int buttonX = (WINDOW_WIDTH - buttonWidth) / 2;
    m_connectBtn = new Fl_Button(buttonX, y, buttonWidth, BUTTON_HEIGHT, "Connect");
    m_connectBtn->box(FL_FLAT_BOX);
    m_connectBtn->color(fl_rgb_color(0, 122, 255)); // macOS blue
    m_connectBtn->labelcolor(FL_WHITE);
    m_connectBtn->labelfont(FL_BOLD);
    m_connectBtn->labelsize(13);
    m_connectBtn->clear_visible_focus(); // Remove dotted focus rectangle

    end(); // End adding widgets to window
}

void MainWindow::connectSignals()
{
    // Button callback
    m_connectBtn->callback(onConnectClick, this);

    // SSH state change callback
    m_sshClient->setStateCallback([this](ConnectionState state, const std::string& error) {
        scheduleUiUpdate(state, error);
    });
}

void MainWindow::onConnectClick(Fl_Widget* /*w*/, void* data)
{
    MainWindow* win = static_cast<MainWindow*>(data);
    if (win->m_sshClient->isConnected()) {
        win->doDisconnect();
    } else {
        win->doConnect();
    }
}

void MainWindow::scheduleUiUpdate(ConnectionState state, const std::string& error)
{
    {
        std::lock_guard<std::mutex> lock(m_pendingStateMutex);
        m_pendingState = state;
        m_pendingError = error;
        m_hasPendingUpdate = true;
    }

    // Schedule UI update on main thread
    Fl::awake(onAwake, this);
}

void MainWindow::onAwake(void* data)
{
    MainWindow* win = static_cast<MainWindow*>(data);

    ConnectionState state;
    std::string error;

    {
        std::lock_guard<std::mutex> lock(win->m_pendingStateMutex);
        if (!win->m_hasPendingUpdate) {
            return;
        }
        state = win->m_pendingState;
        error = win->m_pendingError;
        win->m_hasPendingUpdate = false;
    }

    win->updateUiState(state, error);
}

void MainWindow::doConnect()
{
    int localPort = static_cast<int>(m_localPortSpin->value());
    int remotePort = static_cast<int>(m_remotePortSpin->value());

    // Save config
    m_configManager.config().tunnel.localPort = localPort;
    m_configManager.config().tunnel.remotePort = remotePort;
    m_configManager.save();

    m_stopReconnect.store(false);

    // Connect in background thread
    std::thread([this, localPort, remotePort]() {
        m_sshClient->connect();
        if (m_sshClient->isConnected()) {
            m_sshClient->startReverseTunnel(localPort, remotePort);
        }
    }).detach();
}

void MainWindow::doDisconnect()
{
    m_stopReconnect.store(true);
    int remotePort = static_cast<int>(m_remotePortSpin->value());

    // Disconnect in background thread
    std::thread([this, remotePort]() {
        m_sshClient->stopReverseTunnel(remotePort);
        m_sshClient->disconnect();
    }).detach();
}

void MainWindow::updateUiState(ConnectionState state, const std::string& error)
{
    switch (state) {
        case ConnectionState::Connected:
            m_statusLabel->copy_label("Connected");
            m_statusLabel->labelcolor(fl_rgb_color(40, 167, 69)); // Green
            m_connectBtn->copy_label("Disconnect");
            m_connectBtn->color(fl_rgb_color(220, 53, 69)); // Red
            m_connectBtn->activate();
            m_localPortSpin->deactivate();
            m_remotePortSpin->deactivate();
            break;

        case ConnectionState::Disconnected:
            m_statusLabel->copy_label("Disconnected");
            m_statusLabel->labelcolor(FL_DARK3); // Gray
            m_connectBtn->copy_label("Connect");
            m_connectBtn->color(fl_rgb_color(0, 122, 255)); // Blue
            m_connectBtn->activate();
            m_localPortSpin->activate();
            m_remotePortSpin->activate();
            break;

        case ConnectionState::Connecting:
            m_statusLabel->copy_label("Connecting...");
            m_statusLabel->labelcolor(fl_rgb_color(255, 152, 0)); // Orange
            m_connectBtn->deactivate();
            break;

        case ConnectionState::Error: {
            std::string statusText = "Error: " + error;
            // Log full error to console
            std::cerr << "Connection error: " << error << std::endl;
            // Show full error in status (wrapped)
            m_statusLabel->copy_label(statusText.c_str());
            m_statusLabel->tooltip(error.c_str()); // Full error on hover
            m_statusLabel->labelcolor(fl_rgb_color(220, 53, 69)); // Red
            m_connectBtn->copy_label("Connect");
            m_connectBtn->color(fl_rgb_color(0, 122, 255)); // Blue
            m_connectBtn->activate();
            m_localPortSpin->activate();
            m_remotePortSpin->activate();
            break;
        }
    }

    // Redraw the window to show changes
    redraw();
}

int MainWindow::handle(int event)
{
    if (event == FL_CLOSE) {
        // Handle window close
        m_stopReconnect.store(true);

        if (m_sshClient->isConnected()) {
            m_sshClient->stopReverseTunnel(static_cast<int>(m_remotePortSpin->value()));
            m_sshClient->disconnect();
        }

        m_configManager.save();
        return 1; // Allow close
    }

    return Fl_Window::handle(event);
}

} // namespace sshconn
