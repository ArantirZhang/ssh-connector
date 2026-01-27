"""Configuration management for SSH Connector."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class PortForwardRule:
    """A single port forwarding rule."""
    local_port: int
    remote_port: int
    remote_bind_address: str = "127.0.0.1"
    enabled: bool = True
    description: str = ""


@dataclass
class ServerConfig:
    """SSH server connection settings."""
    hostname: str = ""
    port: int = 22
    username: str = ""


@dataclass
class SSHKeyConfig:
    """SSH key authentication settings."""
    path: str = ""
    passphrase_in_keyring: bool = False


@dataclass
class ReconnectConfig:
    """Auto-reconnect settings."""
    enabled: bool = True
    max_attempts: int = 0  # 0 = infinite
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 300.0
    backoff_multiplier: float = 2.0


@dataclass
class ConnectionConfig:
    """Connection behavior settings."""
    timeout_seconds: int = 30
    keepalive_interval_seconds: int = 30
    keepalive_count_max: int = 3


@dataclass
class UIConfig:
    """UI behavior settings."""
    minimize_to_tray: bool = True
    start_minimized: bool = False
    show_notifications: bool = True


@dataclass
class SystemConfig:
    """System integration settings."""
    start_on_boot: bool = False
    connect_on_start: bool = False


@dataclass
class AppConfig:
    """Complete application configuration."""
    server: ServerConfig = field(default_factory=ServerConfig)
    ssh_key: SSHKeyConfig = field(default_factory=SSHKeyConfig)
    port_forwarding_rules: list[PortForwardRule] = field(default_factory=list)
    reconnect: ReconnectConfig = field(default_factory=ReconnectConfig)
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    system: SystemConfig = field(default_factory=SystemConfig)


class ConfigManager:
    """Manages loading, saving, and validating configuration."""

    DEFAULT_CONFIG_FILENAME = "config.json"

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize config manager.

        Args:
            config_dir: Directory to store config. Defaults to platform-appropriate location.
        """
        if config_dir is None:
            config_dir = self._get_default_config_dir()
        self.config_dir = Path(config_dir)
        self.config_path = self.config_dir / self.DEFAULT_CONFIG_FILENAME
        self.config = AppConfig()

    def _get_default_config_dir(self) -> Path:
        """Get platform-appropriate config directory."""
        if os.name == "nt":  # Windows
            base = Path(os.environ.get("APPDATA", Path.home()))
        elif os.name == "posix":
            if "darwin" in os.uname().sysname.lower():  # macOS
                base = Path.home() / "Library" / "Application Support"
            else:  # Linux
                base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        else:
            base = Path.home()
        return base / "ssh-connector"

    def load(self) -> AppConfig:
        """Load configuration from file.

        Returns:
            Loaded configuration, or defaults if file doesn't exist.
        """
        if not self.config_path.exists():
            return self.config

        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)
            self.config = self._dict_to_config(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Log error and return defaults
            print(f"Error loading config: {e}")

        return self.config

    def save(self) -> None:
        """Save current configuration to file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        data = self._config_to_dict(self.config)
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=2)

    def _dict_to_config(self, data: dict) -> AppConfig:
        """Convert dictionary to AppConfig."""
        config = AppConfig()

        if "server" in data:
            config.server = ServerConfig(**data["server"])

        if "ssh_key" in data:
            config.ssh_key = SSHKeyConfig(**data["ssh_key"])

        if "port_forwarding" in data and "rules" in data["port_forwarding"]:
            config.port_forwarding_rules = [
                PortForwardRule(**rule) for rule in data["port_forwarding"]["rules"]
            ]

        if "reconnect" in data:
            config.reconnect = ReconnectConfig(**data["reconnect"])

        if "connection" in data:
            config.connection = ConnectionConfig(**data["connection"])

        if "ui" in data:
            config.ui = UIConfig(**data["ui"])

        if "system" in data:
            config.system = SystemConfig(**data["system"])

        return config

    def _config_to_dict(self, config: AppConfig) -> dict:
        """Convert AppConfig to dictionary."""
        return {
            "server": {
                "hostname": config.server.hostname,
                "port": config.server.port,
                "username": config.server.username,
            },
            "ssh_key": {
                "path": config.ssh_key.path,
                "passphrase_in_keyring": config.ssh_key.passphrase_in_keyring,
            },
            "port_forwarding": {
                "rules": [
                    {
                        "local_port": rule.local_port,
                        "remote_port": rule.remote_port,
                        "remote_bind_address": rule.remote_bind_address,
                        "enabled": rule.enabled,
                        "description": rule.description,
                    }
                    for rule in config.port_forwarding_rules
                ]
            },
            "reconnect": {
                "enabled": config.reconnect.enabled,
                "max_attempts": config.reconnect.max_attempts,
                "initial_delay_seconds": config.reconnect.initial_delay_seconds,
                "max_delay_seconds": config.reconnect.max_delay_seconds,
                "backoff_multiplier": config.reconnect.backoff_multiplier,
            },
            "connection": {
                "timeout_seconds": config.connection.timeout_seconds,
                "keepalive_interval_seconds": config.connection.keepalive_interval_seconds,
                "keepalive_count_max": config.connection.keepalive_count_max,
            },
            "ui": {
                "minimize_to_tray": config.ui.minimize_to_tray,
                "start_minimized": config.ui.start_minimized,
                "show_notifications": config.ui.show_notifications,
            },
            "system": {
                "start_on_boot": config.system.start_on_boot,
                "connect_on_start": config.system.connect_on_start,
            },
        }

    def validate(self) -> list[str]:
        """Validate current configuration.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        if not self.config.server.hostname:
            errors.append("Server hostname is required")

        if not self.config.server.username:
            errors.append("Username is required")

        if not self.config.ssh_key.path:
            errors.append("SSH key path is required")
        elif not Path(self.config.ssh_key.path).exists():
            errors.append(f"SSH key file not found: {self.config.ssh_key.path}")

        if self.config.server.port < 1 or self.config.server.port > 65535:
            errors.append("Server port must be between 1 and 65535")

        for i, rule in enumerate(self.config.port_forwarding_rules):
            if rule.local_port < 1 or rule.local_port > 65535:
                errors.append(f"Port forward rule {i+1}: local port must be between 1 and 65535")
            if rule.remote_port < 1 or rule.remote_port > 65535:
                errors.append(f"Port forward rule {i+1}: remote port must be between 1 and 65535")

        return errors
