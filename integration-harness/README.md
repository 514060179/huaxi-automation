# Integration Harness

真实环境集成测试 harness，用于按已抓包得到的正常接口时序，驱动“华夏会计网”微信小程序完成课程学习和微信认证链路。

## 安全边界

- 仅使用授权测试账号。
- 仅走正常业务路径，不包含绕过、爆破、批量并发或攻击行为。
- 不自动获取或猜测 token；token 由测试人员手动从已授权抓包会话中提供。
- 不修改业务数据，不保存其他用户数据。
- 原始 token、deviceId 只从运行参数读取，不写入日志或 SQLite。

## 安装

```bash
cd integration-harness
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

## 配置

运行所需账户从外部目录加载：

```text
/Users/liuyingying/simon/work/automation/account
```

目录下每个 `.account` 文件代表一个用户，文件名为身份证号，内容为 JSON：

```json
{
  "idCard": "440682198210063620",
  "name": "张三",
  "replay": false,
  "appId": "60101caa0874ec17548b9822",
  "token": "your-token",
  "deviceId": "your-device-id"
}
```

其他可选配置可使用 `.env`：

```bash
cp .env.example .env
```

可选配置包括：

- `HEARTBEAT_INTERVAL_SECONDS`：心跳间隔，默认 60 秒
- `VERIFY_POLL_INTERVAL_SECONDS`：认证结果轮询间隔，默认 5 秒
- `QR_PAGE_PORT`：本地二维码页面端口，默认 8000
- `VIDEO_QUALITY`：视频清晰度，默认 `FD`
- `VIDEO_MAX_RETRIES`：视频下载最大重试次数，默认 5
- `RUN_START_HOUR` / `RUN_END_HOUR`：允许运行时间窗口，默认 5 点到 22 点
- `WECOM_WEBHOOK_URL`：企业微信机器人 Webhook 地址
- `ACCOUNT_DIR`：账户目录，默认 `/Users/liuyingying/simon/work/automation/account`
- `OSS_BUCKET` / `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET` / `OSS_ENDPOINT`：阿里云 OSS 上传配置
- `HXACC_SSL_VERIFY`：是否校验真实后端 TLS 证书；当前环境默认设为 `false`，仅在无法验证本地代理证书时使用

## 运行

默认读取账户目录：

```bash
.venv/bin/python -m integration_harness run
```

也可以显式指定：

```bash
.venv/bin/python -m integration_harness run \
  --account-dir /Users/liuyingying/simon/work/automation/account
```

多个 `.account` 文件会并行执行，默认最多 3 个并发；可通过 `--max-workers` 调整：

```bash
.venv/bin/python -m integration_harness run --max-workers 5
```

每个账户独立运行，互不影响。账户执行失败时仍会推送企业微信，并写入补偿队列：

```text
runs/.compensation_queue.jsonl
```

修复账户文件或外部问题后，可只补偿执行之前失败的账户：

```bash
.venv/bin/python -m integration_harness run --compensate
```

补偿执行同样支持并行：

```bash
.venv/bin/python -m integration_harness run --compensate --max-workers 5
```

也可以以守护模式监控 OSS 目录 `hxacc/account/`：

```bash
.venv/bin/python -m integration_harness watch
```

同时读取本地账户目录下的 `.account` 文件：

```bash
.venv/bin/python -m integration_harness watch \
  --account-dir /Users/liuyingying/simon/work/automation/account
```

扫描逻辑：

- 若 OSS 中存在 `hxacc/account/{idCard}/finished`，推送“已完成”到企业微信。
- 否则读取本地 `{idCard}.account`，如果 `tokenExpiresAt` 已过期，推送“请重新获取 token”到企业微信。
- 如果未过期，则启动对应的课程学习子进程。

扫描间隔通过 `ACCOUNT_WATCH_INTERVAL_SECONDS` 配置，默认 2 秒。子进程日志写入：

```text
runs/watch/{idCard}.out.log
runs/watch/{idCard}.err.log
```

每个账户运行前，会把对应 `.account` 文件上传到：

```text
hxacc/account/{idCard}/{idCard}.account
```

任务播放完成后，会在该目录下新增：

```text
hxacc/account/{idCard}/yyyyMMddHHmmss.success
hxacc/account/{idCard}/finished
```

其中 `finished` 文件为空内容，表示该账户的全部任务已经看完。

认证二维码触发后，会生成并上传：

```text
hxacc/account/{idCard}/{pointCode}.png
hxacc/account/{idCard}/{pointCode}.json
```

`pointCode.json` 包含 `task_id`、`created_at`、`expires_at`、`sha256`。
其中时间使用 `Asia/Shanghai`（`+08:00`），`sha256` 是 PNG 图片字节内容的 SHA-256，用于防止重扫。

认证等待期间会通过 `/api/mycert/getTaskCert` 检查任务完成状态：根据姓名和身份证号查询列表，匹配 `taskId` 后，`extra.synced=1` 视为已完成；`synced=0` 或缺失则继续观看。若任务一直未完成，等待 30 分钟后会推送企业微信提醒，并自动恢复视频学习。

任务主循环也会优先使用 `getTaskCert` 判断是否同步完成。即使本地课程进度 `lp=100`，只要 `synced != 1`，会继续定位 `courseList` 中的课程观看，不会误报“任务已全部看完”。

`replay=true` 时，允许选择已经 `finish` 的小节进行重复播放；默认 `false` 跳过已完结小节。

账户目录没有文件，或 OSS 上传失败时，会推送企业微信并跳过后续学习。

程序会：

1. 获取任务列表，按接口返回顺序逐个处理所有任务。
2. 已完结的任务、课程或小节会自动跳过；一次只启动一个视频。
3. 循环处理每个任务内未完结课程和小节，直到该任务看完为止。
4. 获取课程详情和课程小节。
5. 进入课程并开始学习。
6. 获取广东监管状态并恢复学习。
7. 按真实时间下载 HLS 分片并发送心跳，直到达到 `learned[docId].totalTime`。
8. 当心跳响应出现 `needPoint: true` 和 `qrcodeUrl` 时，暂停课程并打开本地二维码页面。
9. 测试人员用手机微信扫码。
10. 页面自动轮询认证结果，成功后恢复学习并继续完成该小节。

运行过程中会向企业微信推送以下事件：

- 视频下载重试耗尽或运行异常
- 触发“您今天学习时长已经超过8小时，不继续累计时长！”
- 单个课程学习完成
- 当前时间不在允许运行窗口

企业微信推送失败时会写入本地 outbox：

```text
runs/.wecom_outbox.jsonl
```

下一次运行启动时会先尝试补发 outbox 中未发送成功的通知。

## 运行产物

每次运行会创建：

```text
runs/<session_id>/
├── run.log
└── events.sqlite3
```

`events.sqlite3` 记录 API 调用和关键响应字段，`run.log` 记录人类可读日志。

## 二维码页面

默认地址：

```text
http://127.0.0.1:8000/qr
```

如果浏览器没有自动打开，可手动访问该地址。页面会每 3 秒更新显示，并自动轮询认证结果。

## 测试

```bash
pytest
```
