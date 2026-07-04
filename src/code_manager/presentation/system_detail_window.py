from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
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
from code_manager.presentation.group_config_window import GroupConfigWindow
from code_manager.presentation.repository_config_window import RepositoryConfigWindow
from code_manager.presentation.workers import BatchWorker


class SystemDetailWindow(QMainWindow):
    def __init__(
        self,
        service: CodeManagerService,
        git_service: GitService,
        system_name: str,
    ) -> None:
        super().__init__()
        self.service = service
        self.git_service = git_service
        self.system_name = system_name
        self.thread_pool = QThreadPool.globalInstance()
        self.status_by_url: dict[str, RepositoryStatus] = {}
        self.repository_config_window: RepositoryConfigWindow | None = None
        self.group_config_window: GroupConfigWindow | None = None

        self.repository_table = QTableWidget(0, 8)
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
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.repository_table.setHorizontalHeaderLabels(
            [
                "应用名",
                "分组",
                "本地目录",
                "仓库地址",
                "本地路径",
                "分支",
                "本地改动",
                "远端新代码",
            ]
        )
        self.repository_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.repository_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.repository_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.repository_table, 1)
        layout.addWidget(self.status_label)
        self.setCentralWidget(root)

    def refresh_table(self) -> None:
        system = self._system()
        self.repository_table.setRowCount(len(system.applications))
        for row, application in enumerate(system.applications):
            status = self.status_by_url.get(application.repository_url)
            values = [
                application.name,
                application.group_english_name,
                application.local_dir_name,
                application.repository_url,
                str(application.resolve_local_path(system.code_root)),
                status.branch if status else "-",
                self._yes_no(status.has_local_changes) if status else "-",
                self._yes_no(status.has_remote_updates) if status else "-",
            ]
            for column, value in enumerate(values):
                self.repository_table.setItem(row, column, QTableWidgetItem(value))

    def open_repository_config(self) -> None:
        if self.repository_config_window is not None:
            self._activate_window(self.repository_config_window)
            return
        window = RepositoryConfigWindow(
            self.service,
            self.system_name,
            on_changed=self._handle_repository_config_changed,
        )
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        window.destroyed.connect(lambda _object=None: setattr(self, "repository_config_window", None))
        window.resize(1100, 720)
        window.show()
        self.repository_config_window = window

    def open_group_config(self) -> None:
        if self.group_config_window is not None:
            self._activate_window(self.group_config_window)
            return
        window = GroupConfigWindow(
            self.service,
            self.system_name,
            on_changed=self._handle_repository_config_changed,
        )
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        window.destroyed.connect(lambda _object=None: setattr(self, "group_config_window", None))
        window.resize(720, 560)
        window.show()
        self.group_config_window = window

    def _activate_window(self, window: QMainWindow) -> None:
        if window.isMinimized():
            window.showNormal()
        else:
            window.show()
        window.raise_()
        window.activateWindow()

    def clone_all(self) -> None:
        system = self._system()
        self._run_batch(
            "clone",
            system,
            lambda application: self.git_service.clone(application, system.code_root),
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
        self._run_batch(
            "拉代码",
            system,
            lambda application: self.git_service.update(application, system.code_root),
        )

    def _run_batch(
        self,
        name: str,
        system: SystemProfile,
        operation: Callable[[Application], object],
    ) -> None:
        self.status_label.setText(f"{name} 执行中...")
        worker = BatchWorker(system.applications, operation)
        worker.signals.item_finished.connect(self._handle_batch_result)
        worker.signals.finished.connect(lambda: self.status_label.setText(f"{name} 已完成"))
        self.thread_pool.start(worker)

    def _handle_batch_result(self, result: object) -> None:
        if isinstance(result, RepositoryStatus):
            self.status_by_url[result.application.repository_url] = result
            self.refresh_table()
            return
        if isinstance(result, GitOperationResult):
            self.status_label.setText(f"{result.application.name}: {result.message}")

    def _handle_repository_config_changed(self) -> None:
        self.status_by_url.clear()
        self.refresh_table()

    def _system(self) -> SystemProfile:
        return self.service.config.get_system(self.system_name)

    def _yes_no(self, value: bool) -> str:
        return "是" if value else "否"
