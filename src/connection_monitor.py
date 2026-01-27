"""Connection monitoring and auto-reconnect logic."""

import logging
import threading
import time
from enum import Enum
from typing import Callable, Optional

from .config import AppConfig, PortForwardRule
from .ssh_client import ConnectionState, SSHClient
from .tunnel_manager import TunnelManager

logger = logging.getLogger(__name__)


class MonitorState(Enum):
    """Connection monitor states."""
    STOPPED = "stopped"
    RUNNING = "running"
    RECONNECTING = "reconnecting"


ReconnectCallback = Callable[[int, float], None]  # attempt, delay


class ConnectionMonitor:
    """Monitors SSH connection and handles auto-reconnect."""

    def __init__(
        self,
        ssh_client: SSHClient,
        tunnel_manager: TunnelManager,
        config: AppConfig
    ):
        """Initialize connection monitor.

        Args:
            ssh_client: SSH client to monitor.
            tunnel_manager: Tunnel manager for re-establishing tunnels.
            config: Application configuration.
        """
        self.ssh_client = ssh_client
        self.tunnel_manager = tunnel_manager
        self.config = config

        self._state = MonitorState.STOPPED
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._reconnect_callbacks: list[ReconnectCallback] = []
        self._current_attempt = 0
        self._key_passphrase: Optional[str] = None

    @property
    def state(self) -> MonitorState:
        """Get current monitor state."""
        return self._state

    @property
    def reconnect_attempt(self) -> int:
        """Get current reconnect attempt number."""
        return self._current_attempt

    def add_reconnect_callback(self, callback: ReconnectCallback) -> None:
        """Register a callback for reconnect events."""
        self._reconnect_callbacks.append(callback)

    def remove_reconnect_callback(self, callback: ReconnectCallback) -> None:
        """Remove a reconnect callback."""
        if callback in self._reconnect_callbacks:
            self._reconnect_callbacks.remove(callback)

    def _notify_reconnect(self, attempt: int, delay: float) -> None:
        """Notify callbacks of reconnect attempt."""
        for callback in self._reconnect_callbacks:
            try:
                callback(attempt, delay)
            except Exception as e:
                logger.error(f"Reconnect callback error: {e}")

    def start(self, key_passphrase: Optional[str] = None) -> None:
        """Start the connection monitor.

        Args:
            key_passphrase: SSH key passphrase for reconnection.
        """
        if self._state != MonitorState.STOPPED:
            return

        self._key_passphrase = key_passphrase
        self._stop_event.clear()
        self._current_attempt = 0
        self._state = MonitorState.RUNNING

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="connection-monitor"
        )
        self._monitor_thread.start()
        logger.info("Connection monitor started")

    def stop(self) -> None:
        """Stop the connection monitor."""
        if self._state == MonitorState.STOPPED:
            return

        self._stop_event.set()

        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
            self._monitor_thread = None

        self._state = MonitorState.STOPPED
        self._current_attempt = 0
        logger.info("Connection monitor stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        check_interval = self.config.connection.keepalive_interval_seconds

        while not self._stop_event.is_set():
            # Wait for check interval
            if self._stop_event.wait(timeout=check_interval):
                break

            # Check connection health
            if self.ssh_client.state == ConnectionState.CONNECTED:
                if not self.ssh_client.check_connection():
                    logger.warning("Connection check failed, connection may be lost")
                    self._handle_disconnect()

            elif self.ssh_client.state in (ConnectionState.DISCONNECTED, ConnectionState.ERROR):
                if self.config.reconnect.enabled:
                    self._handle_disconnect()

    def _handle_disconnect(self) -> None:
        """Handle connection loss and attempt reconnection."""
        if not self.config.reconnect.enabled:
            return

        self._state = MonitorState.RECONNECTING

        # Stop existing tunnels
        self.tunnel_manager.stop_all_tunnels()

        # Calculate delay with exponential backoff
        delay = self._calculate_backoff_delay()

        max_attempts = self.config.reconnect.max_attempts

        while not self._stop_event.is_set():
            self._current_attempt += 1

            # Check if we've exceeded max attempts (0 = infinite)
            if max_attempts > 0 and self._current_attempt > max_attempts:
                logger.error(f"Max reconnect attempts ({max_attempts}) exceeded")
                self._state = MonitorState.RUNNING
                return

            logger.info(f"Reconnect attempt {self._current_attempt}, waiting {delay:.1f}s")
            self._notify_reconnect(self._current_attempt, delay)

            # Wait before attempting
            if self._stop_event.wait(timeout=delay):
                break

            # Attempt reconnection
            try:
                self.ssh_client.disconnect()  # Clean up any stale connection
                self.ssh_client.connect(self._key_passphrase)

                # Connection successful, re-establish tunnels
                if self.ssh_client.is_connected:
                    logger.info("Reconnection successful")
                    self._current_attempt = 0
                    self._state = MonitorState.RUNNING

                    # Set transport for tunnels
                    transport = self.ssh_client.get_transport()
                    self.tunnel_manager.set_transport(transport)

                    # Restart all enabled tunnels
                    self.tunnel_manager.start_all_tunnels(
                        self.config.port_forwarding_rules
                    )
                    return

            except Exception as e:
                logger.warning(f"Reconnect attempt {self._current_attempt} failed: {e}")

            # Calculate next delay with backoff
            delay = self._calculate_backoff_delay()

    def _calculate_backoff_delay(self) -> float:
        """Calculate delay with exponential backoff."""
        if self._current_attempt == 0:
            return self.config.reconnect.initial_delay_seconds

        delay = (
            self.config.reconnect.initial_delay_seconds
            * (self.config.reconnect.backoff_multiplier ** self._current_attempt)
        )

        return min(delay, self.config.reconnect.max_delay_seconds)

    def reset_reconnect_counter(self) -> None:
        """Reset the reconnect attempt counter."""
        self._current_attempt = 0
