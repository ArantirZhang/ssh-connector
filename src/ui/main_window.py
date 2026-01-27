"""Main application window."""

import logging
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSystemTrayIcon,
    QMenu,
    QMessageBox,
    QInputDialog,
    QLineEdit,
)

from ..config import ConfigManager
from ..ssh_client import SSHClient, ConnectionState
from ..tunnel_manager import TunnelManager, TunnelState
from ..connection_monitor import ConnectionMonitor, MonitorState
from .settings_dialog import SettingsDialog
from .connection_status import ConnectionStatusWidget

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(
        self,
        config_manager: ConfigManager,
        ssh_client: SSHClient,
        tunnel_manager: TunnelManager,
        connection_monitor: ConnectionMonitor,
        parent: Optional[QWidget] = None
    ):
        """Initialize main window.

        Args:
            config_manager: Configuration manager.
            ssh_client: SSH client instance.
            tunnel_manager: Tunnel manager instance.
            connection_monitor: Connection monitor instance.
            parent: Parent widget.
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.ssh_client = ssh_client
        self.tunnel_manager = tunnel_manager
        self.connection_monitor = connection_monitor

        self._key_passphrase: Optional[str] = None

        self._setup_ui()
        self._setup_tray()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("SSH Connector")
        self.setMinimumSize(400, 300)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Connection status widget
        self.status_widget = ConnectionStatusWidget()
        layout.addWidget(self.status_widget)

        # Server info label
        self.server_label = QLabel()
        self._update_server_label()
        layout.addWidget(self.server_label)

        # Connection controls
        controls_layout = QHBoxLayout()

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_action)
        controls_layout.addWidget(self.connect_button)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_action)
        self.disconnect_button.setEnabled(False)
        controls_layout.addWidget(self.disconnect_button)

        layout.addLayout(controls_layout)

        # Settings button
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self._show_settings)
        layout.addWidget(self.settings_button)

        # Stretch to push everything up
        layout.addStretch()

        # Status bar
        self.statusBar().showMessage("Ready")

    def _setup_tray(self) -> None:
        """Set up system tray icon."""
        self.tray_icon = QSystemTrayIcon(self)
        # TODO: Set proper icon
        # self.tray_icon.setIcon(QIcon(":/icons/tray.png"))

        # Tray menu
        tray_menu = QMenu()

        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        self.tray_connect_action = QAction("Connect", self)
        self.tray_connect_action.triggered.connect(self.connect_action)
        tray_menu.addAction(self.tray_connect_action)

        self.tray_disconnect_action = QAction("Disconnect", self)
        self.tray_disconnect_action.triggered.connect(self.disconnect_action)
        self.tray_disconnect_action.setEnabled(False)
        tray_menu.addAction(self.tray_disconnect_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._quit_application)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_activated)

        if self.config_manager.config.ui.minimize_to_tray:
            self.tray_icon.show()

    def _connect_signals(self) -> None:
        """Connect to component signals/callbacks."""
        # SSH client state changes
        self.ssh_client.add_state_callback(self._on_connection_state_changed)

        # Tunnel state changes
        self.tunnel_manager.add_callback(self._on_tunnel_state_changed)

        # Monitor reconnect events
        self.connection_monitor.add_reconnect_callback(self._on_reconnect_attempt)

    def _update_server_label(self) -> None:
        """Update server info label."""
        config = self.config_manager.config
        if config.server.hostname:
            self.server_label.setText(
                f"Server: {config.server.username}@{config.server.hostname}:{config.server.port}"
            )
        else:
            self.server_label.setText("Server: Not configured")

    def connect_action(self) -> None:
        """Connect to SSH server."""
        # Validate configuration
        errors = self.config_manager.validate()
        if errors:
            QMessageBox.warning(
                self,
                "Configuration Error",
                "Please fix the following:\n\n" + "\n".join(errors)
            )
            return

        # Check if key needs passphrase
        if self._key_passphrase is None:
            # Try connecting without passphrase first
            pass

        self.connect_button.setEnabled(False)
        self.statusBar().showMessage("Connecting...")

        try:
            self.ssh_client.connect(self._key_passphrase)

            # Set transport for tunnels
            transport = self.ssh_client.get_transport()
            self.tunnel_manager.set_transport(transport)

            # Start tunnels
            self.tunnel_manager.start_all_tunnels(
                self.config_manager.config.port_forwarding_rules
            )

            # Start connection monitor
            self.connection_monitor.start(self._key_passphrase)

        except Exception as e:
            error_msg = str(e)

            # Check if it needs a passphrase
            if "passphrase" in error_msg.lower():
                passphrase, ok = QInputDialog.getText(
                    self,
                    "SSH Key Passphrase",
                    "Enter passphrase for SSH key:",
                    QLineEdit.EchoMode.Password
                )
                if ok and passphrase:
                    self._key_passphrase = passphrase
                    self.connect_button.setEnabled(True)
                    self.connect_action()  # Retry with passphrase
                    return

            QMessageBox.critical(self, "Connection Error", error_msg)
            self.connect_button.setEnabled(True)

    def disconnect_action(self) -> None:
        """Disconnect from SSH server."""
        self.connection_monitor.stop()
        self.tunnel_manager.stop_all_tunnels()
        self.ssh_client.disconnect()

    def _on_connection_state_changed(
        self,
        state: ConnectionState,
        error: Optional[str]
    ) -> None:
        """Handle SSH connection state changes."""
        # Update UI (called from background thread, need to use Qt signals in production)
        self.status_widget.set_connection_state(state)

        if state == ConnectionState.CONNECTED:
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.tray_connect_action.setEnabled(False)
            self.tray_disconnect_action.setEnabled(True)
            self.statusBar().showMessage("Connected")
            self._show_notification("SSH Connector", "Connected to server")

        elif state == ConnectionState.DISCONNECTED:
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
            self.tray_connect_action.setEnabled(True)
            self.tray_disconnect_action.setEnabled(False)
            self.statusBar().showMessage("Disconnected")

        elif state == ConnectionState.ERROR:
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
            self.tray_connect_action.setEnabled(True)
            self.tray_disconnect_action.setEnabled(False)
            self.statusBar().showMessage(f"Error: {error}")
            self._show_notification("SSH Connector", f"Connection error: {error}")

        elif state == ConnectionState.CONNECTING:
            self.statusBar().showMessage("Connecting...")

    def _on_tunnel_state_changed(
        self,
        rule,
        state: TunnelState,
        error: Optional[str]
    ) -> None:
        """Handle tunnel state changes."""
        self.status_widget.update_tunnel_status(rule, state, error)

    def _on_reconnect_attempt(self, attempt: int, delay: float) -> None:
        """Handle reconnect attempts."""
        self.statusBar().showMessage(f"Reconnecting (attempt {attempt})...")
        self._show_notification(
            "SSH Connector",
            f"Connection lost. Reconnecting (attempt {attempt})..."
        )

    def _show_settings(self) -> None:
        """Show settings dialog."""
        dialog = SettingsDialog(self.config_manager, self)
        if dialog.exec():
            # Settings were saved
            self._update_server_label()
            self.config_manager.save()

    def _show_notification(self, title: str, message: str) -> None:
        """Show system notification."""
        if (
            self.config_manager.config.ui.show_notifications
            and self.tray_icon.isVisible()
        ):
            self.tray_icon.showMessage(
                title,
                message,
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        if (
            self.config_manager.config.ui.minimize_to_tray
            and self.tray_icon.isVisible()
        ):
            self.hide()
            event.ignore()
        else:
            self._quit_application()

    def _quit_application(self) -> None:
        """Quit the application."""
        self.tray_icon.hide()
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
