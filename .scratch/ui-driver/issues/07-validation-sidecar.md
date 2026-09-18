Status: ready-for-agent
Type: task
Blocked by: 06

# 07 Charles 验证旁路

## 目标

首轮运行时让 Charles 代理真实客户端，抓取实时流量，并与 `001.chlz` 做一致性核对。

## 验收标准

- 运行前检查 Charles 代理和 SSL Proxying 状态。
- 运行后导出或读取本轮流量。
- 对比三套 host 的 header 模板、TLS 版本、ALPN、HTTP 版本、关键 cookie/authorization 位置。
- 产出 `validation.md`，说明一致项、差异项和原因。

## Notes

- 只读 planner 流量是规划流量，不作为 `001.chlz` 学习链路的 1:1 对比对象。
- Charles 与 UI 自动化并发时，若出现连接不稳定，需记录为待观察项。
