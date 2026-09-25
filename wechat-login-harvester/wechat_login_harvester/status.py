from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


class OssReader(Protocol):
    def object_exists(self, key: str) -> bool: ...

    def get_object_text(self, key: str) -> str: ...


@dataclass(frozen=True)
class LearningStatus:
    name: str
    id_card: str
    state: str
    detail: str = ""


def _prefix(id_card: str) -> str:
    return f"hxacc/account/{id_card}/"


def _process_state(oss: OssReader, id_card: str) -> tuple[str, str]:
    key = f"{_prefix(id_card)}{id_card}.process"
    if not oss.object_exists(key):
        return "not_learning", "无运行标记"
    try:
        payload = json.loads(oss.get_object_text(key))
        expires_at = payload.get("expires_at", "")
        expires = datetime.fromisoformat(expires_at)
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        remaining = expires - datetime.now(timezone.utc)
        if remaining.total_seconds() > 0:
            worker = payload.get("worker_id", "?")
            minutes = max(int(remaining.total_seconds() // 60), 0)
            return "learning", f"worker={worker} 剩余约{minutes}分钟"
        return "not_learning", "运行标记已过期"
    except Exception:
        return "not_learning", "运行标记无效"


def build_statuses(
    users: list[dict],
    oss: OssReader,
) -> list[LearningStatus]:
    statuses: list[LearningStatus] = []
    for user in users:
        name = str(user.get("name", ""))
        id_card = str(user.get("id_card", ""))
        skip = bool(user.get("skip", False))
        if skip:
            statuses.append(
                LearningStatus(name=name, id_card=id_card, state="skipped", detail="已跳过")
            )
            continue
        prefix = _prefix(id_card)
        if oss.object_exists(f"{prefix}finished"):
            statuses.append(
                LearningStatus(name=name, id_card=id_card, state="finished", detail="已完成")
            )
            continue
        state, detail = _process_state(oss, id_card)
        statuses.append(
            LearningStatus(name=name, id_card=id_card, state=state, detail=detail)
        )
    return statuses


def render_statuses(
    statuses: list[LearningStatus],
    *,
    only_not_learning: bool = False,
) -> str:
    state_labels = {
        "learning": "学习中",
        "not_learning": "未在学习",
        "finished": "已完成",
        "skipped": "已跳过",
    }
    lines: list[str] = []
    for item in statuses:
        if only_not_learning and item.state != "not_learning":
            continue
        label = state_labels.get(item.state, item.state)
        line = f"{item.name}  {item.id_card}  [{label}]"
        if item.detail:
            line += f"  {item.detail}"
        lines.append(line)
    if not lines:
        return "（无）"
    return "\n".join(lines)


def summary_reply(
    users: list[dict],
    oss: OssReader,
    *,
    only_not_learning: bool = False,
) -> str:
    statuses = build_statuses(users, oss)
    body = render_statuses(statuses, only_not_learning=only_not_learning)
    counts: dict[str, int] = {}
    for item in statuses:
        counts[item.state] = counts.get(item.state, 0) + 1
    learning = counts.get("learning", 0)
    finished = counts.get("finished", 0)
    not_learning = counts.get("not_learning", 0)
    skipped = counts.get("skipped", 0)
    if only_not_learning:
        header = f"未在学习用户（共 {not_learning} 个）："
    else:
        header = (
            f"学习状态：学习中 {learning}，未在学习 {not_learning}，"
            f"已完成 {finished}，已跳过 {skipped}"
        )
    return header + "\n" + body
