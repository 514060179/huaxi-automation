Status: resolved
Type: task
Blocked by: 03, 04

# 05 鼠标与键盘操作

## 目标

将 OCR 文本/bounding box 转为屏幕坐标，并执行真实点击、滚动和键盘操作。

## 验收标准

- 提供按文本定位并点击元素的能力。
- 提供按窗口内逻辑坐标点击的能力。
- 提供滚轮滚动能力，用于课程列表和长页面。
- 提供 Escape/Enter 等键盘事件。
- 实测能点击“专业课 → 开始学习 → 已知晓，前往学习”。

## Notes

- 点击使用 Quartz `CGEvent`。
- 屏幕坐标 = 窗口 origin + bounding box 中心换算后的逻辑点。
- 点击前确保微信窗口在前台，避免点到其他窗口。

## Answer

已实现 `ui_driver/input.py`：Quartz 鼠标点击、键盘事件和滚动事件，并提供 `click_window_pixel` 换算。实测能点击“专业课 → 开始学习 → 已知晓，前往学习”，成功进入任务详情页。
