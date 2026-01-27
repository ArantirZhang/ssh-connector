"""SSH Connector - Simple reverse tunnel client."""

import logging
import sys
import threading
import time
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QPushButton, QGroupBox, QMessageBox
)

from .config import (
    ConfigManager, SSH_HOST, SSH_USER,
    REMOTE_PORT_MIN, REMOTE_PORT_MAX
)
from .ssh_client import SSHClient, ConnectionState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SignalEmitter(QObject):
    """Helper to emit Qt signals from background threads."""
    state_changed = pyqtSignal(str, str)  # state, error


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load()
        self.ssh_client = SSHClient()
        self.signal_emitter = SignalEmitter()
        self._reconnect_thread: Optional[threading.Thread] = None
        self._stop_reconnect = threading.Event()

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        self.setWindowTitle("SSH Tunnel Connector")
        self.setFixedSize(350, 250)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Server info (read-only)
        server_group = QGroupBox("Server")
        server_layout = QVBoxLayout(server_group)
        server_label = QLabel(f"{SSH_USER}@{SSH_HOST}")
        server_label.setStyleSheet("font-weight: bold;")
        server_layout.addWidget(server_label)
        layout.addWidget(server_group)

        # Port configuration
        port_group = QGroupBox("Port Forwarding")
        port_layout = QVBoxLayout(port_group)

        # Local port
        local_layout = QHBoxLayout()
        local_layout.addWidget(QLabel("Local Port:"))
        self.local_port_spin = QSpinBox()
        self.local_port_spin.setRange(1, 65535)
        self.local_port_spin.setValue(self.config.tunnel.local_port)
        local_layout.addWidget(self.local_port_spin)
        port_layout.addLayout(local_layout)

        # Remote port
        remote_layout = QHBoxLayout()
        remote_layout.addWidget(QLabel("Remote Port:"))
        self.remote_port_spin = QSpinBox()
        self.remote_port_spin.setRange(REMOTE_PORT_MIN, REMOTE_PORT_MAX)
        self.remote_port_spin.setValue(self.config.tunnel.remote_port)
        remote_layout.addWidget(self.remote_port_spin)
        port_layout.addLayout(remote_layout)

        layout.addWidget(port_group)

        # Status
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setMinimumHeight(40)
        self.connect_btn.clicked.connect(self._toggle_connection)
        layout.addWidget(self.connect_btn)

    def _connect_signals(self):
        self.ssh_client.add_state_callback(self._on_state_changed_thread)
        self.signal_emitter.state_changed.connect(self._on_state_changed_ui)

    def _on_state_changed_thread(self, state: ConnectionState, error: Optional[str]):
        """Called from SSH client thread - emit signal to UI thread."""
        self.signal_emitter.state_changed.emit(state.value, error or "")

    def _on_state_changed_ui(self, state_str: str, error: str):
        """Handle state change in UI thread."""
        state = ConnectionState(state_str)

        if state == ConnectionState.CONNECTED:
            self.status_label.setText("Status: Connected")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setEnabled(True)
            self.local_port_spin.setEnabled(False)
            self.remote_port_spin.setEnabled(False)

        elif state == ConnectionState.DISCONNECTED:
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("color: gray;")
            self.connect_btn.setText("Connect")
            self.connect_btn.setEnabled(True)
            self.local_port_spin.setEnabled(True)
            self.remote_port_spin.setEnabled(True)

        elif state == ConnectionState.CONNECTING:
            self.status_label.setText("Status: Connecting...")
            self.status_label.setStyleSheet("color: orange;")
            self.connect_btn.setEnabled(False)

        elif state == ConnectionState.ERROR:
            self.status_label.setText(f"Status: Error - {error}")
            self.status_label.setStyleSheet("color: red;")
            self.connect_btn.setText("Connect")
            self.connect_btn.setEnabled(True)
            self.local_port_spin.setEnabled(True)
            self.remote_port_spin.setEnabled(True)

    def _toggle_connection(self):
        if self.ssh_client.is_connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        local_port = self.local_port_spin.value()
        remote_port = self.remote_port_spin.value()

        # Save config
        self.config.tunnel.local_port = local_port
        self.config.tunnel.remote_port = remote_port
        self.config_manager.save()

        self._stop_reconnect.clear()

        def connect_thread():
            try:
                self.ssh_client.connect()
                if self.ssh_client.is_connected:
                    self.ssh_client.start_reverse_tunnel(local_port, remote_port)
            except Exception as e:
                logger.error(f"Connection failed: {e}")

        thread = threading.Thread(target=connect_thread, daemon=True)
        thread.start()

    def _disconnect(self):
        self._stop_reconnect.set()
        remote_port = self.remote_port_spin.value()

        def disconnect_thread():
            self.ssh_client.stop_reverse_tunnel(remote_port)
            self.ssh_client.disconnect()

        thread = threading.Thread(target=disconnect_thread, daemon=True)
        thread.start()

    def closeEvent(self, event):
        self._stop_reconnect.set()
        if self.ssh_client.is_connected:
            self.ssh_client.stop_reverse_tunnel(self.remote_port_spin.value())
            self.ssh_client.disconnect()
        self.config_manager.save()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SSH Tunnel Connector")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
