from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QDialog,
    QFileDialog,
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
from code_manager.domain.models import SystemProfile
from code_manager.infrastructure.git_service import GitService
from code_manager.presentation.dialogs import SystemDialog
from code_manager.presentation.system_detail_window import SystemDetailWindow

SYSTEM_NAME_COLUMN_WIDTH = 170
SYSTEM_TABLE_ROW_HEIGHT = 36
SYSTEM_OPERATION_COLUMN_WIDTH = 300


class MainWindow(QMainWindow):
    def __init__(
        self,
        service: CodeManagerService | None = None,
        git_service: GitService | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("系统管理")
        self.service = service or CodeManagerService()
        self.git_service = git_service or GitService()
        self.detail_windows: dict[str, SystemDetailWindow] = {}
        self.editing_cell: tuple[str, int] | None = None

        self.system_table = QTableWidget(0, 3)
        self.status_label = QLabel("就绪")

        self._build_ui()
        self.resize(720, 420)
        self.refresh_table()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(QLabel("系统列表"))

        button_row = QHBoxLayout()
        for label, handler in [
            ("新增系统", self.add_system),
            ("导入系统", self.import_system_from_yaml),
        ]:
            button = QPushButton(label)
            button.clicked.connect(handler)
            button_row.addWidget(button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.system_table.setHorizontalHeaderLabels(["系统名称", "本地代码路径", "操作"])
        self.system_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.system_table.horizontalHeader().setStretchLastSection(True)
        self.system_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.system_table.verticalHeader().setDefaultSectionSize(SYSTEM_TABLE_ROW_HEIGHT)
        self.system_table.verticalHeader().setMinimumSectionSize(SYSTEM_TABLE_ROW_HEIGHT)
        self.system_table.setColumnWidth(0, SYSTEM_NAME_COLUMN_WIDTH)
        self.system_table.setColumnWidth(1, 200)
        self.system_table.setColumnWidth(2, SYSTEM_OPERATION_COLUMN_WIDTH)
        self.system_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.system_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.system_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.system_table.setFocusPolicy(Qt.NoFocus)
        self.system_table.setStyleSheet("QTableWidget::item:focus { outline: none; }")
        self.system_table.cellDoubleClicked.connect(self.start_cell_edit)
        layout.addWidget(self.system_table, 1)
        layout.addWidget(self.status_label)
        self.setCentralWidget(root)

    def refresh_table(self) -> None:
        self.system_table.blockSignals(True)
        self.system_table.clearContents()
        self.system_table.setRowCount(len(self.service.config.systems))
        for row, system in enumerate(self.service.config.systems):
            editing_column = self._editing_column_for(system.name)
            self.system_table.removeCellWidget(row, 0)
            self.system_table.removeCellWidget(row, 1)
            if editing_column == 0:
                self.system_table.takeItem(row, 0)
                self.system_table.setCellWidget(
                    row,
                    0,
                    self._build_cell_editor(system.name, system.name, 0),
                )
            else:
                self.system_table.setItem(row, 0, self._read_only_item(system.name))

            if editing_column == 1:
                self.system_table.takeItem(row, 1)
                self.system_table.setCellWidget(
                    row,
                    1,
                    self._build_cell_editor(str(system.code_root), system.name, 1),
                )
            else:
                self.system_table.setItem(row, 1, self._read_only_item(str(system.code_root)))

            self.system_table.setCellWidget(row, 2, self._build_operation_cell(system.name))
            self.system_table.setRowHeight(row, SYSTEM_TABLE_ROW_HEIGHT)
        self.system_table.setColumnWidth(0, SYSTEM_NAME_COLUMN_WIDTH)
        self.system_table.setColumnWidth(2, SYSTEM_OPERATION_COLUMN_WIDTH)
        self.system_table.clearSelection()
        self.system_table.setCurrentCell(-1, -1)
        self.system_table.blockSignals(False)
        self.system_table.viewport().update()
        QApplication.processEvents()

    def _read_only_item(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item

    def _build_cell_editor(self, text: str, system_name: str, column: int) -> QWidget:
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
                lambda _checked=False, name=system_name, col=column, action=handler: action(
                    name,
                    col,
                )
            )
            layout.addWidget(button)
        return cell

    def _build_operation_cell(self, system_name: str) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        for label, handler in [
            ("进入", self.open_system_detail),
            ("编辑", self.edit_system),
            ("删除", self.delete_system),
            ("导出", self.export_system_to_yaml),
        ]:
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, name=system_name, action=handler: action(name))
            layout.addWidget(button)
        layout.addStretch(1)
        return cell

    def _build_edit_operation_cell(self, system_name: str) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        for label, handler in [
            ("确认", self.confirm_system_edit),
            ("取消", self.cancel_system_edit),
        ]:
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, name=system_name, action=handler: action(name))
            layout.addWidget(button)
        layout.addStretch(1)
        return cell

    def open_system_detail(self, system_name: str | None = None) -> None:
        system = self.service.config.get_system(system_name) if system_name else self._selected_system_or_none()
        if not system:
            QMessageBox.information(
                self,
                "请先选择系统",
                "请先选择一个系统。",
            )
            return
        existing_window = self.detail_windows.get(system.name)
        if existing_window:
            self._activate_detail_window(existing_window)
            self.status_label.setText(f"已切换到系统: {system.name}")
            return
        self.service.select_system(system.name)
        window = SystemDetailWindow(self.service, self.git_service, system.name)
        window.setAttribute(Qt.WA_DeleteOnClose, True)
        window.destroyed.connect(lambda _obj=None, name=system.name: self.detail_windows.pop(name, None))
        window.resize(1180, 720)
        window.show()
        self.detail_windows[system.name] = window
        self.status_label.setText(f"已打开系统: {system.name}")

    def _activate_detail_window(self, window: SystemDetailWindow) -> None:
        if window.isMinimized():
            window.showNormal()
        else:
            window.show()
        window.raise_()
        window.activateWindow()

    def add_system(self) -> None:
        dialog = SystemDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.service.upsert_system(dialog.system())
            self.refresh_table()
            self.status_label.setText("系统已新增")
        except ValueError as exc:
            QMessageBox.warning(self, "保存失败", str(exc))

    def edit_system(self, system_name: str | None = None) -> None:
        system = self.service.config.get_system(system_name) if system_name else self._selected_system_or_none()
        if not system:
            return
        dialog = SystemDialog(system)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            updated = dialog.system()
            updated.groups = system.groups
            updated.applications = system.applications
            if updated.name.lower() != system.name.lower():
                self.service.delete_system(system.name)
            self.service.upsert_system(updated)
            self.editing_cell = None
            self.refresh_table()
            self.status_label.setText("系统已更新")
        except ValueError as exc:
            QMessageBox.warning(self, "保存失败", str(exc))

    def import_system_from_yaml(self) -> None:
        file_name, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "导入系统",
            str(Path.home()),
            "YAML 文件 (*.yaml *.yml)",
        )
        if not file_name:
            return
        try:
            system = self.service.import_system_from_yaml(Path(file_name))
            self.refresh_table()
            self.status_label.setText(f"系统已导入: {system.name}")
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "导入失败", str(exc))

    def export_system_to_yaml(self, system_name: str | None = None) -> None:
        system = self.service.config.get_system(system_name) if system_name else self._selected_system_or_none()
        if not system:
            return
        file_name, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出系统",
            str(Path.home() / f"{system.name}.yaml"),
            "YAML 文件 (*.yaml *.yml)",
        )
        if not file_name:
            return
        yaml_file = Path(file_name)
        if yaml_file.suffix.lower() not in (".yaml", ".yml"):
            yaml_file = yaml_file.with_suffix(".yaml")
        try:
            self.service.export_system_to_yaml(system.name, yaml_file)
            self.status_label.setText(f"系统已导出: {yaml_file}")
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "导出失败", str(exc))

    def start_cell_edit(self, row: int, column: int) -> None:
        if column not in (0, 1) or row < 0 or row >= len(self.service.config.systems):
            return
        system = self.service.config.systems[row]
        self.editing_cell = (system.name, column)
        self.refresh_table()
        self._focus_editing_cell(system.name, column)
        self.status_label.setText(f"正在编辑{self._cell_label(column)}: {system.name}")

    def cancel_cell_edit(self, system_name: str | None = None, column: int | None = None) -> None:
        self.editing_cell = None
        self.refresh_table()
        if system_name:
            self.status_label.setText(f"已取消编辑{self._cell_label(column)}: {system_name}")

    def confirm_cell_edit(self, system_name: str | None = None, column: int | None = None) -> None:
        system = self.service.config.get_system(system_name) if system_name else self._selected_system_or_none()
        if not system or column not in (0, 1):
            return
        row = self._find_system_row(system.name)
        if row < 0:
            return
        editor = self.system_table.cellWidget(row, column)
        input_widget = editor.findChild(QLineEdit) if editor else None
        if not isinstance(input_widget, QLineEdit):
            return
        try:
            updated = SystemProfile(
                name=input_widget.text().strip() if column == 0 else system.name,
                code_root=Path(input_widget.text().strip()).expanduser()
                if column == 1
                else system.code_root,
            )
            updated.groups = system.groups
            updated.applications = system.applications
            if updated.name.lower() != system.name.lower():
                self.service.delete_system(system.name)
            self.service.upsert_system(updated)
            self.editing_cell = None
            self.refresh_table()
            self.status_label.setText(f"{self._cell_label(column)}已更新")
        except ValueError as exc:
            QMessageBox.warning(self, "保存失败", str(exc))

    def delete_system(self, system_name: str | None = None) -> None:
        system = self.service.config.get_system(system_name) if system_name else self._selected_system_or_none()
        if not system:
            return
        confirmed = (
            QMessageBox.question(
                self,
                "确认",
                f"确定删除系统 {system.name} 吗？",
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.Yes
        )
        if confirmed:
            self.service.delete_system(system.name)
            self.refresh_table()

    def _selected_system_or_none(self) -> SystemProfile | None:
        row = self.system_table.currentRow()
        if row < 0 or row >= len(self.service.config.systems):
            return None
        return self.service.config.systems[row]

    def _find_system_row(self, system_name: str) -> int:
        normalized = system_name.lower()
        for row, system in enumerate(self.service.config.systems):
            if system.name.lower() == normalized:
                return row
        return -1

    def _focus_editing_cell(self, system_name: str, column: int) -> None:
        row = self._find_system_row(system_name)
        if row < 0:
            return
        editor = self.system_table.cellWidget(row, column)
        input_widget = editor.findChild(QLineEdit) if editor else None
        if isinstance(input_widget, QLineEdit):
            input_widget.setFocus()
            input_widget.selectAll()

    def _editing_column_for(self, system_name: str) -> int | None:
        if not self.editing_cell:
            return None
        editing_system_name, column = self.editing_cell
        if editing_system_name.lower() == system_name.lower():
            return column
        return None

    def _cell_label(self, column: int | None) -> str:
        return "系统名称" if column == 0 else "本地代码路径"
