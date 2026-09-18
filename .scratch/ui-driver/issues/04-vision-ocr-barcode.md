Status: resolved
Type: task
Blocked by: 01

# 04 Vision 文字识别与二维码检测

## 目标

封装 macOS Vision，提供 OCR 文本 + bounding box，以及二维码 payload + bounding box。

## 验收标准

- `recognize_text(image_path)` 返回文本、归一化 bounding box 和像素坐标。
- `detect_barcode(image_path)` 能识别 QR payload 和 bounding box。
- 对已知测试二维码稳定返回 payload URL。
- 对无二维码截图返回空列表。
- 支持中文识别语言 `zh-Hans` 和英文 `en-US`。

## Notes

- Vision bounding box 使用左下角原点；转换为屏幕/窗口坐标时要小心。
- 截图是 Retina 2x，必须用图像像素尺寸换算逻辑点。

## Answer

已实现 `ui_driver/vision.py`：`recognize_text` 返回文本和像素 box，`detect_barcodes` 返回 payload 和像素 box。对测试二维码可稳定检出，对当前无二维码窗口返回空列表；中文 OCR 可识别课程列表、任务详情和弹窗文本。
