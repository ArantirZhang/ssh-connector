"""Remote port forwarding (reverse tunnel) management."""

import logging
import socket
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

import paramiko

from .config import PortForwardRule

logger = logging.getLogger(__name__)


class TunnelState(Enum):
    """State of a port forwarding tunnel."""
    INACTIVE = "inactive"
    STARTING = "starting"
    ACTIVE = "active"
    ERROR = "error"


@dataclass
class TunnelStatus:
    """Status information for a tunnel."""
    rule: PortForwardRule
    state: TunnelState
    error_message: Optional[str] = None
    connections_count: int = 0


TunnelCallback = Callable[[PortForwardRule, TunnelState, Optional[str]], None]


class TunnelManager:
    """Manages remote port forwarding tunnels."""

    def __init__(self):
        """Initialize tunnel manager."""
        self._transport: Optional[paramiko.Transport] = None
        self._tunnels: dict[int, TunnelStatus] = {}  # keyed by remote_port
        self._tunnel_threads: dict[int, threading.Thread] = {}
        self._stop_events: dict[int, threading.Event] = {}
        self._callbacks: list[TunnelCallback] = []
        self._lock = threading.Lock()

    def set_transport(self, transport: Optional[paramiko.Transport]) -> None:
        """Set the SSH transport for tunnel creation.

        Args:
            transport: Active SSH transport or None to clear.
        """
        self._transport = transport

    def add_callback(self, callback: TunnelCallback) -> None:
        """Register a callback for tunnel state changes."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: TunnelCallback) -> None:
        """Remove a tunnel state callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_callbacks(
        self,
        rule: PortForwardRule,
        state: TunnelState,
        error: Optional[str] = None
    ) -> None:
        """Notify all callbacks of state change."""
        for callback in self._callbacks:
            try:
                callback(rule, state, error)
            except Exception as e:
                logger.error(f"Tunnel callback error: {e}")

    def start_tunnel(self, rule: PortForwardRule) -> bool:
        """Start a remote port forwarding tunnel.

        This creates a reverse tunnel: connections to remote_port on the
        server are forwarded to local_port on this machine.

        Args:
            rule: Port forwarding rule to establish.

        Returns:
            True if tunnel started successfully.
        """
        if not self._transport or not self._transport.is_active():
            logger.error("Cannot start tunnel: no active transport")
            return False

        with self._lock:
            if rule.remote_port in self._tunnels:
                status = self._tunnels[rule.remote_port]
                if status.state == TunnelState.ACTIVE:
                    logger.warning(f"Tunnel for remote port {rule.remote_port} already active")
                    return True

            self._tunnels[rule.remote_port] = TunnelStatus(
                rule=rule,
                state=TunnelState.STARTING
            )

        self._notify_callbacks(rule, TunnelState.STARTING)

        try:
            # Request remote port forwarding
            # When someone connects to remote_port on the server,
            # the connection is forwarded through our SSH connection
            self._transport.request_port_forward(
                address=rule.remote_bind_address,
                port=rule.remote_port,
            )

            # Start handler thread for incoming connections
            stop_event = threading.Event()
            self._stop_events[rule.remote_port] = stop_event

            handler_thread = threading.Thread(
                target=self._handle_tunnel_connections,
                args=(rule, stop_event),
                daemon=True,
                name=f"tunnel-{rule.remote_port}"
            )
            self._tunnel_threads[rule.remote_port] = handler_thread
            handler_thread.start()

            with self._lock:
                self._tunnels[rule.remote_port].state = TunnelState.ACTIVE

            self._notify_callbacks(rule, TunnelState.ACTIVE)
            logger.info(
                f"Started reverse tunnel: remote {rule.remote_bind_address}:{rule.remote_port} "
                f"-> local 127.0.0.1:{rule.local_port}"
            )
            return True

        except paramiko.SSHException as e:
            error_msg = f"Failed to start tunnel: {e}"
            logger.error(error_msg)

            with self._lock:
                self._tunnels[rule.remote_port] = TunnelStatus(
                    rule=rule,
                    state=TunnelState.ERROR,
                    error_message=error_msg
                )

            self._notify_callbacks(rule, TunnelState.ERROR, error_msg)
            return False

    def _handle_tunnel_connections(
        self,
        rule: PortForwardRule,
        stop_event: threading.Event
    ) -> None:
        """Handle incoming connections for a reverse tunnel.

        This runs in a separate thread and accepts forwarded connections
        from the SSH server, connecting them to the local port.
        """
        while not stop_event.is_set():
            try:
                # Accept a forwarded channel from the transport
                channel = self._transport.accept(timeout=1.0)
                if channel is None:
                    continue

                # Check if this is for our tunnel
                # In paramiko, accept() returns channels for all forwarded ports
                # We need to handle the connection

                # Start a thread to handle this connection
                conn_thread = threading.Thread(
                    target=self._forward_connection,
                    args=(channel, rule),
                    daemon=True
                )
                conn_thread.start()

                with self._lock:
                    if rule.remote_port in self._tunnels:
                        self._tunnels[rule.remote_port].connections_count += 1

            except Exception as e:
                if not stop_event.is_set():
                    logger.error(f"Error accepting tunnel connection: {e}")

    def _forward_connection(
        self,
        channel: paramiko.Channel,
        rule: PortForwardRule
    ) -> None:
        """Forward data between SSH channel and local socket."""
        local_sock = None
        try:
            # Connect to local port
            local_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            local_sock.connect(("127.0.0.1", rule.local_port))
            local_sock.setblocking(False)
            channel.setblocking(False)

            # Bidirectional forwarding
            while True:
                # Read from channel, write to socket
                try:
                    data = channel.recv(32768)
                    if len(data) == 0:
                        break
                    local_sock.sendall(data)
                except socket.error:
                    pass

                # Read from socket, write to channel
                try:
                    data = local_sock.recv(32768)
                    if len(data) == 0:
                        break
                    channel.sendall(data)
                except socket.error:
                    pass

        except Exception as e:
            logger.debug(f"Tunnel connection ended: {e}")
        finally:
            if local_sock:
                try:
                    local_sock.close()
                except Exception:
                    pass
            try:
                channel.close()
            except Exception:
                pass

    def stop_tunnel(self, remote_port: int) -> None:
        """Stop a specific tunnel.

        Args:
            remote_port: The remote port of the tunnel to stop.
        """
        with self._lock:
            if remote_port not in self._tunnels:
                return

            status = self._tunnels[remote_port]
            rule = status.rule

        # Signal handler thread to stop
        if remote_port in self._stop_events:
            self._stop_events[remote_port].set()
            del self._stop_events[remote_port]

        # Wait for thread to finish
        if remote_port in self._tunnel_threads:
            thread = self._tunnel_threads[remote_port]
            thread.join(timeout=2.0)
            del self._tunnel_threads[remote_port]

        # Cancel port forwarding
        if self._transport and self._transport.is_active():
            try:
                self._transport.cancel_port_forward(
                    address=rule.remote_bind_address,
                    port=remote_port
                )
            except Exception as e:
                logger.warning(f"Error canceling port forward: {e}")

        with self._lock:
            self._tunnels[remote_port] = TunnelStatus(
                rule=rule,
                state=TunnelState.INACTIVE
            )

        self._notify_callbacks(rule, TunnelState.INACTIVE)
        logger.info(f"Stopped tunnel for remote port {remote_port}")

    def stop_all_tunnels(self) -> None:
        """Stop all active tunnels."""
        with self._lock:
            ports = list(self._tunnels.keys())

        for port in ports:
            self.stop_tunnel(port)

    def get_tunnel_status(self, remote_port: int) -> Optional[TunnelStatus]:
        """Get status of a specific tunnel."""
        with self._lock:
            return self._tunnels.get(remote_port)

    def get_all_tunnel_statuses(self) -> list[TunnelStatus]:
        """Get status of all tunnels."""
        with self._lock:
            return list(self._tunnels.values())

    def start_all_tunnels(self, rules: list[PortForwardRule]) -> dict[int, bool]:
        """Start tunnels for all enabled rules.

        Args:
            rules: List of port forwarding rules.

        Returns:
            Dict mapping remote_port to success status.
        """
        results = {}
        for rule in rules:
            if rule.enabled:
                results[rule.remote_port] = self.start_tunnel(rule)
        return results
