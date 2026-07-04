from __future__ import annotations

import json
from pathlib import Path

from code_manager.domain.models import Application, Group, SystemProfile


def dump_system_to_yaml(system: SystemProfile) -> str:
    lines = [
        "system:",
        f"  name: {_quote(system.name)}",
        f"  code_root: {_quote(str(system.code_root))}",
        "groups:",
    ]
    if system.groups:
        for group in system.groups:
            lines.extend(
                [
                    f"  - chinese_name: {_quote(group.chinese_name)}",
                    f"    english_name: {_quote(group.english_name)}",
                ]
            )
    else:
        lines[-1] = "groups: []"

    lines.append("applications:")
    if system.applications:
        for application in system.applications:
            lines.extend(
                [
                    f"  - name: {_quote(application.name)}",
                    f"    repository_url: {_quote(application.repository_url)}",
                    f"    group_english_name: {_quote(application.group_english_name)}",
                    f"    local_dir_name: {_quote(application.local_dir_name)}",
                ]
            )
    else:
        lines[-1] = "applications: []"

    return "\n".join(lines) + "\n"


def load_system_from_yaml(yaml_text: str) -> SystemProfile:
    data: dict[str, object] = {
        "system": {},
        "groups": [],
        "applications": [],
    }
    section: str | None = None
    current_item: dict[str, str] | None = None

    for raw_line in yaml_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if not line.startswith(" "):
            if stripped == "system:":
                section = "system"
            elif stripped in ("groups:", "groups: []"):
                section = "groups"
            elif stripped in ("applications:", "applications: []"):
                section = "applications"
            else:
                raise ValueError(f"无法识别的 YAML 配置行: {stripped}")
            current_item = None
            continue

        if section == "system":
            key, value = _parse_key_value(stripped)
            system_data = data["system"]
            assert isinstance(system_data, dict)
            system_data[key] = _parse_scalar(value)
            continue

        if section in ("groups", "applications"):
            target_items = data[section]
            assert isinstance(target_items, list)
            if stripped.startswith("- "):
                current_item = {}
                target_items.append(current_item)
                rest = stripped[2:].strip()
                if rest:
                    key, value = _parse_key_value(rest)
                    current_item[key] = _parse_scalar(value)
            else:
                if current_item is None:
                    raise ValueError(f"YAML 列表项格式错误: {stripped}")
                key, value = _parse_key_value(stripped)
                current_item[key] = _parse_scalar(value)
            continue

        raise ValueError(f"YAML 配置缺少所属区域: {stripped}")

    system_data = data["system"]
    assert isinstance(system_data, dict)
    name = str(system_data.get("name", "")).strip()
    if not name:
        raise ValueError("系统名称不能为空")
    code_root = Path(str(system_data.get("code_root", str(Path.home() / "code"))))

    group_items = data["groups"]
    application_items = data["applications"]
    assert isinstance(group_items, list)
    assert isinstance(application_items, list)

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


def _quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _parse_key_value(text: str) -> tuple[str, str]:
    if ":" not in text:
        raise ValueError(f"YAML 键值格式错误: {text}")
    key, value = text.split(":", 1)
    return key.strip(), value.strip()


def _parse_scalar(value: str) -> str:
    if value.startswith('"') and value.endswith('"'):
        loaded = json.loads(value)
        return str(loaded)
    return value


def _required(item: object, key: str, message: str) -> str:
    if not isinstance(item, dict):
        raise ValueError(message)
    value = str(item.get(key, "")).strip()
    if not value:
        raise ValueError(message)
    return value
