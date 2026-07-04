from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from code_manager.application.config_service import CodeManagerService
from code_manager.domain.models import Application, Group, SystemProfile
from code_manager.presentation.dialogs import GroupDialog

GROUP_TABLE_ROW_HEIGHT = 36
GROUP_OPERATION_COLUMN_WIDTH = 260


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
        self.editing_cell: tuple[str, int] | None = None

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
        self.group_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.group_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.group_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.group_table.verticalHeader().setDefaultSectionSize(GROUP_TABLE_ROW_HEIGHT)
        self.group_table.verticalHeader().setMinimumSectionSize(GROUP_TABLE_ROW_HEIGHT)
        self.group_table.setColumnWidth(2, GROUP_OPERATION_COLUMN_WIDTH)
        self.group_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.group_table.setSelectionMode(QTableWidget.NoSelection)
        self.group_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.group_table.setFocusPolicy(Qt.NoFocus)
        self.group_table.cellDoubleClicked.connect(self.start_cell_edit)
        layout.addWidget(self.group_table, 1)
        layout.addWidget(self.status_label)
        self.setCentralWidget(root)

    def refresh_tables(self) -> None:
        system = self._system()
        self.group_table.setRowCount(len(system.groups))
        for row, group in enumerate(system.groups):
            editing_column = self._editing_column_for(group.english_name)
            self.group_table.removeCellWidget(row, 0)
            self.group_table.removeCellWidget(row, 1)
            if editing_column == 0:
                self.group_table.setCellWidget(
                    row,
                    0,
                    self._build_cell_editor(group.chinese_name, group.english_name, 0),
                )
            else:
                self.group_table.setItem(row, 0, QTableWidgetItem(group.chinese_name))
            if editing_column == 1:
                self.group_table.setCellWidget(
                    row,
                    1,
                    self._build_cell_editor(group.english_name, group.english_name, 1),
                )
            else:
                self.group_table.setItem(row, 1, QTableWidgetItem(group.english_name))
            self.group_table.setCellWidget(row, 2, self._build_group_operation_cell(row))
            self.group_table.setRowHeight(row, GROUP_TABLE_ROW_HEIGHT)
        self.group_table.setColumnWidth(2, GROUP_OPERATION_COLUMN_WIDTH)

    def _build_cell_editor(self, text: str, group_english_name: str, column: int) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        input_widget = QLineEdit(text)
        input_widget.setMinimumHeight(28)
        input_widget.setStyleSheet("QLineEdit { padding: 2px 6px; }")
        layout.addWidget(input_widget, 1)

        for label, handler in [
            ("×", self.cancel_cell_edit),
            ("√", self.confirm_cell_edit),
        ]:
            button = QPushButton(label)
            button.setFixedSize(26, 28)
            button.clicked.connect(
                lambda _checked=False, name=group_english_name, col=column, action=handler: action(
                    name,
                    col,
                )
            )
            layout.addWidget(button)
        return cell

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

    def start_cell_edit(self, row: int, column: int) -> None:
        if column not in (0, 1):
            return
        system = self._system()
        if row < 0 or row >= len(system.groups):
            return
        group = system.groups[row]
        self.editing_cell = (group.english_name, column)
        self.refresh_tables()
        self._focus_editing_cell(group.english_name, column)
        self.status_label.setText(f"正在编辑{self._cell_label(column)}: {group.english_name}")

    def cancel_cell_edit(self, group_english_name: str | None = None, column: int | None = None) -> None:
        self.editing_cell = None
        self.refresh_tables()
        if group_english_name:
            self.status_label.setText(f"已取消编辑{self._cell_label(column)}: {group_english_name}")

    def confirm_cell_edit(self, group_english_name: str | None = None, column: int | None = None) -> None:
        if not group_english_name or column not in (0, 1):
            return
        system = self._system()
        row = self._find_group_row(group_english_name)
        if row < 0:
            return
        editor = self.group_table.cellWidget(row, column)
        input_widget = editor.findChild(QLineEdit) if editor else None
        if not isinstance(input_widget, QLineEdit):
            return
        current = system.groups[row]
        updated = Group(
            chinese_name=input_widget.text().strip() if column == 0 else current.chinese_name,
            english_name=input_widget.text().strip() if column == 1 else current.english_name,
        )
        try:
            self.service.select_system(self.system_name)
            if updated.english_name.lower() != current.english_name.lower():
                system.groups[row] = updated
                system.applications = [
                    Application(
                        name=application.name,
                        repository_url=application.repository_url,
                        group_english_name=updated.english_name,
                        local_dir_name=application.local_dir_name,
                    )
                    if application.group_english_name.lower() == current.english_name.lower()
                    else application
                    for application in system.applications
                ]
                self.service.save()
            else:
                self.service.upsert_group(updated)
            self.editing_cell = None
            self._changed()
        except ValueError as exc:
            QMessageBox.warning(self, "保存失败", str(exc))

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

    def _find_group_row(self, english_name: str) -> int:
        normalized = english_name.lower()
        for row, group in enumerate(self._system().groups):
            if group.english_name.lower() == normalized:
                return row
        return -1

    def _focus_editing_cell(self, group_english_name: str, column: int) -> None:
        row = self._find_group_row(group_english_name)
        if row < 0:
            return
        editor = self.group_table.cellWidget(row, column)
        input_widget = editor.findChild(QLineEdit) if editor else None
        if isinstance(input_widget, QLineEdit):
            input_widget.setFocus()
            input_widget.selectAll()

    def _editing_column_for(self, group_english_name: str) -> int | None:
        if not self.editing_cell:
            return None
        editing_group_english_name, column = self.editing_cell
        if editing_group_english_name.lower() == group_english_name.lower():
            return column
        return None

    def _cell_label(self, column: int | None) -> str:
        return "中文名" if column == 0 else "英文名"

    def _confirm(self, message: str) -> bool:
        return (
            QMessageBox.question(self, "确认", message, QMessageBox.Yes | QMessageBox.No)
            == QMessageBox.Yes
        )
