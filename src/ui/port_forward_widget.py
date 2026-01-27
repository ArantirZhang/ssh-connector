"""Port forwarding rules management widget."""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QDialog,
    QFormLayout,
    QSpinBox,
    QLineEdit,
    QCheckBox,
    QDialogButtonBox,
    QHeaderView,
    QAbstractItemView,
)

from ..config import PortForwardRule


class PortForwardWidget(QWidget):
    """Widget for managing port forwarding rules."""

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize port forward widget.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._rules: list[PortForwardRule] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the widget UI."""
        layout = QVBoxLayout(self)

        # Table for rules
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Enabled", "Local Port", "Remote Port", "Remote Address", "Description"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        # Set column resize modes
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()

        add_button = QPushButton("Add Rule")
        add_button.clicked.connect(self._add_rule)
        button_layout.addWidget(add_button)

        edit_button = QPushButton("Edit Rule")
        edit_button.clicked.connect(self._edit_rule)
        button_layout.addWidget(edit_button)

        remove_button = QPushButton("Remove Rule")
        remove_button.clicked.connect(self._remove_rule)
        button_layout.addWidget(remove_button)

        button_layout.addStretch()

        layout.addLayout(button_layout)

    def set_rules(self, rules: list[PortForwardRule]) -> None:
        """Set the port forwarding rules to display.

        Args:
            rules: List of port forwarding rules.
        """
        self._rules = list(rules)
        self._refresh_table()

    def get_rules(self) -> list[PortForwardRule]:
        """Get the current port forwarding rules.

        Returns:
            List of port forwarding rules.
        """
        return list(self._rules)

    def _refresh_table(self) -> None:
        """Refresh the table with current rules."""
        self.table.setRowCount(len(self._rules))

        for row, rule in enumerate(self._rules):
            # Enabled checkbox
            enabled_item = QTableWidgetItem()
            enabled_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            enabled_item.setCheckState(
                Qt.CheckState.Checked if rule.enabled else Qt.CheckState.Unchecked
            )
            self.table.setItem(row, 0, enabled_item)

            # Local port
            self.table.setItem(row, 1, QTableWidgetItem(str(rule.local_port)))

            # Remote port
            self.table.setItem(row, 2, QTableWidgetItem(str(rule.remote_port)))

            # Remote address
            self.table.setItem(row, 3, QTableWidgetItem(rule.remote_bind_address))

            # Description
            self.table.setItem(row, 4, QTableWidgetItem(rule.description))

    def _sync_from_table(self) -> None:
        """Sync rules from table state (for enabled checkboxes)."""
        for row in range(self.table.rowCount()):
            enabled_item = self.table.item(row, 0)
            if enabled_item and row < len(self._rules):
                self._rules[row].enabled = (
                    enabled_item.checkState() == Qt.CheckState.Checked
                )

    def _add_rule(self) -> None:
        """Add a new port forwarding rule."""
        dialog = PortForwardEditDialog(parent=self)
        if dialog.exec():
            rule = dialog.get_rule()
            self._rules.append(rule)
            self._refresh_table()

    def _edit_rule(self) -> None:
        """Edit the selected port forwarding rule."""
        self._sync_from_table()

        row = self.table.currentRow()
        if row < 0 or row >= len(self._rules):
            return

        dialog = PortForwardEditDialog(self._rules[row], parent=self)
        if dialog.exec():
            self._rules[row] = dialog.get_rule()
            self._refresh_table()

    def _remove_rule(self) -> None:
        """Remove the selected port forwarding rule."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self._rules):
            return

        del self._rules[row]
        self._refresh_table()


class PortForwardEditDialog(QDialog):
    """Dialog for adding/editing a port forwarding rule."""

    def __init__(
        self,
        rule: Optional[PortForwardRule] = None,
        parent: Optional[QWidget] = None
    ):
        """Initialize edit dialog.

        Args:
            rule: Existing rule to edit, or None for new rule.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._rule = rule
        self._setup_ui()

        if rule:
            self._load_rule(rule)

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Port Forwarding Rule")
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.local_port_spin = QSpinBox()
        self.local_port_spin.setRange(1, 65535)
        self.local_port_spin.setValue(22)
        form_layout.addRow("Local Port:", self.local_port_spin)

        self.remote_port_spin = QSpinBox()
        self.remote_port_spin.setRange(1, 65535)
        self.remote_port_spin.setValue(2222)
        form_layout.addRow("Remote Port:", self.remote_port_spin)

        self.remote_address_edit = QLineEdit()
        self.remote_address_edit.setText("127.0.0.1")
        self.remote_address_edit.setPlaceholderText("Remote bind address")
        form_layout.addRow("Remote Address:", self.remote_address_edit)

        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Optional description")
        form_layout.addRow("Description:", self.description_edit)

        self.enabled_check = QCheckBox("Enabled")
        self.enabled_check.setChecked(True)
        form_layout.addRow("", self.enabled_check)

        layout.addLayout(form_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_rule(self, rule: PortForwardRule) -> None:
        """Load rule values into UI."""
        self.local_port_spin.setValue(rule.local_port)
        self.remote_port_spin.setValue(rule.remote_port)
        self.remote_address_edit.setText(rule.remote_bind_address)
        self.description_edit.setText(rule.description)
        self.enabled_check.setChecked(rule.enabled)

    def get_rule(self) -> PortForwardRule:
        """Get the rule from UI values.

        Returns:
            Port forwarding rule with current values.
        """
        return PortForwardRule(
            local_port=self.local_port_spin.value(),
            remote_port=self.remote_port_spin.value(),
            remote_bind_address=self.remote_address_edit.text().strip() or "127.0.0.1",
            description=self.description_edit.text().strip(),
            enabled=self.enabled_check.isChecked()
        )
