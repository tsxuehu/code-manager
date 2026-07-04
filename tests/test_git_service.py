import tempfile
import unittest
from pathlib import Path

from code_manager.domain.models import Application
from code_manager.infrastructure.git_service import GitService


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
            self.assertEqual(status.message, "本地仓库不存在")


if __name__ == "__main__":
    unittest.main()
