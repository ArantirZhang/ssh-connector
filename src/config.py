"""Configuration for SSH Connector - Fixed server settings."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Fixed SSH server configuration
SSH_HOST = "we3d.com.cn"
SSH_PORT = 22
SSH_USER = "tunneluser"
SSH_KEY_PATH = "~/.ssh/tunnel_key"
KEEPALIVE_INTERVAL = 60
KEEPALIVE_COUNT_MAX = 3

# Remote port range
REMOTE_PORT_MIN = 12000
REMOTE_PORT_MAX = 13000


@dataclass
class TunnelConfig:
    """Port forwarding configuration."""
    local_port: int = 80
    remote_port: int = 12000
    enabled: bool = False


@dataclass
class AppConfig:
    """Application configuration."""
    tunnel: TunnelConfig = field(default_factory=TunnelConfig)

    # Reconnect settings
    auto_reconnect: bool = True
    reconnect_delay: float = 5.0
    max_reconnect_delay: float = 300.0


class ConfigManager:
    """Manages loading and saving configuration."""

    CONFIG_FILENAME = "config.json"

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            config_dir = self._get_default_config_dir()
        self.config_dir = Path(config_dir)
        self.config_path = self.config_dir / self.CONFIG_FILENAME
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
        """Load configuration from file."""
        if not self.config_path.exists():
            return self.config

        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)

            if "tunnel" in data:
                self.config.tunnel = TunnelConfig(**data["tunnel"])
            if "auto_reconnect" in data:
                self.config.auto_reconnect = data["auto_reconnect"]
            if "reconnect_delay" in data:
                self.config.reconnect_delay = data["reconnect_delay"]

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error loading config: {e}")

        return self.config

    def save(self) -> None:
        """Save current configuration to file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "tunnel": {
                "local_port": self.config.tunnel.local_port,
                "remote_port": self.config.tunnel.remote_port,
                "enabled": self.config.tunnel.enabled,
            },
            "auto_reconnect": self.config.auto_reconnect,
            "reconnect_delay": self.config.reconnect_delay,
        }
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_ssh_key_path(self) -> Path:
        """Get expanded SSH key path."""
        return Path(SSH_KEY_PATH).expanduser()
