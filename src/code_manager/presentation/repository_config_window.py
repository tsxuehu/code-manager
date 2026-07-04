from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
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
from code_manager.domain.models import Application, SystemProfile
from code_manager.presentation.dialogs import ApplicationDialog, ImportRepositoriesDialog

APPLICATION_TABLE_ROW_HEIGHT = 36
APPLICATION_OPERATION_COLUMN_WIDTH = 260


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
        self.editing_cell: tuple[str, int] | None = None

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
        for column in range(5):
            self.application_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.Stretch)
        self.application_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.application_table.verticalHeader().setDefaultSectionSize(APPLICATION_TABLE_ROW_HEIGHT)
        self.application_table.verticalHeader().setMinimumSectionSize(APPLICATION_TABLE_ROW_HEIGHT)
        self.application_table.setColumnWidth(5, APPLICATION_OPERATION_COLUMN_WIDTH)
        self.application_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.application_table.setSelectionMode(QTableWidget.NoSelection)
        self.application_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.application_table.setFocusPolicy(Qt.NoFocus)
        self.application_table.cellDoubleClicked.connect(self.start_cell_edit)
        layout.addWidget(self.application_table)
        return panel

    def refresh_tables(self) -> None:
        system = self._system()
        self.application_table.setRowCount(len(system.applications))
        for row, application in enumerate(system.applications):
            editing_column = self._editing_column_for(application.repository_url)
            values = [
                application.name,
                application.group_english_name,
                application.local_dir_name,
                application.repository_url,
                str(application.resolve_local_path(system.code_root)),
            ]
            for column, value in enumerate(values):
                self.application_table.removeCellWidget(row, column)
                if editing_column == column and column in (0, 2, 3):
                    self.application_table.takeItem(row, column)
                    self.application_table.setCellWidget(
                        row,
                        column,
                        self._build_text_cell_editor(value, application.repository_url, column),
                    )
                elif editing_column == column and column == 1:
                    self.application_table.takeItem(row, column)
                    self.application_table.setCellWidget(
                        row,
                        column,
                        self._build_group_cell_editor(value, application.repository_url, column),
                    )
                else:
                    self.application_table.setItem(row, column, QTableWidgetItem(value))
            self.application_table.setCellWidget(row, 5, self._build_application_operation_cell(row))
            self.application_table.setRowHeight(row, APPLICATION_TABLE_ROW_HEIGHT)
        self.application_table.setColumnWidth(5, APPLICATION_OPERATION_COLUMN_WIDTH)

    def _build_text_cell_editor(self, text: str, repository_url: str, column: int) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        input_widget = QLineEdit(text)
        input_widget.setMinimumHeight(28)
        input_widget.setStyleSheet("QLineEdit { padding: 2px 6px; }")
        layout.addWidget(input_widget, 1)
        self._add_editor_buttons(layout, repository_url, column)
        return cell

    def _build_group_cell_editor(self, current_group: str, repository_url: str, column: int) -> QWidget:
        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        combo = QComboBox()
        combo.setMinimumHeight(28)
        combo.addItems([group.english_name for group in self._system().groups])
        if current_group:
            combo.setCurrentText(current_group)
        layout.addWidget(combo, 1)
        self._add_editor_buttons(layout, repository_url, column)
        return cell

    def _add_editor_buttons(self, layout: QHBoxLayout, repository_url: str, column: int) -> None:
        for label, handler in [
            ("×", self.cancel_cell_edit),
            ("√", self.confirm_cell_edit),
        ]:
            button = QPushButton(label)
            button.setFixedSize(26, 28)
            button.clicked.connect(
                lambda _checked=False, url=repository_url, col=column, action=handler: action(
                    url,
                    col,
                )
            )
            layout.addWidget(button)

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
        dialog = ApplicationDialog(group_options=self._group_options())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._save_application_from_dialog(dialog)

    def start_cell_edit(self, row: int, column: int) -> None:
        if column not in (0, 1, 2, 3):
            return
        system = self._system()
        if row < 0 or row >= len(system.applications):
            return
        application = system.applications[row]
        self.editing_cell = (application.repository_url, column)
        self.refresh_tables()
        self._focus_editing_cell(application.repository_url, column)
        self.status_label.setText(f"正在编辑{self._cell_label(column)}: {application.name}")

    def cancel_cell_edit(self, repository_url: str | None = None, column: int | None = None) -> None:
        self.editing_cell = None
        self.refresh_tables()
        if repository_url:
            self.status_label.setText(f"已取消编辑{self._cell_label(column)}")

    def confirm_cell_edit(self, repository_url: str | None = None, column: int | None = None) -> None:
        if not repository_url or column not in (0, 1, 2, 3):
            return
        row = self._find_application_row(repository_url)
        if row < 0:
            return
        editor = self.application_table.cellWidget(row, column)
        current = self._system().applications[row]
        if column == 1:
            combo = editor.findChild(QComboBox) if editor else None
            if not isinstance(combo, QComboBox):
                return
            value = combo.currentText().strip()
        else:
            input_widget = editor.findChild(QLineEdit) if editor else None
            if not isinstance(input_widget, QLineEdit):
                return
            value = input_widget.text().strip()

        updated = Application(
            name=value if column == 0 else current.name,
            repository_url=value if column == 3 else current.repository_url,
            group_english_name=value if column == 1 else current.group_english_name,
            local_dir_name=value if column == 2 else current.local_dir_name,
        )
        try:
            self.service.select_system(self.system_name)
            if updated.repository_url != current.repository_url:
                self.service.delete_application(current.repository_url)
            self.service.upsert_application(updated)
            self.editing_cell = None
            self._changed()
            self.status_label.setText(f"{self._cell_label(column)}已更新")
        except ValueError as exc:
            QMessageBox.warning(self, "保存失败", str(exc))

    def edit_application(self, row: int | None = None) -> None:
        system = self._system()
        row = self.application_table.currentRow() if row is None else row
        if row < 0:
            return
        dialog = ApplicationDialog(system.applications[row], group_options=self._group_options())
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

    def _group_options(self) -> list[str]:
        return [group.english_name for group in self._system().groups]

    def _find_application_row(self, repository_url: str) -> int:
        for row, application in enumerate(self._system().applications):
            if application.repository_url == repository_url:
                return row
        return -1

    def _focus_editing_cell(self, repository_url: str, column: int) -> None:
        row = self._find_application_row(repository_url)
        if row < 0:
            return
        editor = self.application_table.cellWidget(row, column)
        if column == 1:
            input_widget = editor.findChild(QComboBox) if editor else None
        else:
            input_widget = editor.findChild(QLineEdit) if editor else None
        if input_widget:
            input_widget.setFocus()
            if isinstance(input_widget, QLineEdit):
                input_widget.selectAll()

    def _editing_column_for(self, repository_url: str) -> int | None:
        if not self.editing_cell:
            return None
        editing_repository_url, column = self.editing_cell
        if editing_repository_url == repository_url:
            return column
        return None

    def _cell_label(self, column: int | None) -> str:
        labels = {
            0: "应用名",
            1: "分组",
            2: "本地目录",
            3: "仓库地址",
        }
        return labels.get(column, "单元格")

    def _confirm(self, message: str) -> bool:
        return (
            QMessageBox.question(self, "确认", message, QMessageBox.Yes | QMessageBox.No)
            == QMessageBox.Yes
        )
