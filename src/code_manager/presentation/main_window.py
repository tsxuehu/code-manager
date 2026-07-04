from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
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
from code_manager.domain.models import SystemProfile
from code_manager.infrastructure.git_service import GitService
from code_manager.presentation.dialogs import SystemDialog
from code_manager.presentation.system_detail_window import SystemDetailWindow


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
        ]:
            button = QPushButton(label)
            button.clicked.connect(handler)
            button_row.addWidget(button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.system_table.setHorizontalHeaderLabels(["系统名称", "本地代码路径", "操作"])
        self.system_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.system_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.system_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.system_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.system_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.system_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.system_table.setFocusPolicy(Qt.NoFocus)
        self.system_table.setStyleSheet("QTableWidget::item:focus { outline: none; }")
        self.system_table.cellDoubleClicked.connect(lambda _row, _column: self.open_system_detail())
        layout.addWidget(self.system_table, 1)
        layout.addWidget(self.status_label)
        self.setCentralWidget(root)

    def refresh_table(self) -> None:
        self.system_table.blockSignals(True)
        self.system_table.clearContents()
        self.system_table.setRowCount(len(self.service.config.systems))
        for row, system in enumerate(self.service.config.systems):
            self.system_table.setItem(row, 0, self._read_only_item(system.name))
            self.system_table.setItem(row, 1, self._read_only_item(str(system.code_root)))
            self.system_table.setCellWidget(row, 2, self._build_operation_cell(system.name))
        self.system_table.resizeRowsToContents()
        self.system_table.clearSelection()
        self.system_table.setCurrentCell(-1, -1)
        self.system_table.blockSignals(False)
        self.system_table.viewport().update()
        QApplication.processEvents()

    def _read_only_item(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item

    def _build_operation_cell(self, system_name: str) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        for label, handler in [
            ("进入", self.open_system_detail),
            ("编辑", self.edit_system),
            ("删除", self.delete_system),
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
            self.refresh_table()
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
