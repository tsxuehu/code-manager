# 代码管理器

代码管理器是一个 Python 桌面应用，用于统一管理一个系统下所有应用的代码仓库。

## 技术栈

- Python 3.11+
- uv 依赖管理
- PySide6 桌面界面
- 本机 Git 命令执行仓库操作

## 功能

- 配置系统代码在本地的存放根目录
- 管理应用分组，分组包含中文名和英文名
- 管理应用，配置应用名称、仓库地址、所属分组、本地目录名
- 批量导入仓库地址，一行一个仓库
- 根据仓库地址自动解析分组英文名和本地目录名
- 一键 clone 全部仓库，已存在的仓库会跳过
- 查看仓库当前分支、本地改动、远端新代码状态
- 一键更新全部本地仓库

## 本地路径规则

仓库在本地的路径按以下规则生成：

```text
系统代码根目录 / 分组英文名 / 仓库本地目录名
```

例如：

```text
D:/workspace/platform/order-service
```

## 配置存储

配置文件存放在当前用户 Home 目录下：

```text
~/.code-manager/config.json
```

## 开发

```powershell
uv sync
uv run code-manager
uv run python -m unittest discover -s tests
```

如果本机 uv 缓存目录异常，可以临时把缓存放到项目目录：

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run code-manager
```