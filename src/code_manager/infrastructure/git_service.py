from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from code_manager.domain.models import Application

CommandRunner = Callable[[list[str], Path | None], str]


@dataclass(frozen=True)
class GitOperationResult:
    application: Application
    success: bool
    message: str


@dataclass(frozen=True)
class RepositoryStatus:
    application: Application
    local_path: Path
    exists: bool
    branch: str
    has_local_changes: bool
    has_remote_updates: bool
    message: str


class GitService:
    def __init__(self, runner: CommandRunner | None = None) -> None:
        self._runner = runner or self._run_command

    def clone(
        self,
        application: Application,
        code_root: Path,
        include_submodules: bool = False,
    ) -> GitOperationResult:
        local_path = application.resolve_local_path(code_root)
        if (local_path / ".git").exists():
            return GitOperationResult(application, True, "仓库已存在，跳过 clone")

        parent_dir = local_path.parent
        parent_dir.mkdir(parents=True, exist_ok=True)
        try:
            command = ["git", "clone"]
            if include_submodules:
                command.append("--recurse-submodules")
            command.extend([application.repository_url, application.local_dir_name])
            self._runner(command, parent_dir)
            return GitOperationResult(application, True, "clone 完成")
        except subprocess.CalledProcessError as exc:
            return GitOperationResult(application, False, self._format_error(exc))

    def update(
        self,
        application: Application,
        code_root: Path,
        include_submodules: bool = False,
    ) -> GitOperationResult:
        local_path = application.resolve_local_path(code_root)
        if not (local_path / ".git").exists():
            return GitOperationResult(application, False, "本地仓库不存在，请先 clone")

        try:
            self._runner(["git", "pull", "--ff-only"], local_path)
            if include_submodules:
                self._runner(["git", "submodule", "update", "--init", "--recursive"], local_path)
            return GitOperationResult(application, True, "更新完成")
        except subprocess.CalledProcessError as exc:
            return GitOperationResult(application, False, self._format_error(exc))

    def status(self, application: Application, code_root: Path) -> RepositoryStatus:
        local_path = application.resolve_local_path(code_root)
        if not (local_path / ".git").exists():
            return RepositoryStatus(
                application=application,
                local_path=local_path,
                exists=False,
                branch="-",
                has_local_changes=False,
                has_remote_updates=False,
                message="本地仓库不存在",
            )

        try:
            self._runner(["git", "fetch", "--quiet"], local_path)
            branch = self._runner(["git", "branch", "--show-current"], local_path).strip() or "(detached)"
            status_text = self._runner(["git", "status", "--porcelain"], local_path)
            remote_updates = self._has_remote_updates(local_path)
            return RepositoryStatus(
                application=application,
                local_path=local_path,
                exists=True,
                branch=branch,
                has_local_changes=bool(status_text.strip()),
                has_remote_updates=remote_updates,
                message="状态已刷新",
            )
        except subprocess.CalledProcessError as exc:
            return RepositoryStatus(
                application=application,
                local_path=local_path,
                exists=True,
                branch="-",
                has_local_changes=False,
                has_remote_updates=False,
                message=self._format_error(exc),
            )

    def _has_remote_updates(self, local_path: Path) -> bool:
        output = self._runner(["git", "status", "-sb"], local_path)
        return "behind" in output or "diverged" in output

    def _run_command(self, command: list[str], cwd: Path | None) -> str:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return completed.stdout

    def _format_error(self, exc: subprocess.CalledProcessError) -> str:
        stderr = exc.stderr.strip() if isinstance(exc.stderr, str) else ""
        stdout = exc.stdout.strip() if isinstance(exc.stdout, str) else ""
        return stderr or stdout or str(exc)
