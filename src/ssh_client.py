"""SSH client with reverse tunnel support."""

import logging
import socket
import threading
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

import paramiko

from .config import (
    SSH_HOST, SSH_PORT, SSH_USER, SSH_KEY_PATH,
    KEEPALIVE_INTERVAL, KEEPALIVE_COUNT_MAX
)

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """SSH connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


StateCallback = Callable[[ConnectionState, Optional[str]], None]


class SSHClient:
    """SSH client with reverse tunnel support."""

    def __init__(self):
        self._client: Optional[paramiko.SSHClient] = None
        self._transport: Optional[paramiko.Transport] = None
        self._state = ConnectionState.DISCONNECTED
        self._state_callbacks: list[StateCallback] = []
        self._error_message: Optional[str] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def error_message(self) -> Optional[str]:
        return self._error_message

    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED and self._is_transport_active()

    def _is_transport_active(self) -> bool:
        return self._transport is not None and self._transport.is_active()

    def add_state_callback(self, callback: StateCallback) -> None:
        self._state_callbacks.append(callback)

    def _set_state(self, state: ConnectionState, error_message: Optional[str] = None) -> None:
        self._state = state
        self._error_message = error_message
        for callback in self._state_callbacks:
            try:
                callback(state, error_message)
            except Exception as e:
                logger.error(f"State callback error: {e}")

    def connect(self) -> None:
        """Connect to the SSH server."""
        with self._lock:
            if self._state in (ConnectionState.CONNECTING, ConnectionState.CONNECTED):
                return
            self._set_state(ConnectionState.CONNECTING)

        try:
            # Load SSH key
            key_path = Path(SSH_KEY_PATH).expanduser()
            if not key_path.exists():
                raise FileNotFoundError(f"SSH key not found: {key_path}")

            private_key = self._load_key(key_path)
            if private_key is None:
                raise Exception("Failed to load SSH key")

            # Create client and connect
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            logger.info(f"Connecting to {SSH_USER}@{SSH_HOST}:{SSH_PORT}")

            self._client.connect(
                hostname=SSH_HOST,
                port=SSH_PORT,
                username=SSH_USER,
                pkey=private_key,
                timeout=30,
                allow_agent=False,
                look_for_keys=False,
            )

            # Configure keepalive
            self._transport = self._client.get_transport()
            if self._transport:
                self._transport.set_keepalive(KEEPALIVE_INTERVAL)

            self._set_state(ConnectionState.CONNECTED)
            logger.info("Connected successfully")

        except Exception as e:
            self._cleanup()
            error_msg = str(e)
            self._set_state(ConnectionState.ERROR, error_msg)
            logger.error(f"Connection failed: {error_msg}")
            raise

    def _load_key(self, key_path: Path) -> Optional[paramiko.PKey]:
        """Try loading key with different key types."""
        key_classes = [
            paramiko.Ed25519Key,
            paramiko.RSAKey,
            paramiko.ECDSAKey,
        ]
        for key_class in key_classes:
            try:
                return key_class.from_private_key_file(str(key_path))
            except (paramiko.ssh_exception.SSHException, ValueError):
                continue
        return None

    def disconnect(self) -> None:
        """Disconnect from SSH server."""
        with self._lock:
            if self._state == ConnectionState.DISCONNECTED:
                return

        self._cleanup()
        self._set_state(ConnectionState.DISCONNECTED)
        logger.info("Disconnected")

    def _cleanup(self) -> None:
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        self._transport = None

    def get_transport(self) -> Optional[paramiko.Transport]:
        if self._is_transport_active():
            return self._transport
        return None

    def check_connection(self) -> bool:
        """Check if connection is still alive."""
        if not self._is_transport_active():
            return False
        try:
            self._transport.send_ignore()
            return True
        except Exception:
            return False

    def start_reverse_tunnel(self, local_port: int, remote_port: int) -> bool:
        """Start a reverse tunnel: remote_port on server -> local_port on this machine."""
        if not self._is_transport_active():
            logger.error("Cannot start tunnel: not connected")
            return False

        try:
            self._transport.request_port_forward("127.0.0.1", remote_port)

            # Start handler thread
            thread = threading.Thread(
                target=self._tunnel_handler,
                args=(local_port, remote_port),
                daemon=True,
                name=f"tunnel-{remote_port}"
            )
            thread.start()

            logger.info(f"Reverse tunnel started: remote:{remote_port} -> local:{local_port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start tunnel: {e}")
            return False

    def _tunnel_handler(self, local_port: int, remote_port: int) -> None:
        """Handle incoming tunnel connections."""
        while self._is_transport_active():
            try:
                channel = self._transport.accept(timeout=1.0)
                if channel is None:
                    continue

                # Forward to local port
                thread = threading.Thread(
                    target=self._forward_channel,
                    args=(channel, local_port),
                    daemon=True
                )
                thread.start()

            except Exception as e:
                if self._is_transport_active():
                    logger.debug(f"Tunnel accept error: {e}")

    def _forward_channel(self, channel: paramiko.Channel, local_port: int) -> None:
        """Forward channel data to local port."""
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", local_port))

            while True:
                # Channel -> Socket
                if channel.recv_ready():
                    data = channel.recv(32768)
                    if not data:
                        break
                    sock.sendall(data)

                # Socket -> Channel
                sock.setblocking(False)
                try:
                    data = sock.recv(32768)
                    if not data:
                        break
                    channel.sendall(data)
                except BlockingIOError:
                    pass
                finally:
                    sock.setblocking(True)

                if channel.closed:
                    break

        except Exception as e:
            logger.debug(f"Forward ended: {e}")
        finally:
            if sock:
                sock.close()
            channel.close()

    def stop_reverse_tunnel(self, remote_port: int) -> None:
        """Stop a reverse tunnel."""
        if self._is_transport_active():
            try:
                self._transport.cancel_port_forward("127.0.0.1", remote_port)
                logger.info(f"Tunnel stopped: remote:{remote_port}")
            except Exception as e:
                logger.warning(f"Error stopping tunnel: {e}")
