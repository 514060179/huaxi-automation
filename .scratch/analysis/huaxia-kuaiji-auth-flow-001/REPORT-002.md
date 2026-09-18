# 002.chlz 分析：微信认证结果确认

会话编号：`huaxia-kuaiji-auth-flow-002`  
原始文件：`002.chlz`  
录制时间：2026-09-15 14:35:18 至 14:37:04  
请求数：6 个 API 请求，无视频分片

## 结论

第二个抓包文件证明微信认证已经完成。桌面小程序通过 `gdQueryVerificationResults` 轮询到：

```json
{
  "verifyResult": "1",
  "raw": {
    "status": "200",
    "msg": "已验证！",
    "data": "1"
  }
}
```

之后小程序立即调用 `gdResumeCourse` 恢复学习，状态回到 `IN_PROGRESS`。

## 请求时间线

| 时间 | 接口 | 说明 |
| --- | --- | --- |
| 14:35:18.785 | `getMycourseDetail` | 检查课程状态，认证仍为 `PENDING` |
| 14:35:19.538 | `guangdongPoint` / `gdGetPointState` | 学习状态为 `PAUSED`，认证仍为 `PENDING` |
| 14:37:03.971 | `guangdongPoint` / `gdQueryVerificationResults` | 返回 `verifyResult=1`，已认证 |
| 14:37:03.973 | `getMycourseDetail` | 再次检查课程详情 |
| 14:37:04.957 | `guangdongPoint` / `gdResumeCourse` | 恢复学习，状态 `IN_PROGRESS` |
| 14:37:04.957 | `guangdongPoint` / `gdGetPointState` | 学习状态已恢复 |

## 与 001.chlz 的衔接

`001.chlz` 停在：

- `verifyResult: 0`
- `verifyStatus: PENDING`
- `learnStatus: PAUSED`

`002.chlz` 补齐了后续：

- 手机扫码完成后，桌面小程序再次进入课程页
- 调用 `gdQueryVerificationResults` 得到“已验证！”
- 自动恢复播放

因此完整的认证闭环是：

`postUpdateTimeGuangdong` 触发二维码 → 小程序暂停 → 用户在手机微信扫码完成认证 → 小程序轮询 `gdQueryVerificationResults` 得到成功 → `gdResumeCourse` 恢复学习。

## 备注

在 `002.chlz` 的 `gdGetPointState` 响应里，外层 `pointState.verifyStatus` 仍然是 `PENDING`，但 `gdQueryVerificationResults` 已返回“已验证！”。这说明外层字段可能是缓存/延迟更新；判断认证成功应以 `gdQueryVerificationResults.verifyResult` 为准。
