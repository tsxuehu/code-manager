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
from code_manager.domain.models import SystemProfile
from code_manager.presentation.dialogs import ApplicationDialog, ImportRepositoriesDialog


class RepositoryConfigWindow(QMainWindow):
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

        self.application_table = QTableWidget(0, 6)
        self.status_label = QLabel("就绪")

        self.setWindowTitle(f"配置仓库 - {system_name}")
        self._build_ui()
        self.refresh_tables()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addWidget(QLabel(f"系统: {self.system_name}"))

        button_row = QHBoxLayout()
        for label, handler in [
            ("导入仓库", self.import_repositories),
            ("新增应用", self.add_application),
        ]:
            button = QPushButton(label)
            button.clicked.connect(handler)
            button_row.addWidget(button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        layout.addWidget(self._build_application_panel(), 1)
        layout.addWidget(self.status_label)
        self.setCentralWidget(root)

    def _build_application_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("应用"))
        self.application_table.setHorizontalHeaderLabels(
            ["应用名", "分组", "本地目录", "仓库地址", "本地路径", "操作"]
        )
        self.application_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.application_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.application_table.setSelectionMode(QTableWidget.NoSelection)
        self.application_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.application_table.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.application_table)
        return panel

    def refresh_tables(self) -> None:
        system = self._system()
        self.application_table.setRowCount(len(system.applications))
        for row, application in enumerate(system.applications):
            values = [
                application.name,
                application.group_english_name,
                application.local_dir_name,
                application.repository_url,
                str(application.resolve_local_path(system.code_root)),
            ]
            for column, value in enumerate(values):
                self.application_table.setItem(row, column, QTableWidgetItem(value))
            self.application_table.setCellWidget(row, 5, self._build_application_operation_cell(row))

    def _build_application_operation_cell(self, row: int) -> QWidget:
        return self._build_operation_cell(
            [
                ("编辑", lambda: self.edit_application(row)),
                ("删除", lambda: self.delete_application(row)),
            ]
        )

    def _build_operation_cell(self, actions: list[tuple[str, Callable[[], None]]]) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        for label, handler in actions:
            button = QPushButton(label)
            button.clicked.connect(handler)
            layout.addWidget(button)
        layout.addStretch(1)
        return cell

    def import_repositories(self) -> None:
        self.service.select_system(self.system_name)
        dialog = ImportRepositoriesDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        result = self.service.import_repositories(dialog.repositories_text())
        message = f"导入 {result.imported_count} 个，跳过 {result.skipped_count} 个"
        if result.errors:
            message += "\n" + "\n".join(result.errors)
        QMessageBox.information(self, "导入结果", message)
        self._changed()

    def add_application(self) -> None:
        dialog = ApplicationDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._save_application_from_dialog(dialog)

    def edit_application(self, row: int | None = None) -> None:
        system = self._system()
        row = self.application_table.currentRow() if row is None else row
        if row < 0:
            return
        dialog = ApplicationDialog(system.applications[row])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._save_application_from_dialog(dialog)

    def _save_application_from_dialog(self, dialog: ApplicationDialog) -> None:
        try:
            self.service.select_system(self.system_name)
            self.service.upsert_application(dialog.application())
            self._changed()
        except ValueError as exc:
            QMessageBox.warning(self, "保存失败", str(exc))

    def delete_application(self, row: int | None = None) -> None:
        system = self._system()
        row = self.application_table.currentRow() if row is None else row
        if row < 0:
            return
        application = system.applications[row]
        if self._confirm(f"确定删除应用 {application.name} 吗？"):
            self.service.select_system(self.system_name)
            self.service.delete_application(application.repository_url)
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
