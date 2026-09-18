# Context Map

## Contexts

- [微信小程序请求行为分析](./CONTEXT.md)：分析“华夏会计网”小程序的网络请求与认证链路。
- [真实环境集成测试 harness](./integration-harness/CONTEXT.md)：按正常接口时序驱动真实后端完成课程学习和微信认证。
- [微信小程序 UI 驱动](./ui-driver/CONTEXT.md)：驱动真实 `WeChat.app` 完成课程学习、微信认证和二维码截图。

## Relationships

- **微信小程序请求行为分析 → 真实环境集成测试 harness**：抓包分析产出的接口清单和时序，作为集成测试 harness 的参考路径。
- **真实环境集成测试 harness → 微信小程序请求行为分析**：真实运行中发现的字段或状态变化，可以回写补充分析结论。
- **微信小程序请求行为分析 → 微信小程序 UI 驱动**：抓包分析产出的接口清单、时序和二维码触发规则，作为 UI 驱动的识别与验证参照。
- **微信小程序 UI 驱动 → 真实环境集成测试 harness**：UI 驱动中只读 planner 和结果核对可复用 harness 已稳定字段与事件结构。
