"""SSH client implementation using paramiko."""

import logging
import socket
import threading
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

import paramiko

from .config import AppConfig

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """SSH connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    ERROR = "error"


class SSHClientError(Exception):
    """Base exception for SSH client errors."""
    pass


class AuthenticationError(SSHClientError):
    """Authentication failed."""
    pass


class ConnectionError(SSHClientError):
    """Connection failed."""
    pass


StateCallback = Callable[[ConnectionState, Optional[str]], None]


class SSHClient:
    """SSH client with key-based authentication and keepalive support."""

    def __init__(self, config: AppConfig):
        """Initialize SSH client.

        Args:
            config: Application configuration.
        """
        self.config = config
        self._client: Optional[paramiko.SSHClient] = None
        self._transport: Optional[paramiko.Transport] = None
        self._state = ConnectionState.DISCONNECTED
        self._state_callbacks: list[StateCallback] = []
        self._error_message: Optional[str] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state

    @property
    def error_message(self) -> Optional[str]:
        """Get last error message."""
        return self._error_message

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._state == ConnectionState.CONNECTED and self._is_transport_active()

    def _is_transport_active(self) -> bool:
        """Check if transport is active."""
        return (
            self._transport is not None
            and self._transport.is_active()
        )

    def add_state_callback(self, callback: StateCallback) -> None:
        """Register a callback for state changes.

        Args:
            callback: Function called with (new_state, error_message).
        """
        self._state_callbacks.append(callback)

    def remove_state_callback(self, callback: StateCallback) -> None:
        """Remove a state change callback."""
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)

    def _set_state(self, state: ConnectionState, error_message: Optional[str] = None) -> None:
        """Update connection state and notify callbacks."""
        self._state = state
        self._error_message = error_message
        for callback in self._state_callbacks:
            try:
                callback(state, error_message)
            except Exception as e:
                logger.error(f"State callback error: {e}")

    def connect(self, key_passphrase: Optional[str] = None) -> None:
        """Establish SSH connection.

        Args:
            key_passphrase: Optional passphrase for encrypted SSH key.

        Raises:
            AuthenticationError: If authentication fails.
            ConnectionError: If connection fails.
        """
        with self._lock:
            if self._state in (ConnectionState.CONNECTING, ConnectionState.CONNECTED):
                return

            self._set_state(ConnectionState.CONNECTING)

        try:
            # Create SSH client
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Load SSH key
            key_path = Path(self.config.ssh_key.path).expanduser()
            try:
                private_key = paramiko.RSAKey.from_private_key_file(
                    str(key_path),
                    password=key_passphrase
                )
            except paramiko.ssh_exception.PasswordRequiredException:
                raise AuthenticationError("SSH key requires a passphrase")
            except paramiko.ssh_exception.SSHException as e:
                # Try other key types
                private_key = self._try_load_key(key_path, key_passphrase)
                if private_key is None:
                    raise AuthenticationError(f"Failed to load SSH key: {e}")

            # Connect
            self._client.connect(
                hostname=self.config.server.hostname,
                port=self.config.server.port,
                username=self.config.server.username,
                pkey=private_key,
                timeout=self.config.connection.timeout_seconds,
                allow_agent=False,
                look_for_keys=False,
            )

            # Get transport and configure keepalive
            self._transport = self._client.get_transport()
            if self._transport:
                self._transport.set_keepalive(
                    self.config.connection.keepalive_interval_seconds
                )

            self._set_state(ConnectionState.CONNECTED)
            logger.info(f"Connected to {self.config.server.hostname}:{self.config.server.port}")

        except paramiko.AuthenticationException as e:
            self._cleanup()
            self._set_state(ConnectionState.ERROR, str(e))
            raise AuthenticationError(f"Authentication failed: {e}")

        except (socket.error, socket.timeout, paramiko.SSHException) as e:
            self._cleanup()
            self._set_state(ConnectionState.ERROR, str(e))
            raise ConnectionError(f"Connection failed: {e}")

    def _try_load_key(
        self,
        key_path: Path,
        passphrase: Optional[str]
    ) -> Optional[paramiko.PKey]:
        """Try loading key with different key types."""
        key_classes = [
            paramiko.RSAKey,
            paramiko.Ed25519Key,
            paramiko.ECDSAKey,
            paramiko.DSSKey,
        ]

        for key_class in key_classes:
            try:
                return key_class.from_private_key_file(str(key_path), password=passphrase)
            except (paramiko.ssh_exception.SSHException, ValueError):
                continue

        return None

    def disconnect(self) -> None:
        """Disconnect from SSH server."""
        with self._lock:
            if self._state == ConnectionState.DISCONNECTED:
                return

            self._set_state(ConnectionState.DISCONNECTING)

        self._cleanup()
        self._set_state(ConnectionState.DISCONNECTED)
        logger.info("Disconnected from SSH server")

    def _cleanup(self) -> None:
        """Clean up SSH resources."""
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        self._transport = None

    def get_transport(self) -> Optional[paramiko.Transport]:
        """Get the underlying transport for tunnel setup.

        Returns:
            Active transport or None if not connected.
        """
        if self._is_transport_active():
            return self._transport
        return None

    def check_connection(self) -> bool:
        """Check if connection is still alive.

        Returns:
            True if connected and responsive.
        """
        if not self._is_transport_active():
            return False

        try:
            # Send a keepalive to verify connection
            self._transport.send_ignore()
            return True
        except Exception:
            return False
