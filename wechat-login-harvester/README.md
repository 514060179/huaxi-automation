# wechat-login-harvester

用于自动完成“打开微信小程序 → 输入账号密码 → 点击登录”，并通过本地代理抓取登录响应，提取 Token。

## 命令

```bash
python -m wechat_login_harvester login
python -m wechat_login_harvester capture
python -m wechat_login_harvester harvest
python -m wechat_login_harvester reconcile
python -m wechat_login_harvester watch
```

- `login`：执行 UI 登录流程。
- `capture`：启动抓包代理，监听登录请求并提取 Token。
- `harvest`：同时启动抓包代理和 UI 登录。
- `reconcile`：按 `USER_FILE` 对账，删除已标记跳过用户的本地 `.account` 和 OSS 目录。
- `watch`：持续监控 `USER_FILE`，有变更时自动对账，并对新增用户重新采集 token。

## 配置

复制并填写：

```bash
cp .env.example .env
```

关键配置：

- `USER_FILE`：账号密码 JSON 文件
- `ACCOUNT_DIR`：写入 token/账号信息的目标目录
- `CAPTURE_PORT`
- `LOGIN_URL_MARKER`
- `WATCH_INTERVAL_SECONDS`：`watch` 命令的轮询间隔，默认 5 秒
- `LOGIN_LOGOUT_DELAY_SECONDS`：每次登录、登出前等待的秒数，默认 30 秒
- `WECOM_WEBHOOK_URL`：企业微信机器人 Webhook 地址
- `OSS_BUCKET` / `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET` / `OSS_ENDPOINT`：删除 OSS 账号目录所需

`USER_FILE` 示例：

```json
[
  {
    "name": "梁敏仪",
    "id_card": "440682197801283620",
    "skip": false
  },
  {
    "name": "梁映仪",
    "id_card": "440682198210063620",
    "skip": true
  }
]
```

`skip` 为 `true` 的用户不会登录、不会生成 `.account`，并会在 `reconcile`/`watch` 时删除对应的本地与 OSS 文件。

登录成功后会把捕获到的 `appId`、`token`、`deviceId`、`idCard`、`name`、`tokenExpiresAt` 写入：

```text
/Users/liuyingying/simon/work/automation/account/{idCard}.account
```

`tokenExpiresAt` 是 JWT 中 `exp` 的 Unix 时间戳（秒）。

同时，每次成功采集 token 后会向 OSS 上传：

```text
hxacc/account/{idCard}/{idCard}.account
hxacc/account/{idCard}/account.json
```

其中 `{idCard}.account` 是与本地账户目录相同的完整账户文件；`account.json` 是账号索引信息，内容：

```json
{
  "username": "姓名",
  "id_card": "身份证号码"
}
```

OSS 凭证需配置在 `.env` 中（`OSS_BUCKET`、`OSS_ACCESS_KEY_ID`、`OSS_ACCESS_KEY_SECRET`、`OSS_ENDPOINT`）。

上传 OSS 文件时会打印开始/成功/失败日志；失败时同时推送企业微信。登录、登出、抓包代理、OSS 删除等失败操作也会推送企业微信。
