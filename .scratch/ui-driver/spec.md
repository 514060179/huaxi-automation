# UI 驱动项目 Spec

功能目录：`.scratch/ui-driver/`

## 目标

驱动真实 `WeChat.app` 中的“华夏会计网”小程序，按正常路径完成所有 `status=1` 任务内所有未完成小节的学习与微信认证，并在学习过程中截取真实小程序里的认证二维码。

## 背景

`001.chlz` 已完成接口清单、调用时序和认证闭环分析。上一轮已确认：

- 不使用自造 HTTP 客户端伪造请求，改为真实微信客户端 UI 自动化，使 TLS、header、cookie、deviceId 天然与抓包一致。
- 只读 planner 用现有 token 枚举未完成小节清单，不做学习状态变更。
- 首轮保留 Charles 代理作为验证旁路，对比实时流量与 `001.chlz`。
- 新建独立项目 `ui-driver`；`integration-harness` 保留作参考和只读规划/结果核对参考，不删除。

## 可行性探测结论

1. 授予“辅助功能”和“屏幕录制”后，可以通过 `System Events` 读到 `WeChat` 进程和窗口列表。
2. 小程序窗口 `华夏会计网校` 的 AX 树 `childCount=0`，是整块不透明 webview，不能依赖 AX 元素读取/点击。
3. 通过 `screencapture -R<x,y,w,h>` 可以截取小程序窗口内容；截图尺寸是 Retina 2x，内容非黑图。
4. 使用 macOS Vision 的 `VNRecognizeTextRequest` 可以稳定识别小程序页面文本和归一化 bounding box，进而把文本坐标换算成屏幕点击坐标。
5. 使用 macOS Vision 的 `VNDetectBarcodesRequest` 可以识别二维码，返回 payload URL 和 bounding box；本地生成的测试二维码已验证可检出。
6. 使用 Quartz `CGEvent` 可以在真实小程序窗口内点击。实测点击“专业课 → 开始学习 → 已知晓，前往学习”成功进入任务详情页。
7. 窗口尺寸会随页面从单栏课程列表变为双栏任务详情而改变；实现必须动态读取窗口 bounds，不能写死 414×780。

## 架构

新项目：`ui-driver/`，Python 包 `ui_driver`。

核心组件：

- `config`：环境变量/`.env`，与 `integration-harness` 保持互不依赖。
- `planner`：只读调用 `getTaskList` / `getMytaskDetail` / `getTaskCourseList` / `getMycourseDetail`，输出任务、课程、未完成小节清单和 `learned[docId].status`。
- `window`：动态发现 `WeChat` 的“华夏会计网校”窗口，读取 bounds，前台化，按 bounds 截图。
- `vision`：OCR 文本 + bounding box、二维码检测 + payload/bounding box。
- `input`：Quartz 鼠标点击、滚轮、键盘事件；把 OCR bounding box 转成屏幕坐标。
- `runner`：按 planner 清单驱动真实小程序，等待视频播放/心跳，检测二维码，暂停学习，截屏，等待人工扫码认证，恢复学习，继续到 `finish`。
- `validation`：首轮 Charles 旁路，生成实时流量与 `001.chlz` 的对比证据。
- `runs`：运行目录，含日志、事件、截图和验证报告。

## 完成判据

- 对每个 `status=1` 任务，遍历其所有课程。
- 对每个课程中 `learned[docId].status != "finish"` 的小节，完成一次正常学习闭环。
- 遇到认证二维码时，必须走完“暂停 → 截图 → 人工扫码 → 验证成功 → 恢复学习”。
- 小节完成以只读 planner 后续查询到 `learned[docId].status == "finish"` 为准。
- 截图保存到 `runs/<session_id>/screenshots/qr-<ts>.png` 和 `qr-verified-<ts>.png`。
- 首轮同时产出 Charles 流量与 `001.chlz` 的一致性核对结果。

## 非目标

- 不自动获取或猜测微信 `code`、token、deviceId；token 由测试人员从授权抓包会话手动提供。
- 不绕过、不爆破、不并发攻击，不修改业务数据。
- 不模拟“本地二维码页面”，必须截真实小程序窗口中的二维码区域。

## 风险

- 小程序页面结构变化会影响 OCR 文本和坐标。
- 微信客户端版本升级可能改变窗口尺寸、字体或渲染方式。
- 二维码出现的视觉样式可能不同于当前样本，需要在真实触发点再次验证 `VNDetectBarcodesRequest`。
- 视频播放时长和认证触发时间取决于真实业务状态，整轮可能很长。
