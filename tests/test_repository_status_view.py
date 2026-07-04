import unittest
from pathlib import Path

from code_manager.domain.models import Application
from code_manager.infrastructure.git_service import RepositoryStatus
from code_manager.presentation.repository_status_view import local_status_text, remote_status_text


class RepositoryStatusViewTests(unittest.TestCase):
    def test_local_status_text_for_missing_repository(self) -> None:
        application = Application(
            name="demo",
            repository_url="https://git.example.com/demo.git",
            group_english_name="server",
            local_dir_name="demo",
        )
        self.assertEqual(local_status_text(None), "-")
        self.assertEqual(
            local_status_text(
                RepositoryStatus(
                    application=application,
                    local_path=application.resolve_local_path(Path("/tmp")),
                    exists=False,
                    branch="-",
                    has_local_changes=False,
                    has_unpushed_commits=False,
                    has_remote_updates=False,
                    message="本地仓库不存在",
                )
            ),
            "本地仓库不存在",
        )

    def test_local_status_text_includes_branch_and_colored_flags(self) -> None:
        application = Application(
            name="demo",
            repository_url="https://git.example.com/demo.git",
            group_english_name="server",
            local_dir_name="demo",
        )
        status = RepositoryStatus(
            application=application,
            local_path=application.resolve_local_path(Path("/tmp")),
            exists=True,
            branch="master",
            has_local_changes=True,
            has_unpushed_commits=False,
            has_remote_updates=False,
            message="状态已刷新",
        )

        text = local_status_text(status)

        self.assertIn("分支: master;", text)
        self.assertIn("有待提交内容", text)
        self.assertIn("无待push内容", text)
        self.assertIn("#dc2626", text)
        self.assertIn("#16a34a", text)

    def test_remote_status_text_uses_colored_labels(self) -> None:
        application = Application(
            name="demo",
            repository_url="https://git.example.com/demo.git",
            group_english_name="server",
            local_dir_name="demo",
        )
        status = RepositoryStatus(
            application=application,
            local_path=application.resolve_local_path(Path("/tmp")),
            exists=True,
            branch="master",
            has_local_changes=False,
            has_unpushed_commits=False,
            has_remote_updates=True,
            message="状态已刷新",
        )

        self.assertIn("有新代码", remote_status_text(status))
        self.assertIn("#dc2626", remote_status_text(status))


if __name__ == "__main__":
    unittest.main()
