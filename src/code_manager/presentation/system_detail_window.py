from __future__ import annotations

from collections.abc import Callable
import os
import platform
import shutil
import subprocess
from pathlib import Path
import shlex

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
from code_manager.presentation.group_config_window import GroupConfigWindow
from code_manager.presentation.repository_config_window import RepositoryConfigWindow
from code_manager.presentation.workers import BatchWorker


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
        self.repository_table = QTableWidget(0, 7)
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
            [
                "分组",
                "应用名",
                "本地路径",
                "分支",
                "本地改动",
                "远端新代码",
                "操作",
            ]
        )
        header = self.repository_table.horizontalHeader()
        column_widths = {
            0: 120,
            1: 260,
            3: 90,
            4: 100,
            5: 115,
            6: 220,
        }
        for column, width in column_widths.items():
            header.setSectionResizeMode(column, QHeaderView.Fixed)
            self.repository_table.setColumnWidth(column, width)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.repository_table.setSelectionMode(QTableWidget.NoSelection)
        self.repository_table.setFocusPolicy(Qt.NoFocus)
        self.repository_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.repository_table, 1)
        layout.addWidget(self.status_label)
        self.setCentralWidget(root)

    def refresh_table(self) -> None:
        system = self._system()
        applications = sorted(
            system.applications,
            key=lambda application: (application.group_english_name, application.name),
        )
        self.repository_table.setRowCount(len(applications))
        for row, application in enumerate(applications):
            status = self.status_by_url.get(application.repository_url)
            local_path = application.resolve_local_path(system.code_root)
            values = [
                application.group_english_name,
                application.name,
                str(local_path),
                status.branch if status else "-",
                self._local_changes_text(status),
                self._yes_no(status.has_remote_updates) if status else "-",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
                self.repository_table.setItem(row, column, item)
            self.repository_table.setCellWidget(row, 6, self._operation_widget(application, local_path))

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

    def _local_changes_text(self, status: RepositoryStatus | None) -> str:
        if status is None:
            return "-"
        if not status.exists:
            return "未clone"
        return self._yes_no(status.has_local_changes)

    def _operation_widget(self, application: Application, local_path: Path) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 2, 4, 2)
        open_directory_button = QPushButton("打本目录")
        open_directory_button.setFixedWidth(86)
        open_directory_button.clicked.connect(
            lambda _checked=False: self._handle_open_local_path(application, local_path)
        )
        terminal_button = QPushButton("在终端中打开")
        terminal_button.setFixedWidth(112)
        terminal_button.clicked.connect(
            lambda _checked=False: self._handle_open_terminal_path(application, local_path)
        )
        layout.addWidget(open_directory_button)
        layout.addWidget(terminal_button)
        layout.addStretch(1)
        return widget

    def _handle_open_local_path(self, application: Application, local_path: Path) -> None:
        self.open_local_path(local_path)
        self.status_label.setText(f"打开本地目录: {application.name}")

    def _open_local_path(self, local_path: Path) -> bool:
        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(local_path)))

    def _handle_open_terminal_path(self, application: Application, local_path: Path) -> None:
        self.open_terminal_path(local_path)
        self.status_label.setText(f"在终端中打开: {application.name}")

    def _open_terminal_path(self, local_path: Path) -> bool:
        local_path.mkdir(parents=True, exist_ok=True)
        system_name = platform.system()
        if system_name == "Windows":
            creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
            subprocess.Popen(["powershell.exe", "-NoExit"], cwd=local_path, creationflags=creation_flags)
            return True
        if system_name == "Darwin":
            return self._open_terminal_on_macos(local_path)
        return self._open_terminal_on_linux(local_path)

    def _open_terminal_on_linux(self, local_path: Path) -> bool:
        candidates = [
            os.environ.get("TERMINAL"),
            "x-terminal-emulator",
            "gnome-terminal",
            "konsole",
            "xfce4-terminal",
            "xterm",
        ]
        for candidate in candidates:
            if candidate and shutil.which(candidate):
                subprocess.Popen([candidate], cwd=local_path)
                return True
        return False

    def _open_terminal_on_macos(self, local_path: Path) -> bool:
        if Path("/Applications/iTerm.app").exists() and shutil.which("osascript"):
            quoted_path = shlex.quote(str(local_path))
            script = (
                'tell application "iTerm"\n'
                "  create window with default profile\n"
                "  tell current session of current window\n"
                f'    write text "cd {quoted_path}"\n'
                "  end tell\n"
                "end tell"
            )
            subprocess.Popen(["osascript", "-e", script])
            return True
        if shutil.which("open"):
            subprocess.Popen(["open", "-a", "Terminal", str(local_path)])
            return True
        return False
