from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from code_manager.application.config_service import CodeManagerService
from code_manager.domain.models import Group, SystemProfile
from code_manager.presentation.dialogs import GroupDialog


class GroupConfigWindow(QMainWindow):
    def __init__(
        self,
        service: CodeManagerService,
        system_name: str,
        on_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self.service = service
        self.system_name = system_name
        self.on_changed = on_changed

        self.group_table = QTableWidget(0, 3)
        self.status_label = QLabel("就绪")

        self.setWindowTitle(f"配置分组 - {system_name}")
        self._build_ui()
        self.refresh_tables()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addWidget(QLabel(f"系统: {self.system_name}"))

        button_row = QHBoxLayout()
        add_button = QPushButton("新增分组")
        add_button.clicked.connect(self.add_group)
        button_row.addWidget(add_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.group_table.setHorizontalHeaderLabels(["中文名", "英文名", "操作"])
        self.group_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.group_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.group_table.setSelectionMode(QTableWidget.NoSelection)
        self.group_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.group_table.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.group_table, 1)
        layout.addWidget(self.status_label)
        self.setCentralWidget(root)

    def refresh_tables(self) -> None:
        system = self._system()
        self.group_table.setRowCount(len(system.groups))
        for row, group in enumerate(system.groups):
            self.group_table.setItem(row, 0, QTableWidgetItem(group.chinese_name))
            self.group_table.setItem(row, 1, QTableWidgetItem(group.english_name))
            self.group_table.setCellWidget(row, 2, self._build_group_operation_cell(row))

    def _build_group_operation_cell(self, row: int) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        for label, handler in [
            ("编辑", lambda: self.edit_group(row)),
            ("删除", lambda: self.delete_group(row)),
        ]:
            button = QPushButton(label)
            button.clicked.connect(handler)
            layout.addWidget(button)
        layout.addStretch(1)
        return cell

    def add_group(self) -> None:
        dialog = GroupDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._save_group_from_dialog(dialog)

    def edit_group(self, row: int | None = None) -> None:
        system = self._system()
        row = self.group_table.currentRow() if row is None else row
        if row < 0:
            return
        dialog = GroupDialog(system.groups[row])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._save_group_from_dialog(dialog)

    def _save_group_from_dialog(self, dialog: GroupDialog) -> None:
        try:
            self.service.select_system(self.system_name)
            self.service.upsert_group(dialog.group())
            self._changed()
        except ValueError as exc:
            QMessageBox.warning(self, "保存失败", str(exc))

    def delete_group(self, row: int | None = None) -> None:
        system = self._system()
        row = self.group_table.currentRow() if row is None else row
        if row < 0:
            return
        group: Group = system.groups[row]
        if self._confirm(f"确定删除分组 {group.english_name} 吗？该分组下的应用会取消所属分组。"):
            self.service.select_system(self.system_name)
            self.service.delete_group(group.english_name)
            self._changed()

    def _changed(self) -> None:
        self.refresh_tables()
        self.status_label.setText("配置已更新")
        if self.on_changed:
            self.on_changed()

    def _system(self) -> SystemProfile:
        return self.service.config.get_system(self.system_name)

    def _confirm(self, message: str) -> bool:
        return (
            QMessageBox.question(self, "确认", message, QMessageBox.Yes | QMessageBox.No)
            == QMessageBox.Yes
        )
