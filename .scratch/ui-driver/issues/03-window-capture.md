Status: resolved
Type: task
Blocked by: 01

# 03 微信小程序窗口发现与截图

## 目标

动态发现真实 `WeChat` 中的“华夏会计网校”小程序窗口，并按其当前 bounds 截取内容。

## 验收标准

- 通过 Quartz `CGWindowListCopyWindowInfo` 找到 owner 为“微信”、name 为“华夏会计网校”的窗口。
- 每次操作前重新读取 bounds，不能写死 414×780 或 829×780。
- 支持将微信进程前置到前台。
- 支持按 bounds 使用 `screencapture -R` 或等价方式截图。
- 截图可被 Vision OCR 读取。

## Notes

- 窗口从单栏课程列表切换到双栏任务详情时 bounds 会变化。
- 截图坐标为逻辑点，图像像素是 Retina 2x；转换逻辑要封装在 vision/input 层。

## Answer

已实现 `ui_driver/window.py`，用 Quartz 动态发现 owner 为“微信”、name 为“华夏会计网校”的窗口，并支持前台化和按 bounds 截图。实测窗口 bounds 从 414×780 变为 829×780，动态发现有效。
