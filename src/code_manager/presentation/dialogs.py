from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from code_manager.domain.models import Application, Group, SystemProfile


class SystemDialog(QDialog):
    def __init__(self, system: SystemProfile | None = None) -> None:
        super().__init__()
        self.setWindowTitle("系统配置")
        self.name_input = QLineEdit(system.name if system else "")
        self.code_root_input = QLineEdit(str(system.code_root) if system else "")

        form = QFormLayout()
        form.addRow("系统名称", self.name_input)
        form.addRow("代码根目录", self.code_root_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def system(self) -> SystemProfile:
        return SystemProfile(
            name=self.name_input.text().strip(),
            code_root=Path(self.code_root_input.text().strip()).expanduser(),
        )


class GroupDialog(QDialog):
    def __init__(self, group: Group | None = None) -> None:
        super().__init__()
        self.setWindowTitle("分组配置")
        self.chinese_name_input = QLineEdit(group.chinese_name if group else "")
        self.english_name_input = QLineEdit(group.english_name if group else "")

        form = QFormLayout()
        form.addRow("中文名", self.chinese_name_input)
        form.addRow("英文名", self.english_name_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def group(self) -> Group:
        return Group(
            chinese_name=self.chinese_name_input.text().strip(),
            english_name=self.english_name_input.text().strip(),
        )


class ApplicationDialog(QDialog):
    def __init__(
        self,
        application: Application | None = None,
        group_options: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("应用配置")
        self.name_input = QLineEdit(application.name if application else "")
        self.repository_url_input = QLineEdit(application.repository_url if application else "")
        self.group_input = QComboBox()
        self.group_input.setEditable(False)
        groups = group_options or []
        self.group_input.addItems(groups)
        if application and application.group_english_name:
            if application.group_english_name not in groups:
                self.group_input.addItem(application.group_english_name)
            self.group_input.setCurrentText(application.group_english_name)
        self.local_dir_input = QLineEdit(application.local_dir_name if application else "")

        field_min_width = 560
        self.setMinimumWidth(640)
        for widget in (
            self.name_input,
            self.repository_url_input,
            self.group_input,
            self.local_dir_input,
        ):
            widget.setMinimumWidth(field_min_width)

        form = QFormLayout()
        form.addRow("应用名", self.name_input)
        form.addRow("仓库地址", self.repository_url_input)
        form.addRow("分组英文名", self.group_input)
        form.addRow("本地目录名", self.local_dir_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def application(self) -> Application:
        return Application(
            name=self.name_input.text().strip(),
            repository_url=self.repository_url_input.text().strip(),
            group_english_name=self.group_input.currentText().strip(),
            local_dir_name=self.local_dir_input.text().strip(),
        )


class ImportRepositoriesDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("导入仓库")
        self.repository_text = QPlainTextEdit()
        self.repository_text.setPlaceholderText(
            "粘贴仓库地址，支持换行或空格分隔"
        )
        self.repository_text.setMinimumSize(640, 360)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.repository_text)
        layout.addWidget(buttons)

    def repositories_text(self) -> str:
        return self.repository_text.toPlainText()
