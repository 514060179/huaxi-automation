from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Account:
    id_card: str
    name: str
    replay: bool
    app_id: str
    token: str
    device_id: str
    source_path: Path


class AccountLoadError(RuntimeError):
    pass


def discover_account_files(account_dir: Path) -> list[Path]:
    if not account_dir.exists():
        raise AccountLoadError(f"账户目录不存在：{account_dir}")
    if not account_dir.is_dir():
        raise AccountLoadError(f"账户路径不是目录：{account_dir}")

    files = sorted(account_dir.glob("*.account"))
    if not files:
        raise AccountLoadError(f"账户目录中没有 .account 文件：{account_dir}")
    return files


def load_account_file(path: Path) -> Account:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AccountLoadError(f"账户文件不是合法 JSON：{path}") from exc
    if not isinstance(payload, dict):
        raise AccountLoadError(f"账户文件顶层必须是 JSON 对象：{path}")

    app_id = payload.get("appId") or payload.get("app_id")
    token = payload.get("token")
    device_id = payload.get("deviceId") or payload.get("device_id")
    name = payload.get("name")
    replay = bool(payload.get("replay", False))
    id_card = payload.get("idCard") or path.stem
    if not app_id or not token or not device_id or not name:
        raise AccountLoadError(
            f"账户文件缺少 appId/app_id、token、deviceId/device_id、name：{path}"
        )

    return Account(
        id_card=str(id_card),
        name=str(name),
        replay=replay,
        app_id=str(app_id),
        token=str(token),
        device_id=str(device_id),
        source_path=path,
    )


def load_accounts(account_dir: Path) -> list[Account]:
    return [load_account_file(path) for path in discover_account_files(account_dir)]
