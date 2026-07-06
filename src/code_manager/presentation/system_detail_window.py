from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from code_manager.application.config_service import CodeManagerService
from code_manager.domain.models import Application, SystemProfile
from code_manager.infrastructure.git_service import GitOperationResult, GitService, RepositoryStatus
from code_manager.presentation.child_window import show_or_raise_window
from code_manager.presentation.group_config_window import GroupConfigWindow
from code_manager.presentation.repository_config_window import RepositoryConfigWindow
from code_manager.presentation.repository_status_view import (
    build_status_cell,
    local_status_text,
    remote_status_text,
)
from code_manager.presentation.table_hover import install_row_hover_highlight
from code_manager.presentation.terminal_launcher import open_terminal_at
from code_manager.presentation.workers import BatchWorker

COL_GROUP = 0
COL_APPLICATION = 1
COL_LOCAL_STATUS = 2
COL_REMOTE_STATUS = 3
COL_OPERATIONS = 4

REPOSITORY_TABLE_COLUMN_WIDTHS = {
    COL_GROUP: 120,
    COL_APPLICATION: 160,
    COL_LOCAL_STATUS: 420,
    COL_REMOTE_STATUS: 115,
    COL_OPERATIONS: 360,
}


class SystemDetailWindow(QMainWindow):
    def __init__(
        self,
        service: CodeManagerService,
        git_service: GitService,
        system_name: str,
        open_local_path: Callable[[Path], object] | None = None,
        open_terminal_path: Callable[[Path], object] | None = None,
    ) -> None:
        super().__init__()
        self.service = service
        self.git_service = git_service
        self.system_name = system_name
        self.open_local_path = open_local_path or self._open_local_path
        self.open_terminal_path = open_terminal_path or self._open_terminal_path
        self.thread_pool = QThreadPool.globalInstance()
        self.status_by_url: dict[str, RepositoryStatus] = {}
        self.repository_config_window: RepositoryConfigWindow | None = None
        self.group_config_window: GroupConfigWindow | None = None

        self.include_submodules_checkbox = QCheckBox("操作应用于 sub module")
        self.repository_table = QTableWidget(0, len(REPOSITORY_TABLE_COLUMN_WIDTHS))
        self.status_label = QLabel("就绪")

        self.setWindowTitle(f"系统详情 - {system_name}")
        self._build_ui()
        self.refresh_table()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addWidget(QLabel(f"系统: {self.system_name}"))

        button_row = QHBoxLayout()
        for label, handler in [
            ("Clone 全部", self.clone_all),
            ("拉代码", self.update_all),
            ("刷新状态", self.refresh_statuses),
            ("配置仓库", self.open_repository_config),
            ("配置分组", self.open_group_config),
        ]:
            button = QPushButton(label)
            button.clicked.connect(handler)
            button_row.addWidget(button)
        button_row.addWidget(self.include_submodules_checkbox)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.repository_table.setHorizontalHeaderLabels(
            ["分组", "应用名", "本地状态", "远端状态", "操作"]
        )
        header = self.repository_table.horizontalHeader()
        for column, width in REPOSITORY_TABLE_COLUMN_WIDTHS.items():
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
            self.repository_table.setColumnWidth(column, width)
        header.setStretchLastSection(True)
        self.repository_table.verticalHeader().setVisible(False)
        self.repository_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.repository_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.repository_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.repository_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        install_row_hover_highlight(self.repository_table)
        layout.addWidget(self.repository_table, 1)
        layout.addWidget(self.status_label)
        self.setCentralWidget(root)

    def refresh_table(self) -> None:
        system = self._system()
        applications = self._sorted_applications(system)
        self.repository_table.setRowCount(len(applications))
        for row, application in enumerate(applications):
            self._render_repository_row(row, application, system.code_root)

    def open_repository_config(self) -> None:
        self.repository_config_window = show_or_raise_window(
            self.repository_config_window,
            lambda: RepositoryConfigWindow(
                self.service,
                self.system_name,
                on_changed=self._handle_repository_config_changed,
            ),
            lambda: setattr(self, "repository_config_window", None),
        )
        self.repository_config_window.resize(1100, 720)

    def open_group_config(self) -> None:
        self.group_config_window = show_or_raise_window(
            self.group_config_window,
            lambda: GroupConfigWindow(
                self.service,
                self.system_name,
                on_changed=self._handle_repository_config_changed,
            ),
            lambda: setattr(self, "group_config_window", None),
        )
        self.group_config_window.resize(720, 560)

    def clone_all(self) -> None:
        system = self._system()
        include_submodules = self.include_submodules_checkbox.isChecked()
        self._run_batch(
            "clone",
            system,
            lambda application: self.git_service.clone(
                application,
                system.code_root,
                include_submodules=include_submodules,
            ),
        )

    def refresh_statuses(self) -> None:
        system = self._system()
        self._run_batch(
            "状态刷新",
            system,
            lambda application: self.git_service.status(application, system.code_root),
        )

    def update_all(self) -> None:
        system = self._system()
        include_submodules = self.include_submodules_checkbox.isChecked()
        self._run_batch(
            "拉代码",
            system,
            lambda application: self.git_service.update(
                application,
                system.code_root,
                include_submodules=include_submodules,
            ),
        )

    def _run_batch(
        self,
        name: str,
        system: SystemProfile,
        operation: Callable[[Application], object],
    ) -> None:
        self.status_label.setText(f"{name} 执行中...")
        worker = BatchWorker(system.applications, operation, signal_parent=self)
        worker.signals.item_started.connect(
            lambda application, batch_name=name: self._handle_batch_item_started(batch_name, application)
        )
        worker.signals.item_finished.connect(self._handle_batch_result)
        worker.signals.finished.connect(lambda w=worker: self._finish_batch(name, w))
        self.thread_pool.start(worker)

    def _handle_batch_item_started(self, name: str, application: Application) -> None:
        self.status_label.setText(f"{name}: {application.name}")

    def _finish_batch(self, name: str, worker: BatchWorker) -> None:
        self.status_label.setText(f"{name} 已完成")
        worker.signals.deleteLater()

    def _handle_batch_result(self, result: object) -> None:
        if isinstance(result, RepositoryStatus):
            self.status_by_url[result.application.repository_url] = result
            row = self._find_application_row(result.application.repository_url)
            if row >= 0:
                self._update_repository_status_cells(row, result.application)
            else:
                self.refresh_table()
            return
        if isinstance(result, GitOperationResult):
            return

    def _handle_repository_config_changed(self) -> None:
        self.status_by_url.clear()
        self.refresh_table()

    def _system(self) -> SystemProfile:
        return self.service.config.get_system(self.system_name)

    def _sorted_applications(self, system: SystemProfile) -> list[Application]:
        return sorted(
            system.applications,
            key=lambda application: (application.group_english_name, application.name),
        )

    def _find_application_row(self, repository_url: str) -> int:
        system = self._system()
        for row, application in enumerate(self._sorted_applications(system)):
            if application.repository_url == repository_url:
                return row
        return -1

    def _render_repository_row(self, row: int, application: Application, code_root: Path) -> None:
        status = self.status_by_url.get(application.repository_url)
        local_path = application.resolve_local_path(code_root)

        for column, value in (
            (COL_GROUP, application.group_english_name),
            (COL_APPLICATION, application.name),
        ):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.repository_table.setItem(row, column, item)

        self._update_repository_status_cells(row, application)
        self.repository_table.setCellWidget(row, COL_OPERATIONS, self._operation_widget(application, local_path))

    def _update_repository_status_cells(self, row: int, application: Application) -> None:
        status = self.status_by_url.get(application.repository_url)
        self.repository_table.setCellWidget(
            row,
            COL_LOCAL_STATUS,
            build_status_cell(local_status_text(status)),
        )
        self.repository_table.setCellWidget(
            row,
            COL_REMOTE_STATUS,
            build_status_cell(remote_status_text(status)),
        )

    def _operation_widget(self, application: Application, local_path: Path) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 2, 4, 2)

        refresh_button = QPushButton("刷新")
        refresh_button.setFixedWidth(56)
        refresh_button.clicked.connect(
            lambda _checked=False: self._refresh_application_status(application)
        )
        update_button = QPushButton("拉代码")
        update_button.setFixedWidth(56)
        update_button.clicked.connect(
            lambda _checked=False: self._update_application(application)
        )
        open_directory_button = QPushButton("打开目录")
        open_directory_button.setFixedWidth(70)
        open_directory_button.clicked.connect(
            lambda _checked=False: self._handle_open_local_path(application, local_path)
        )
        terminal_button = QPushButton("在终端中打开")
        terminal_button.setFixedWidth(128)
        terminal_button.clicked.connect(
            lambda _checked=False: self._handle_open_terminal_path(application, local_path)
        )

        layout.addWidget(refresh_button)
        layout.addWidget(update_button)
        layout.addWidget(open_directory_button)
        layout.addWidget(terminal_button)
        layout.addStretch(1)
        return widget

    def _refresh_application_status(self, application: Application) -> None:
        system = self._system()
        self.status_label.setText(f"刷新状态: {application.name}")
        worker = BatchWorker(
            [application],
            lambda current_application: self.git_service.status(current_application, system.code_root),
            signal_parent=self,
        )
        worker.signals.item_finished.connect(self._handle_batch_result)
        worker.signals.finished.connect(
            lambda w=worker: self._finish_single_refresh(application.name, w)
        )
        self.thread_pool.start(worker)

    def _finish_single_refresh(self, application_name: str, worker: BatchWorker) -> None:
        self.status_label.setText(f"刷新完成: {application_name}")
        worker.signals.deleteLater()

    def _update_application(self, application: Application) -> None:
        system = self._system()
        include_submodules = self.include_submodules_checkbox.isChecked()
        self.status_label.setText(f"拉代码: {application.name}")
        worker = BatchWorker(
            [application],
            lambda current_application: self.git_service.update(
                current_application,
                system.code_root,
                include_submodules=include_submodules,
            ),
            signal_parent=self,
        )
        worker.signals.item_finished.connect(self._handle_single_update_result)
        worker.signals.finished.connect(
            lambda w=worker: self._finish_single_update(application.name, w)
        )
        self.thread_pool.start(worker)

    def _handle_single_update_result(self, result: object) -> None:
        if not isinstance(result, GitOperationResult):
            return
        prefix = "拉代码完成" if result.success else "拉代码失败"
        self.status_label.setText(f"{prefix}: {result.application.name} - {result.message}")

    def _finish_single_update(self, application_name: str, worker: BatchWorker) -> None:
        if self.status_label.text().startswith("拉代码:"):
            self.status_label.setText(f"拉代码完成: {application_name}")
        worker.signals.deleteLater()

    def _handle_open_local_path(self, application: Application, local_path: Path) -> None:
        self.open_local_path(local_path)
        self.status_label.setText(f"打开本地目录: {application.name}")

    def _open_local_path(self, local_path: Path) -> bool:
        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(local_path)))

    def _handle_open_terminal_path(self, application: Application, local_path: Path) -> None:
        self.open_terminal_path(local_path)
        self.status_label.setText(f"在终端中打开: {application.name}")

    def _open_terminal_path(self, local_path: Path) -> bool:
        return open_terminal_at(local_path)
