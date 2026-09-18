先用 wechat-login-harvester 抓取 token，生成本地 .account 并上传 OSS；再用 integration-harness 读取 .account 跑课程学习和微信认证。

  ## 一、采集 token：wechat-login-harvester

  目录：

  cd /Users/liuyingying/simon/work/automation/wechat-login-harvester

  首次初始化：

  python3 -m venv .venv
  source .venv/bin/activate
  pip install -e ".[test]"

  配置：

  cp .env.example .env

  重点检查 .env：

  USER_FILE=/Users/liuyingying/simon/work/automation/wechat-login-harvester/user
  ACCOUNT_DIR=/Users/liuyingying/simon/work/automation/account
  CAPTURE_PORT=8888
  LOGIN_LOGOUT_DELAY_SECONDS=30
  WECOM_WEBHOOK_URL=你的企业微信机器人地址
  OSS_BUCKET=hxacc-auto
  OSS_ACCESS_KEY_ID=你的AK
  OSS_ACCESS_KEY_SECRET=你的SK
  OSS_ENDPOINT=https://oss-cn-shenzhen.aliyuncs.com

  用户文件 user 示例：

  [
    {"name": "梁敏仪", "id_card": "身份证号"},
    {"name": "梁映仪", "id_card": "身份证号", "skip": true}
  ]

  推荐启动命令：

  cd /Users/liuyingying/simon/work/automation/wechat-login-harvester
  source .venv/bin/activate
  python -m wechat_login_harvester harvest

  也可以不激活环境：

  .venv/bin/python -m wechat_login_harvester harvest

  其他命令：

  python -m wechat_login_harvester login       # 只跑 UI 登录，不抓包
  python -m wechat_login_harvester capture     # 只启动抓包代理，手动在微信登录
  python -m wechat_login_harvester harvest     # 推荐：抓包 + UI 登录
  python -m wechat_login_harvester reconcile   # 清理 skip 用户
  python -m wechat_login_harvester watch       # 持续监控 user 文件变化

  采集成功后会生成：

  /Users/liuyingying/simon/work/automation/account/{idCard}.account
  runs/tokens/*.json
  runs/<session>/mitmdump.out.log

  同时上传 OSS：

  hxacc/account/{idCard}/{idCard}.account
  hxacc/account/{idCard}/account.json

  ———

  ## 二、跑课程学习：integration-harness

  前提：上面已经生成至少一个 .account 文件。

  目录：

  cd /Users/liuyingying/simon/work/automation/integration-harness

  首次初始化：

  python3 -m venv .venv
  source .venv/bin/activate
  pip install -e ".[test]"

  配置：

  cp .env.example .env

  启动：

  cd /Users/liuyingying/simon/work/automation/integration-harness
  source .venv/bin/activate
  python -m integration_harness run

  或直接：

  .venv/bin/python -m integration_harness run

  显式指定账户目录：

  .venv/bin/python -m integration_harness run \
    --account-dir /Users/liuyingying/simon/work/automation/account

  如果运行中触发认证二维码，浏览器访问：

  http://127.0.0.1:8000/qr

  运行日志和事件：

  runs/<session_id>/run.log
  runs/<session_id>/events.sqlite3

  ———

  ## 三、测试命令

  cd /Users/liuyingying/simon/work/automation/wechat-login-harvester
  .venv/bin/pytest

  cd /Users/liuyingying/simon/work/automation/integration-harness
  .venv/bin/pytest

  ———

  ## 推荐的日常启动顺序

  # 1. 采集 token
  cd /Users/liuyingying/simon/work/automation/wechat-login-harvester
  .venv/bin/python -m wechat_login_harvester harvest

  # 2. 确认 .account 已生成
  ls -lt /Users/liuyingying/simon/work/automation/account

  # 3. 跑课程学习
  cd /Users/liuyingying/simon/work/automation/integration-harness
  .venv/bin/python -m integration_harness run