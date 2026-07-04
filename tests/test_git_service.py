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
                        ["git", "clone", app.repository_url, "order-service"],
                        Path(temp_dir) / "platform",
                    )
                ],
            )


if __name__ == "__main__":
    unittest.main()
