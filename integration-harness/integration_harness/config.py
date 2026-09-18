from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    token: str
    device_id: str
    www_base_url: str
    learn_base_url: str
    video_base_url: str
    video_quality: str
    app_id: str
    wecom_webhook_url: str
    account_dir: Path
    oss_bucket: str
    oss_access_key_id: str
    oss_access_key_secret: str
    oss_endpoint: str
    run_start_hour: int
    run_end_hour: int
    video_max_retries: int
    heartbeat_interval_seconds: int
    verify_poll_interval_seconds: int
    qr_page_port: int
    runs_dir: Path
    ssl_verify: bool

    @property
    def token_prefix(self) -> str:
        if not self.token:
            return "<empty>"
        return self.token[:12]


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


def load_config(overrides: dict[str, str] | None = None) -> Config:
    _load_dotenv(Path(".env"))
    values = dict(os.environ)
    if overrides:
        values.update(overrides)

    token = values.get("HXACC_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "HXACC_TOKEN is required. Copy it into integration-harness/.env "
            "or export it in your shell."
        )

    device_id = values.get("HXACC_DEVICE_ID", "").strip()
    if not device_id:
        raise RuntimeError(
            "HXACC_DEVICE_ID is required. Copy it into integration-harness/.env "
            "or export it in your shell."
        )

    runs_dir = Path(values.get("RUNS_DIR", "runs"))
    if not runs_dir.is_absolute():
        runs_dir = Path.cwd() / runs_dir

    account_dir = Path(
        values.get(
            "ACCOUNT_DIR",
            "/Users/liuyingying/simon/work/automation/account",
        )
    ).expanduser()
    if not account_dir.is_absolute():
        account_dir = Path.cwd() / account_dir

    return Config(
        token=token,
        device_id=device_id,
        www_base_url=values.get("WWW_BASE_URL", "https://www.hxacc.com").rstrip("/"),
        learn_base_url=values.get("LEARN_BASE_URL", "https://learn.hxacc.com").rstrip("/"),
        video_base_url=values.get("VIDEO_BASE_URL", "https://v1.hxacc.com").rstrip("/"),
        video_quality=values.get("VIDEO_QUALITY", "FD").strip().upper(),
        app_id=values.get("APP_ID", "60101caa0874ec17548b9822"),
        wecom_webhook_url=values.get(
            "WECOM_WEBHOOK_URL",
            "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=de2d8b32-ca95-4117-b349-816feb0347d2",
        ).strip(),
        account_dir=account_dir,
        oss_bucket=values.get("OSS_BUCKET", "hxacc-auto").strip(),
        oss_access_key_id=values.get(
            "OSS_ACCESS_KEY_ID",
            "LTAI5t7nheec8XfbRDEPm9a9",
        ).strip(),
        oss_access_key_secret=values.get(
            "OSS_ACCESS_KEY_SECRET",
            "dR1pJmBJXpOUt62ECTLk9ourszjQ42",
        ).strip(),
        oss_endpoint=values.get(
            "OSS_ENDPOINT",
            "https://oss-cn-shenzhen.aliyuncs.com",
        ).strip(),
        run_start_hour=int(values.get("RUN_START_HOUR", "5")),
        run_end_hour=int(values.get("RUN_END_HOUR", "22")),
        video_max_retries=int(values.get("VIDEO_MAX_RETRIES", "5")),
        heartbeat_interval_seconds=int(values.get("HEARTBEAT_INTERVAL_SECONDS", "60")),
        verify_poll_interval_seconds=int(values.get("VERIFY_POLL_INTERVAL_SECONDS", "5")),
        qr_page_port=int(values.get("QR_PAGE_PORT", "8000")),
        runs_dir=runs_dir,
        ssl_verify=values.get("HXACC_SSL_VERIFY", "false").strip().lower()
        not in {"0", "false", "no", "off"},
    )
