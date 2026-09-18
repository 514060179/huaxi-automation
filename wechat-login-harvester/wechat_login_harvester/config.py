from __future__ import annotations

import os
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UserCredential:
    name: str
    id_card: str
    skip: bool = False


@dataclass(frozen=True)
class Config:
    users: tuple[UserCredential, ...]
    user_file: Path
    account_dir: Path
    capture_port: int
    login_url_marker: str
    token_output_dir: Path
    learn_base_url: str
    oss_bucket: str
    oss_access_key_id: str
    oss_access_key_secret: str
    oss_endpoint: str
    watch_interval_seconds: float
    wecom_webhook_url: str = ""
    login_logout_delay_seconds: float = 30.0


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


def load_config() -> Config:
    _load_dotenv(Path(".env"))
    user_file = Path(
        os.getenv(
            "USER_FILE",
            "/Users/liuyingying/simon/work/automation/wechat-login-harvester/user",
        )
    ).expanduser()
    if not user_file.is_absolute():
        user_file = Path.cwd() / user_file

    if not user_file.exists():
        raise RuntimeError(
            f"用户文件不存在：{user_file}"
        )

    try:
        user_payload = json.loads(user_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"用户文件不是合法 JSON：{user_file}") from exc
    if isinstance(user_payload, list):
        user_items = user_payload
    elif isinstance(user_payload, dict):
        user_items = [user_payload]
    else:
        raise RuntimeError(f"用户文件顶层必须是 JSON 对象或数组：{user_file}")

    users: list[UserCredential] = []
    for item in user_items:
        if not isinstance(item, dict):
            raise RuntimeError("用户数组中的每一项必须是 JSON 对象")
        name = str(item.get("name", "")).strip()
        id_card = str(item.get("id_card", "")).strip()
        if not name or not id_card:
            raise RuntimeError("用户数组中存在缺少 name/id_card 的用户")
        skip_raw = item.get("skip", False)
        if isinstance(skip_raw, bool):
            skip = skip_raw
        else:
            skip = str(skip_raw).strip().lower() in {
                "true",
                "1",
                "yes",
                "on",
            }
        users.append(
            UserCredential(name=name, id_card=id_card, skip=skip)
        )
    if not users:
        raise RuntimeError("用户文件为空")

    account_dir = Path(
        os.getenv(
            "ACCOUNT_DIR",
            "/Users/liuyingying/simon/work/automation/account",
        )
    ).expanduser()
    if not account_dir.is_absolute():
        account_dir = Path.cwd() / account_dir

    output_dir = Path(os.getenv("TOKEN_OUTPUT_DIR", "runs/tokens"))
    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir

    return Config(
        users=tuple(users),
        user_file=user_file,
        account_dir=account_dir,
        capture_port=int(os.getenv("CAPTURE_PORT", "8888")),
        login_url_marker=os.getenv(
            "LOGIN_URL_MARKER",
            "/index.php/api/user/wechatLogin",
        ),
        token_output_dir=output_dir,
        learn_base_url=os.getenv(
            "LEARN_BASE_URL",
            "https://learn.hxacc.com",
        ).rstrip("/"),
        oss_bucket=os.getenv("OSS_BUCKET", "hxacc-auto").strip(),
        oss_access_key_id=os.getenv("OSS_ACCESS_KEY_ID", "").strip(),
        oss_access_key_secret=os.getenv("OSS_ACCESS_KEY_SECRET", "").strip(),
        oss_endpoint=os.getenv(
            "OSS_ENDPOINT",
            "https://oss-cn-shenzhen.aliyuncs.com",
        ).strip(),
        watch_interval_seconds=float(
            os.getenv("WATCH_INTERVAL_SECONDS", "5")
        ),
        wecom_webhook_url=os.getenv(
            "WECOM_WEBHOOK_URL",
            "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=de2d8b32-ca95-4117-b349-816feb0347d2",
        ).strip(),
        login_logout_delay_seconds=float(
            os.getenv("LOGIN_LOGOUT_DELAY_SECONDS", "30")
        ),
    )
