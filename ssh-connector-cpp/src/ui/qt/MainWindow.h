#ifndef MAIN_WINDOW_QT_H
#define MAIN_WINDOW_QT_H

#include "../../core/SSHClient.h"
#include "../../config/ConfigManager.h"

#include <QMainWindow>
#include <QLabel>
#include <QSpinBox>
#include <QPushButton>
#include <memory>
#include <atomic>

namespace sshconn {

class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(QWidget* parent = nullptr);
    ~MainWindow() override;

protected:
    void closeEvent(QCloseEvent* event) override;

private slots:
    void toggleConnection();
    void onStateChanged(ConnectionState state, const std::string& error);

private:
    void setupUi();
    void connectSignals();
    void doConnect();
    void doDisconnect();
    void updateUiState(ConnectionState state, const std::string& error);

    // Configuration
    ConfigManager m_configManager;

    // SSH client
    std::unique_ptr<SSHClient> m_sshClient;

    // UI elements
    QLabel* m_serverLabel = nullptr;
    QSpinBox* m_localPortSpin = nullptr;
    QSpinBox* m_remotePortSpin = nullptr;
    QLabel* m_statusLabel = nullptr;
    QPushButton* m_connectBtn = nullptr;

    // Threading
    std::atomic<bool> m_stopReconnect{false};
};

} // namespace sshconn

#endif // MAIN_WINDOW_QT_H
