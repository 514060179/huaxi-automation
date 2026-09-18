# ui-driver Wayfinding Map

## Notes

- Feature slug：`ui-driver`
- 独立项目目录：`ui-driver/`
- 只读 planner 与真实客户端 UI 自动化严格分离
- `integration-harness` 保留作参考，不删除

## Decisions-so-far

- 驱动层：真实 `WeChat.app` UI 自动化。
- 验证旁路：首轮 Charles 代理真实客户端，与 `001.chlz` 对比。
- 只读 planner：使用现有 token 枚举未完成小节。
- 范围：所有 `status=1` 任务（含公需课）→ 所有课程 → 所有 `status != finish` 小节。
- 完成判据：`learned[docId].status == "finish"`。
- 二维码：真实小程序窗口截图，出现时与认证成功后各截一张。
- 失败策略：任一环节失败中断整轮；“跳过坏小节”为默认关闭开关。
- 可行路径：AX 树不可读；使用窗口截图 + Vision OCR/二维码识别 + Quartz 点击。
- 已实现：独立项目脚手架、只读 planner、窗口发现/截图、Vision OCR/二维码检测、Quartz 点击/滚动/键盘。
- 已实现基础 runner：`python -m ui_driver run` 按 plan 进入任务/课程/小节，等待二维码，保存出现/认证成功截图，并用只读 planner 轮询完成状态。

## Fog

- 真实二维码触发时的视觉样式尚未在实际页面验证。
- 视频播放中窗口是否保持同一 bounds、是否有全屏/浮动层，需要在真实运行中观察。
- Charles 旁路与 UI 自动化的并发稳定性尚未验证。
- 课程小节页、视频播放页和二维码出现页的具体页面结构仍需在真实运行中逐步补齐识别规则。

## Tickets

- [01-scaffold-project](issues/01-scaffold-project.md)
- [02-read-only-planner](issues/02-read-only-planner.md)
- [03-window-capture](issues/03-window-capture.md)
- [04-vision-ocr-barcode](issues/04-vision-ocr-barcode.md)
- [05-ui-actions](issues/05-ui-actions.md)
- [06-runner-full-loop](issues/06-runner-full-loop.md)
- [07-validation-sidecar](issues/07-validation-sidecar.md)
- [08-e2e-smoke-and-docs](issues/08-e2e-smoke-and-docs.md)
