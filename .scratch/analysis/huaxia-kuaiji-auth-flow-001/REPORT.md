# 华夏会计网微信认证链路分析报告

会话编号：`huaxia-kuaiji-auth-flow-001`  
原始文件：`001.chlz`  
录制时间：2026-09-15 13:57:45 至 14:16:09（约 18 分 24 秒）

## 结论摘要

本次抓包完整覆盖了从打开“华夏会计网”小程序、进入专业课、开始学习、播放 HLS 视频，到广东省继续教育微信认证二维码出现、暂停课程、查询验证结果的过程。

后续的 `002.chlz` 已补齐认证成功闭环，详见 [REPORT-002.md](./REPORT-002.md)。

关键发现：

- 微信登录入口是 `POST /index.php/api/user/wechatLogin`，请求携带微信临时 `code`、设备号和身份证号，响应返回 `token`、`memberId`、`openid`。
- 学习业务 API 集中在 `learn.hxacc.com`，使用同一个 Bearer JWT 鉴权。
- 视频流来自 `v1.hxacc.com`，每约 10 秒请求一个 HLS `.ts` 分片，本次共 91 个分片。
- 学习进度通过 `postUpdateTimeGuangdong` 心跳接口每约 60 秒上报一次。
- 微信认证不是“30 分钟后”才出现；本次在视频播放约 15 分 39 秒时，最后一次心跳响应里返回了新的 `needPoint: true` 和二维码地址。
- 扫码动作没有经过桌面 Charles。二维码指向 `https://kj.czt.gd.gov.cn:8093/miniprogram/...`，应由手机微信访问该域名；因此本次抓包里没有该域名的请求。
- 会话结束时，`gdQueryVerificationResults` 返回 `verifyResult: 0`，即“未验证”。认证结果尚未同步或尚未完成。

## 补充：002.chlz 结论

`002.chlz` 证明认证最终成功：

- `gdQueryVerificationResults` 返回 `verifyResult: 1`
- `raw.msg` 为“已验证！”
- 随后 `gdResumeCourse` 恢复学习，`learnStatus` 回到 `IN_PROGRESS`

完整认证闭环：

`postUpdateTimeGuangdong` 返回二维码 → 课程暂停 → 用户手机扫码 → `gdQueryVerificationResults` 查询到已验证 → `gdResumeCourse` 恢复学习。

## 主机与端口

| 主机 | 用途 | 端口 |
| --- | --- | --- |
| `www.hxacc.com` | 首页新闻、微信登录 | 443 |
| `learn.hxacc.com` | 学习任务、课程、进度、广东监管接口 | 443 |
| `v1.hxacc.com` | HLS 视频分片 | 443 |
| `kj.czt.gd.gov.cn` | 认证二维码目标地址 | 8093 |

## 请求量统计

| 类型 | 数量 |
| --- | --- |
| API 请求 | 33 |
| 视频 `.ts` 分片 | 91 |
| 总计 | 124 |

## 认证链路

1. 小程序启动时先请求首页新闻列表，然后调用 `wechatLogin` 完成登录。
2. 登录成功后拿到 JWT，后续所有 `learn.hxacc.com` 请求都带 `Authorization: Bearer <JWT>`。
3. 进入“专业课”后，通过 `getMytaskDetail`、`getTaskCourseList`、`postLearnCourse`、`getMycourseDetail` 加载课程和小节。
4. `gdGetPointState` 建立广东学习监管状态，`gdResumeCourse` 开始学习。
5. 播放视频期间，`postUpdateTimeGuangdong` 心跳持续上报 `docPlayTime` 和 `lastTime`。
6. 最后一次心跳返回 `needPoint: true`、新的 `pointCode`、`qrcodeUrl` 和 `verifyStatus: PENDING`，这是二维码认证触发点。
7. 小程序随即调用 `gdPauseCourse` 暂停课程。
8. 约 2 分 43 秒后，小程序调用 `gdQueryVerificationResults` 查询认证结果，返回“未验证”；随后 `gdGetPointState` 仍显示 `PENDING`。

## 关键时间点

| 时间 | 事件 |
| --- | --- |
| 13:57:45.674 | 请求首页新闻列表 |
| 13:57:45.807 | 微信登录 |
| 13:57:54.966 | 获取任务列表 |
| 13:58:05.563 | 进入“新《会计法》对财务人员的影响”课程 |
| 13:58:07.770 | 广东监管接口恢复学习 |
| 13:58:18.058 | 开始拉取第一个视频分片 |
| 14:13:24.888 | 心跳响应返回认证二维码 |
| 14:13:26.119 | 暂停课程 |
| 14:16:08.723 | 查询认证结果，仍为未验证 |
| 14:16:09.499 | 查询广东学习状态，仍为 PENDING |

## 需要继续观察的点

- 本次没有捕获到手机扫码后与 `kj.czt.gd.gov.cn` 的交互，因此无法判断认证是否在手机端完成。
- 如果要拿到“验证成功”的闭环，建议继续录制到 `gdQueryVerificationResults` 返回 `verifyResult: 1` 或状态变为 `VERIFIED`。
- 若需要复现完整闭环，第二次会话可命名为 `huaxia-kuaiji-auth-flow-002`。

## 隐私说明

原始文件包含身份证号、微信 `code`、JWT、`openid`、用户真实姓名等敏感信息，按要求仅保存在本地。
