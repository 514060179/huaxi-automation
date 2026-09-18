Status: resolved
Type: task
Blocked by: none

# 01 脚手架独立 ui-driver 项目

## 目标

在仓库根目录新建 `ui-driver/`，使其能作为独立 Python 项目安装和运行。

## 验收标准

- 存在 `ui-driver/pyproject.toml`，包名为 `ui-driver`，Python 包为 `ui_driver`。
- 存在 `ui_driver/__init__.py` 和 `ui_driver/__main__.py`。
- `python -m ui_driver --help` 至少能显示帮助，不依赖 `integration-harness`。
- 依赖包含 macOS 所需的 `pyobjc-framework-Cocoa`、`pyobjc-framework-Quartz`、`pyobjc-framework-Vision`。
- 存在 `.env.example`、`.gitignore`、`README.md`。
- 存在空运行目录约定 `runs/<session_id>/`。

## Notes

- 项目只面向 macOS，暂不做跨平台兼容。
- 测试依赖 `pytest`。

## Answer

已在 `ui-driver/` 建立独立项目：`pyproject.toml`、`ui_driver` 包、`__main__.py`、`README.md`、`.env.example`、`.gitignore` 和基础测试目录。`PYTHONPATH=. python3 -m ui_driver --help` 可正常显示帮助。
