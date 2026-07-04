from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from code_manager.infrastructure.git_service import RepositoryStatus

STATUS_COLOR_POSITIVE = "#16a34a"
STATUS_COLOR_NEGATIVE = "#dc2626"


def _colored_text(text: str, *, positive: bool) -> str:
    color = STATUS_COLOR_POSITIVE if positive else STATUS_COLOR_NEGATIVE
    return f'<span style="color: {color};">{text}</span>'


def local_status_text(status: RepositoryStatus | None) -> str:
    if status is None:
        return "-"
    if not status.exists:
        return "本地仓库不存在"

    commit_text = "有待提交内容" if status.has_local_changes else "无待提交内容"
    push_text = "有待push内容" if status.has_unpushed_commits else "无待push内容"
    return (
        f"分支: {status.branch}; "
        f"{_colored_text(commit_text, positive=not status.has_local_changes)}; "
        f"{_colored_text(push_text, positive=not status.has_unpushed_commits)}"
    )


def remote_status_text(status: RepositoryStatus | None) -> str:
    if status is None or not status.exists:
        return "-"
    if status.has_remote_updates:
        return _colored_text("有新代码", positive=False)
    return _colored_text("无新代码", positive=True)


def build_status_cell(text: str) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(6, 4, 6, 4)
    layout.setSpacing(2)

    label = QLabel(text)
    label.setWordWrap(False)
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    layout.addWidget(label)
    return widget
