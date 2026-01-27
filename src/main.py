"""SSH Connector - Application entry point."""

import logging
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from .config import ConfigManager
from .ssh_client import SSHClient
from .tunnel_manager import TunnelManager
from .connection_monitor import ConnectionMonitor
from .ui.main_window import MainWindow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Application:
    """Main application controller."""

    def __init__(self):
        """Initialize the application."""
        # Load configuration
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load()

        # Create core components
        self.ssh_client = SSHClient(self.config)
        self.tunnel_manager = TunnelManager()
        self.connection_monitor = ConnectionMonitor(
            self.ssh_client,
            self.tunnel_manager,
            self.config
        )

        # Qt application
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setApplicationName("SSH Connector")
        self.qt_app.setOrganizationName("SSH Connector")

        # Create main window
        self.main_window = MainWindow(
            config_manager=self.config_manager,
            ssh_client=self.ssh_client,
            tunnel_manager=self.tunnel_manager,
            connection_monitor=self.connection_monitor
        )

    def run(self) -> int:
        """Run the application.

        Returns:
            Exit code.
        """
        logger.info("Starting SSH Connector")

        # Show window (unless configured to start minimized)
        if self.config.ui.start_minimized and self.config.ui.minimize_to_tray:
            self.main_window.hide()
        else:
            self.main_window.show()

        # Auto-connect if configured
        if self.config.system.connect_on_start:
            self.main_window.connect_action()

        # Run Qt event loop
        return self.qt_app.exec()

    def cleanup(self) -> None:
        """Clean up resources before exit."""
        logger.info("Shutting down SSH Connector")

        # Stop monitoring
        self.connection_monitor.stop()

        # Stop tunnels and disconnect
        self.tunnel_manager.stop_all_tunnels()
        self.ssh_client.disconnect()

        # Save configuration
        self.config_manager.save()


def main() -> int:
    """Application entry point."""
    app = Application()
    try:
        return app.run()
    finally:
        app.cleanup()


if __name__ == "__main__":
    sys.exit(main())
