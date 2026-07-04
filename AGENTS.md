# AGENTS.md

给后续在这个仓库里 vibing coding 的代理或开发者看的项目说明。先读这个，再动代码。

## 项目定位

这是一个用 Python + PySide6 写的桌面应用，用来管理多个系统的代码仓库。

核心概念：

- 系统：一个业务系统，包含系统名和本地代码根目录。
- 分组：系统内的应用分组，包含中文名和英文名。
- 应用：一个 Git 仓库配置，包含应用名、仓库地址、所属分组英文名、本地目录名。
- 本地仓库路径：`系统本地代码根目录 / 分组英文名 / 本地目录名`。

配置存储在当前用户 Home 下：

```text
~/.code-manager/config.json
```

## 技术栈

- Python 3.11+
- uv 管理依赖和运行命令
- PySide6 桌面 UI
- 本机 Git 命令执行 clone、pull、status、fetch 等操作
- 不额外依赖 YAML 库，系统导入导出使用项目内受控 YAML 读写器

## 常用命令

```powershell
uv sync
uv run code-manager
```

测试：

```powershell
$env:UV_CACHE_DIR='.uv-cache'
$env:QT_QPA_PLATFORM='offscreen'
uv run python -m unittest discover -s tests
```

编译检查：

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python -m compileall src tests
```

检查不要出现中文 Unicode 转义：

```powershell
rg "\\u[0-9a-fA-F]{4}" src tests
```

`rg` 返回退出码 1 且无输出表示没匹配到，是正常结果。

## 目录结构

```text
src/code_manager/
  domain/            领域模型和仓库地址解析
  application/       应用服务，组合领域逻辑和持久化
  infrastructure/    配置文件、Git、YAML 导入导出等外部能力
  presentation/      PySide6 窗口、对话框、后台 worker
tests/               unittest 测试
```

主要文件：

- `domain/models.py`：`SystemProfile`、`Group`、`Application`、`CodeManagerConfig`
- `application/config_service.py`：配置增删改、仓库导入、系统 YAML 导入导出
- `infrastructure/config_store.py`：`~/.code-manager/config.json` 读写
- `infrastructure/git_service.py`：Git 操作
- `infrastructure/system_yaml.py`：系统配置 YAML 导入导出
- `presentation/main_window.py`：系统管理窗口
- `presentation/system_detail_window.py`：系统详情窗口
- `presentation/repository_config_window.py`：仓库配置窗口
- `presentation/group_config_window.py`：分组配置窗口

## UI 规则

用户对 UI 细节很敏感，改界面时务必遵守：

- 系统管理窗口显示系统列表；每行操作按钮放在该行后面。
- 系统详情窗口显示仓库状态；不要显示仓库地址和本地路径，只显示分组、应用名、分支、本地改动、远端新代码、操作。
- 仓库配置窗口只配置应用；分组配置窗口只配置分组。
- 同一个系统只能打开一个详情窗口。
- 同一个系统只能打开一个仓库配置窗口、一个分组配置窗口。
- 列表页默认不可选中，不显示单元格光标。
- 四个表格都允许用户用鼠标调整列宽。
- 不允许刚打开窗口就出现横向滚动条。
- 表格宽度要铺满窗口，最后一列通常用 `setStretchLastSection(True)` 吃掉剩余空间。
- 行内操作按钮必须固定宽度，不要因为内容或拉伸留下大块空白。
- 列表项高度固定，避免编辑状态或刷新后跳动。
- 系统列表的编辑按钮使用弹窗编辑；不要再改成行内编辑。
- 分组列表和仓库列表支持双击单元格编辑。
- 仓库列表的分组列编辑时使用下拉框。

## Git 操作规则

系统详情窗口顶部有 `操作应用于 sub module` 复选框。

- 勾选时：clone、拉代码需要处理 submodule。
- 不勾选时：Git 命令必须显式禁止 submodule 行为，不能依赖 Git 默认行为。

当前约定：

- clone 不含 submodule：`git clone --no-recurse-submodules ...`
- clone 含 submodule：`git clone --recurse-submodules ...`
- pull 不含 submodule：使用 `-c submodule.recurse=false` 和 `--recurse-submodules=no`
- pull 含 submodule：pull 后执行 `git submodule update --init --recursive`

仓库未 clone 到本地时，系统详情里的“本地改动”显示 `未clone`。

## 系统 YAML 导入导出

系统列表窗口：

- 顶部有 `导入系统` 按钮。
- 每个系统行后面有 `导出` 按钮。

YAML 用来给别人迁移系统配置，包含：

- 系统名
- 分组列表
- 应用仓库列表

导出 YAML 时不要包含系统在本机的代码根目录，这个路径属于个人机器配置。

导入 YAML 时先读取系统名、分组和应用列表，再让用户填写当前机器的系统代码根目录，最终用系统名 upsert 到配置里。

## 编码约定

- 写中文就直接写中文，不要写成 Unicode 转义。
- 新文件默认 UTF-8。
- 手工改文件用 `apply_patch`。
- 不要随手重构无关代码。
- 不要回滚用户已有改动。
- 新行为优先补测试，至少覆盖服务层和关键 UI 行为。
- PySide6 测试设置：

```python
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
```

## 测试分布

- `test_models.py`：领域模型行为
- `test_application_service.py`：应用服务行为
- `test_config_store.py`：配置存储兼容性
- `test_git_service.py`：Git 命令行为
- `test_system_yaml.py`：系统 YAML 导入导出
- `test_main_window.py`：系统管理窗口
- `test_system_detail_window.py`：系统详情窗口
- `test_repository_config_window.py`：仓库配置窗口
- `test_group_config_window.py`：分组配置窗口
- `test_dialogs.py`：对话框
- `test_repo_parser.py`：仓库地址解析

## 改动前检查清单

动代码前先确认：

- 这次改动属于哪个层：domain、application、infrastructure、presentation。
- 有没有现成服务或模型方法可以复用。
- UI 改动会不会重新出现横向滚动条、单元格光标、按钮错位。
- Git 命令有没有明确处理 submodule 开关。
- 中文有没有被转义或写成乱码。

交付前跑：

```powershell
$env:UV_CACHE_DIR='.uv-cache'
$env:QT_QPA_PLATFORM='offscreen'
uv run python -m unittest discover -s tests
uv run python -m compileall src tests
rg "\\u[0-9a-fA-F]{4}" src tests
```
