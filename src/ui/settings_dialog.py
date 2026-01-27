"""Settings configuration dialog."""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QPushButton,
    QFileDialog,
    QGroupBox,
    QDialogButtonBox,
    QMessageBox,
)

from ..config import ConfigManager, PortForwardRule
from .port_forward_widget import PortForwardWidget


class SettingsDialog(QDialog):
    """Settings configuration dialog."""

    def __init__(
        self,
        config_manager: ConfigManager,
        parent: Optional[QWidget] = None
    ):
        """Initialize settings dialog.

        Args:
            config_manager: Configuration manager.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.config = config_manager.config

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # Tab widget
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Server tab
        server_tab = self._create_server_tab()
        tabs.addTab(server_tab, "Server")

        # Port Forwarding tab
        self.port_forward_widget = PortForwardWidget()
        tabs.addTab(self.port_forward_widget, "Port Forwarding")

        # Reconnect tab
        reconnect_tab = self._create_reconnect_tab()
        tabs.addTab(reconnect_tab, "Reconnect")

        # UI tab
        ui_tab = self._create_ui_tab()
        tabs.addTab(ui_tab, "Interface")

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _create_server_tab(self) -> QWidget:
        """Create server configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Server settings
        server_group = QGroupBox("SSH Server")
        server_layout = QFormLayout(server_group)

        self.hostname_edit = QLineEdit()
        self.hostname_edit.setPlaceholderText("hostname or IP address")
        server_layout.addRow("Hostname:", self.hostname_edit)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        server_layout.addRow("Port:", self.port_spin)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("SSH username")
        server_layout.addRow("Username:", self.username_edit)

        layout.addWidget(server_group)

        # SSH Key settings
        key_group = QGroupBox("SSH Key")
        key_layout = QFormLayout(key_group)

        key_path_layout = QHBoxLayout()
        self.key_path_edit = QLineEdit()
        self.key_path_edit.setPlaceholderText("Path to private key file")
        key_path_layout.addWidget(self.key_path_edit)

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_key_file)
        key_path_layout.addWidget(browse_button)

        key_layout.addRow("Key File:", key_path_layout)

        self.keyring_check = QCheckBox("Store passphrase in system keyring")
        key_layout.addRow("", self.keyring_check)

        layout.addWidget(key_group)

        # Connection settings
        conn_group = QGroupBox("Connection")
        conn_layout = QFormLayout(conn_group)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 300)
        self.timeout_spin.setSuffix(" seconds")
        conn_layout.addRow("Timeout:", self.timeout_spin)

        self.keepalive_spin = QSpinBox()
        self.keepalive_spin.setRange(5, 300)
        self.keepalive_spin.setSuffix(" seconds")
        conn_layout.addRow("Keepalive Interval:", self.keepalive_spin)

        layout.addWidget(conn_group)

        layout.addStretch()
        return widget

    def _create_reconnect_tab(self) -> QWidget:
        """Create reconnect settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Auto-Reconnect")
        group_layout = QFormLayout(group)

        self.reconnect_enabled_check = QCheckBox("Enable auto-reconnect")
        group_layout.addRow("", self.reconnect_enabled_check)

        self.max_attempts_spin = QSpinBox()
        self.max_attempts_spin.setRange(0, 1000)
        self.max_attempts_spin.setSpecialValueText("Unlimited")
        group_layout.addRow("Max Attempts:", self.max_attempts_spin)

        self.initial_delay_spin = QDoubleSpinBox()
        self.initial_delay_spin.setRange(0.5, 60.0)
        self.initial_delay_spin.setSuffix(" seconds")
        self.initial_delay_spin.setDecimals(1)
        group_layout.addRow("Initial Delay:", self.initial_delay_spin)

        self.max_delay_spin = QDoubleSpinBox()
        self.max_delay_spin.setRange(10.0, 3600.0)
        self.max_delay_spin.setSuffix(" seconds")
        self.max_delay_spin.setDecimals(0)
        group_layout.addRow("Max Delay:", self.max_delay_spin)

        self.backoff_spin = QDoubleSpinBox()
        self.backoff_spin.setRange(1.0, 5.0)
        self.backoff_spin.setDecimals(1)
        group_layout.addRow("Backoff Multiplier:", self.backoff_spin)

        layout.addWidget(group)
        layout.addStretch()
        return widget

    def _create_ui_tab(self) -> QWidget:
        """Create UI settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # System tray
        tray_group = QGroupBox("System Tray")
        tray_layout = QVBoxLayout(tray_group)

        self.minimize_to_tray_check = QCheckBox("Minimize to system tray")
        tray_layout.addWidget(self.minimize_to_tray_check)

        self.start_minimized_check = QCheckBox("Start minimized")
        tray_layout.addWidget(self.start_minimized_check)

        self.show_notifications_check = QCheckBox("Show notifications")
        tray_layout.addWidget(self.show_notifications_check)

        layout.addWidget(tray_group)

        # Startup
        startup_group = QGroupBox("Startup")
        startup_layout = QVBoxLayout(startup_group)

        self.start_on_boot_check = QCheckBox("Start on system boot")
        startup_layout.addWidget(self.start_on_boot_check)

        self.connect_on_start_check = QCheckBox("Connect automatically on start")
        startup_layout.addWidget(self.connect_on_start_check)

        layout.addWidget(startup_group)

        layout.addStretch()
        return widget

    def _browse_key_file(self) -> None:
        """Open file browser for SSH key selection."""
        # Start in ~/.ssh if it exists
        start_dir = str(Path.home() / ".ssh")
        if not Path(start_dir).exists():
            start_dir = str(Path.home())

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SSH Private Key",
            start_dir,
            "All Files (*)"
        )
        if file_path:
            self.key_path_edit.setText(file_path)

    def _load_settings(self) -> None:
        """Load current settings into UI."""
        config = self.config

        # Server
        self.hostname_edit.setText(config.server.hostname)
        self.port_spin.setValue(config.server.port)
        self.username_edit.setText(config.server.username)

        # SSH Key
        self.key_path_edit.setText(config.ssh_key.path)
        self.keyring_check.setChecked(config.ssh_key.passphrase_in_keyring)

        # Connection
        self.timeout_spin.setValue(config.connection.timeout_seconds)
        self.keepalive_spin.setValue(config.connection.keepalive_interval_seconds)

        # Port forwarding
        self.port_forward_widget.set_rules(config.port_forwarding_rules)

        # Reconnect
        self.reconnect_enabled_check.setChecked(config.reconnect.enabled)
        self.max_attempts_spin.setValue(config.reconnect.max_attempts)
        self.initial_delay_spin.setValue(config.reconnect.initial_delay_seconds)
        self.max_delay_spin.setValue(config.reconnect.max_delay_seconds)
        self.backoff_spin.setValue(config.reconnect.backoff_multiplier)

        # UI
        self.minimize_to_tray_check.setChecked(config.ui.minimize_to_tray)
        self.start_minimized_check.setChecked(config.ui.start_minimized)
        self.show_notifications_check.setChecked(config.ui.show_notifications)

        # System
        self.start_on_boot_check.setChecked(config.system.start_on_boot)
        self.connect_on_start_check.setChecked(config.system.connect_on_start)

    def _save_settings(self) -> None:
        """Save UI values to configuration."""
        config = self.config

        # Server
        config.server.hostname = self.hostname_edit.text().strip()
        config.server.port = self.port_spin.value()
        config.server.username = self.username_edit.text().strip()

        # SSH Key
        config.ssh_key.path = self.key_path_edit.text().strip()
        config.ssh_key.passphrase_in_keyring = self.keyring_check.isChecked()

        # Connection
        config.connection.timeout_seconds = self.timeout_spin.value()
        config.connection.keepalive_interval_seconds = self.keepalive_spin.value()

        # Port forwarding
        config.port_forwarding_rules = self.port_forward_widget.get_rules()

        # Reconnect
        config.reconnect.enabled = self.reconnect_enabled_check.isChecked()
        config.reconnect.max_attempts = self.max_attempts_spin.value()
        config.reconnect.initial_delay_seconds = self.initial_delay_spin.value()
        config.reconnect.max_delay_seconds = self.max_delay_spin.value()
        config.reconnect.backoff_multiplier = self.backoff_spin.value()

        # UI
        config.ui.minimize_to_tray = self.minimize_to_tray_check.isChecked()
        config.ui.start_minimized = self.start_minimized_check.isChecked()
        config.ui.show_notifications = self.show_notifications_check.isChecked()

        # System
        config.system.start_on_boot = self.start_on_boot_check.isChecked()
        config.system.connect_on_start = self.connect_on_start_check.isChecked()

    def _save_and_accept(self) -> None:
        """Validate, save settings and close dialog."""
        self._save_settings()

        # Validate
        errors = self.config_manager.validate()
        if errors:
            # Show warnings but allow saving
            QMessageBox.warning(
                self,
                "Configuration Warnings",
                "The following issues were found:\n\n" + "\n".join(errors)
            )

        self.config_manager.save()
        self.accept()
