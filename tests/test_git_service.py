import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from code_manager.domain.models import Application
from code_manager.infrastructure.git_service import GitService, subprocess_run_kwargs


class GitServiceTests(unittest.TestCase):
    def test_clone_skips_existing_git_repository(self) -> None:
        commands: list[list[str]] = []

        def runner(command: list[str], cwd: Path | None = None) -> str:
            commands.append(command)
            return ""

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "platform" / "order-service"
            (target / ".git").mkdir(parents=True)
            service = GitService(runner=runner)
            app = Application(
                name="order-service",
                repository_url="https://git.example.com/platform/order-service.git",
                group_english_name="platform",
                local_dir_name="order-service",
            )

            result = service.clone(app, Path(temp_dir))

            self.assertTrue(result.success)
            self.assertIn("已存在", result.message)
            self.assertEqual(commands, [])

    def test_clone_runs_git_clone_when_repository_missing(self) -> None:
        commands: list[tuple[list[str], Path | None]] = []

        def runner(command: list[str], cwd: Path | None = None) -> str:
            commands.append((command, cwd))
            return ""

        with tempfile.TemporaryDirectory() as temp_dir:
            service = GitService(runner=runner)
            app = Application(
                name="order-service",
                repository_url="https://git.example.com/platform/order-service.git",
                group_english_name="platform",
                local_dir_name="order-service",
            )

            result = service.clone(app, Path(temp_dir))

            self.assertTrue(result.success)
            self.assertEqual(
                commands,
                [
                    (
                        ["git", "clone", "--no-recurse-submodules", app.repository_url, "order-service"],
                        Path(temp_dir) / "platform",
                    )
                ],
            )

    def test_clone_includes_submodules_when_requested(self) -> None:
        commands: list[tuple[list[str], Path | None]] = []

        def runner(command: list[str], cwd: Path | None = None) -> str:
            commands.append((command, cwd))
            return ""

        with tempfile.TemporaryDirectory() as temp_dir:
            service = GitService(runner=runner)
            app = Application(
                name="order-service",
                repository_url="https://git.example.com/platform/order-service.git",
                group_english_name="platform",
                local_dir_name="order-service",
            )

            result = service.clone(app, Path(temp_dir), include_submodules=True)

            self.assertTrue(result.success)
            self.assertEqual(
                commands,
                [
                    (
                        ["git", "clone", "--recurse-submodules", app.repository_url, "order-service"],
                        Path(temp_dir) / "platform",
                    )
                ],
            )

    def test_update_updates_submodules_when_requested(self) -> None:
        commands: list[tuple[list[str], Path | None]] = []

        def runner(command: list[str], cwd: Path | None = None) -> str:
            commands.append((command, cwd))
            return ""

        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = Path(temp_dir) / "platform" / "order-service"
            (local_path / ".git").mkdir(parents=True)
            service = GitService(runner=runner)
            app = Application(
                name="order-service",
                repository_url="https://git.example.com/platform/order-service.git",
                group_english_name="platform",
                local_dir_name="order-service",
            )

            result = service.update(app, Path(temp_dir), include_submodules=True)

            self.assertTrue(result.success)
            self.assertEqual(
                commands,
                [
                    (
                        [
                            "git",
                            "-c",
                            "submodule.recurse=false",
                            "pull",
                            "--ff-only",
                            "--recurse-submodules=no",
                        ],
                        local_path,
                    ),
                    (["git", "submodule", "update", "--init", "--recursive"], local_path),
                ],
            )

    def test_update_disables_submodules_by_default(self) -> None:
        commands: list[tuple[list[str], Path | None]] = []

        def runner(command: list[str], cwd: Path | None = None) -> str:
            commands.append((command, cwd))
            return ""

        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = Path(temp_dir) / "platform" / "order-service"
            (local_path / ".git").mkdir(parents=True)
            service = GitService(runner=runner)
            app = Application(
                name="order-service",
                repository_url="https://git.example.com/platform/order-service.git",
                group_english_name="platform",
                local_dir_name="order-service",
            )

            result = service.update(app, Path(temp_dir))

            self.assertTrue(result.success)
            self.assertEqual(
                commands,
                [
                    (
                        [
                            "git",
                            "-c",
                            "submodule.recurse=false",
                            "pull",
                            "--ff-only",
                            "--recurse-submodules=no",
                        ],
                        local_path,
                    ),
                ],
            )

    def test_status_marks_repository_as_missing_when_not_cloned(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = GitService()
            app = Application(
                name="order-service",
                repository_url="https://git.example.com/platform/order-service.git",
                group_english_name="platform",
                local_dir_name="order-service",
            )

            status = service.status(app, Path(temp_dir))

            self.assertFalse(status.exists)
            self.assertEqual(status.branch, "-")
            self.assertFalse(status.has_local_changes)
            self.assertFalse(status.has_unpushed_commits)
            self.assertEqual(status.message, "本地仓库不存在")

    def test_status_detects_unpushed_commits_from_tracking_status(self) -> None:
        commands: list[list[str]] = []

        def runner(command: list[str], cwd: Path | None = None) -> str:
            commands.append(command)
            if command[:3] == ["git", "fetch", "--quiet"]:
                return ""
            if command[:3] == ["git", "branch", "--show-current"]:
                return "master\n"
            if command[:3] == ["git", "status", "--porcelain"]:
                return ""
            if command[:3] == ["git", "status", "-sb"]:
                return "## master...origin/master [ahead 2]\n"
            return ""

        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = Path(temp_dir) / "platform" / "order-service"
            (local_path / ".git").mkdir(parents=True)
            service = GitService(runner=runner)
            app = Application(
                name="order-service",
                repository_url="https://git.example.com/platform/order-service.git",
                group_english_name="platform",
                local_dir_name="order-service",
            )

            status = service.status(app, Path(temp_dir))

            self.assertTrue(status.exists)
            self.assertEqual(status.branch, "master")
            self.assertFalse(status.has_local_changes)
            self.assertTrue(status.has_unpushed_commits)
            self.assertFalse(status.has_remote_updates)


class GitServiceSubprocessTests(unittest.TestCase):
    def test_subprocess_run_kwargs_hides_console_on_windows(self) -> None:
        with patch.object(sys, "platform", "win32"):
            self.assertEqual(
                subprocess_run_kwargs(),
                {"creationflags": subprocess.CREATE_NO_WINDOW},
            )

    def test_subprocess_run_kwargs_empty_on_non_windows(self) -> None:
        with patch.object(sys, "platform", "linux"):
            self.assertEqual(subprocess_run_kwargs(), {})

    def test_run_command_passes_no_window_flag_on_windows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = Path(temp_dir)
            (local_path / ".git").mkdir()
            service = GitService()

            with patch.object(sys, "platform", "win32"), patch.object(
                subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, stdout="master\n", stderr=""),
            ) as run:
                branch = service._run_command(["git", "branch", "--show-current"], local_path)

            self.assertEqual(branch, "master\n")
            self.assertEqual(
                run.call_args.kwargs.get("creationflags"),
                subprocess.CREATE_NO_WINDOW,
            )


if __name__ == "__main__":
    unittest.main()
