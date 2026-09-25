import json
from datetime import datetime, timedelta, timezone

from wechat_login_harvester.status import build_statuses, summary_reply


class FakeOss:
    def __init__(self, objects: dict[str, str]) -> None:
        self.objects = objects

    def object_exists(self, key: str) -> bool:
        return key in self.objects

    def get_object_text(self, key: str) -> str:
        return self.objects.get(key, "")


def _process_payload(expires_delta_seconds: int, worker: str = "w1") -> str:
    now = datetime.now(timezone.utc)
    return json.dumps(
        {
            "worker_id": worker,
            "started_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=expires_delta_seconds)).isoformat(),
        }
    )


def test_build_statuses_classifies_users():
    oss = FakeOss(
        {
            "hxacc/account/111/finished": "",
            "hxacc/account/222/222.process": _process_payload(120),
            "hxacc/account/333/333.process": _process_payload(-10),
        }
    )
    users = [
        {"name": "完成", "id_card": "111"},
        {"name": "学习中", "id_card": "222"},
        {"name": "未学习", "id_card": "333"},
        {"name": "跳过", "id_card": "444", "skip": True},
    ]

    statuses = build_statuses(users, oss)
    by_id = {item.id_card: item.state for item in statuses}

    assert by_id == {
        "111": "finished",
        "222": "learning",
        "333": "not_learning",
        "444": "skipped",
    }


def test_summary_reply_only_not_learning():
    oss = FakeOss(
        {
            "hxacc/account/222/222.process": _process_payload(120),
            "hxacc/account/333/333.process": _process_payload(-10),
        }
    )
    users = [
        {"name": "学习中", "id_card": "222"},
        {"name": "未学习", "id_card": "333"},
    ]

    reply = summary_reply(users, oss, only_not_learning=True)

    assert "未学习" in reply
    assert "333" in reply
    assert "222" not in reply


def test_summary_reply_requires_oss():
    from wechat_login_harvester.bot import UserStore, handle_text

    store = UserStore(__import__("pathlib").Path("unused"))
    reply = handle_text(store, "未学习", oss=None)
    assert "未配置 OSS" in reply
