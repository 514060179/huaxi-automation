Status: claimed
Type: task
Blocked by: 02, 05

# 06 完整学习与认证编排

## 目标

把 planner 清单、窗口截图、OCR、二维码检测、点击/滚动和人工扫码调度串成完整 runner。

## 验收标准

- 按任务/课程/小节的顺序进入目标小节并开始学习。
- 播放期间持续截图并检测二维码。
- 检测到二维码后：暂停课程、截图 `qr-<ts>.png`、提示人工扫码。
- 轮询二维码页面视觉状态或结合只读查询，判断认证成功。
- 认证成功后截图 `qr-verified-<ts>.png`，恢复学习。
- 后续查询 `learned[docId].status == "finish"` 后进入下一个小节。
- 任一环节失败中断整轮；`SKIP_BAD_DOC=true` 时允许跳过坏小节继续。

## Notes

- 认证成功判断优先以只读 planner 查询 `learned`/`verifyResult` 为准，视觉状态作为辅助。
- 同一小节可能触发多次二维码，必须支持循环。

## Comments

- 已实现 `ui_driver/runner.py` 和 `python -m ui_driver run` 的基础编排：任务/课程/小节导航、二维码检测与截图、认证成功截图、只读 planner 完成态轮询。
- 尚未做真实 E2E 运行；真实二维码出现、认证成功 UI 文案、视频播放页结构需要首次运行继续校正。
