from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from code_manager.domain.models import Application, Group, SystemProfile


def dump_system_to_yaml(system: SystemProfile) -> str:
    data = {
        "system": {
            "name": system.name,
        },
        "groups": [
            {
                "chinese_name": group.chinese_name,
                "english_name": group.english_name,
            }
            for group in system.groups
        ],
        "applications": [
            {
                "name": application.name,
                "repository_url": application.repository_url,
                "group_english_name": application.group_english_name,
                "local_dir_name": application.local_dir_name,
            }
            for application in system.applications
        ],
    }
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def load_system_from_yaml(yaml_text: str) -> SystemProfile:
    try:
        data = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML 文件格式错误: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("YAML 根节点必须是对象")

    system_data = data.get("system") or {}
    if not isinstance(system_data, dict):
        raise ValueError("系统配置格式错误")
    name = str(system_data.get("name", "")).strip()
    if not name:
        raise ValueError("系统名称不能为空")
    code_root = Path.home() / "code"

    group_items = _list_items(data.get("groups", []), "分组配置格式错误")
    application_items = _list_items(data.get("applications", []), "应用配置格式错误")

    return SystemProfile(
        name=name,
        code_root=code_root,
        groups=[
            Group(
                chinese_name=_required(item, "chinese_name", "分组中文名不能为空"),
                english_name=_required(item, "english_name", "分组英文名不能为空"),
            )
            for item in group_items
        ],
        applications=[
            Application(
                name=_required(item, "name", "应用名不能为空"),
                repository_url=_required(item, "repository_url", "仓库地址不能为空"),
                group_english_name=str(item.get("group_english_name", "")),
                local_dir_name=_required(item, "local_dir_name", "本地目录名不能为空"),
            )
            for item in application_items
        ],
    )

def _list_items(value: object, message: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(message)
    return value


def _required(item: object, key: str, message: str) -> str:
    if not isinstance(item, dict):
        raise ValueError(message)
    value = str(item.get(key, "")).strip()
    if not value:
        raise ValueError(message)
    return value
