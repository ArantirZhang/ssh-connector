"""Connection status display widget."""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
)

from ..ssh_client import ConnectionState
from ..tunnel_manager import TunnelState
from ..config import PortForwardRule


class StatusIndicator(QWidget):
    """Small colored status indicator."""

    COLORS = {
        "green": "#22c55e",
        "yellow": "#eab308",
        "red": "#ef4444",
        "gray": "#9ca3af",
    }

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize status indicator."""
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._color = "gray"
        self._update_style()

    def set_color(self, color: str) -> None:
        """Set indicator color."""
        self._color = color
        self._update_style()

    def _update_style(self) -> None:
        """Update the indicator style."""
        hex_color = self.COLORS.get(self._color, self.COLORS["gray"])
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {hex_color};
                border-radius: 6px;
            }}
        """)


class ConnectionStatusWidget(QWidget):
    """Widget displaying connection and tunnel status."""

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize connection status widget."""
        super().__init__(parent)
        self._tunnel_widgets: dict[int, QWidget] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Connection status
        conn_frame = QFrame()
        conn_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        conn_layout = QHBoxLayout(conn_frame)

        self.conn_indicator = StatusIndicator()
        conn_layout.addWidget(self.conn_indicator)

        self.conn_label = QLabel("Disconnected")
        self.conn_label.setStyleSheet("font-weight: bold;")
        conn_layout.addWidget(self.conn_label)

        conn_layout.addStretch()

        layout.addWidget(conn_frame)

        # Tunnels section
        tunnels_label = QLabel("Port Forwarding:")
        tunnels_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        layout.addWidget(tunnels_label)

        # Scroll area for tunnels
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(150)
        scroll.setFrameStyle(QFrame.Shape.NoFrame)

        self.tunnels_container = QWidget()
        self.tunnels_layout = QVBoxLayout(self.tunnels_container)
        self.tunnels_layout.setContentsMargins(0, 0, 0, 0)
        self.tunnels_layout.setSpacing(4)

        self.no_tunnels_label = QLabel("No port forwarding rules configured")
        self.no_tunnels_label.setStyleSheet("color: #6b7280; font-style: italic;")
        self.tunnels_layout.addWidget(self.no_tunnels_label)

        self.tunnels_layout.addStretch()

        scroll.setWidget(self.tunnels_container)
        layout.addWidget(scroll)

    def set_connection_state(self, state: ConnectionState) -> None:
        """Update the connection state display.

        Args:
            state: New connection state.
        """
        state_config = {
            ConnectionState.DISCONNECTED: ("gray", "Disconnected"),
            ConnectionState.CONNECTING: ("yellow", "Connecting..."),
            ConnectionState.CONNECTED: ("green", "Connected"),
            ConnectionState.DISCONNECTING: ("yellow", "Disconnecting..."),
            ConnectionState.ERROR: ("red", "Error"),
        }

        color, text = state_config.get(state, ("gray", "Unknown"))
        self.conn_indicator.set_color(color)
        self.conn_label.setText(text)

    def update_tunnel_status(
        self,
        rule: PortForwardRule,
        state: TunnelState,
        error: Optional[str] = None
    ) -> None:
        """Update status for a specific tunnel.

        Args:
            rule: Port forwarding rule.
            state: New tunnel state.
            error: Error message if state is ERROR.
        """
        # Hide "no tunnels" label
        self.no_tunnels_label.hide()

        # Get or create widget for this tunnel
        if rule.remote_port not in self._tunnel_widgets:
            widget = self._create_tunnel_widget(rule)
            self._tunnel_widgets[rule.remote_port] = widget
            # Insert before the stretch
            self.tunnels_layout.insertWidget(
                self.tunnels_layout.count() - 1,
                widget
            )

        widget = self._tunnel_widgets[rule.remote_port]
        indicator = widget.findChild(StatusIndicator)
        label = widget.findChild(QLabel)

        # Update indicator color
        state_colors = {
            TunnelState.INACTIVE: "gray",
            TunnelState.STARTING: "yellow",
            TunnelState.ACTIVE: "green",
            TunnelState.ERROR: "red",
        }
        indicator.set_color(state_colors.get(state, "gray"))

        # Update label
        status_text = f":{rule.local_port} → :{rule.remote_port}"
        if rule.description:
            status_text += f" ({rule.description})"

        if state == TunnelState.ERROR and error:
            status_text += f" - {error}"

        label.setText(status_text)

    def _create_tunnel_widget(self, rule: PortForwardRule) -> QWidget:
        """Create a widget for displaying tunnel status."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 2, 4, 2)

        indicator = StatusIndicator()
        layout.addWidget(indicator)

        label = QLabel()
        layout.addWidget(label)

        layout.addStretch()

        return widget

    def clear_tunnels(self) -> None:
        """Clear all tunnel status displays."""
        for widget in self._tunnel_widgets.values():
            widget.deleteLater()
        self._tunnel_widgets.clear()
        self.no_tunnels_label.show()
