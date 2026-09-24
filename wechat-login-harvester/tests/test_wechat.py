import json

import httpx

from wechat_login_harvester.wechat import WeChatNotifier


def test_send_failure_writes_outbox_on_http_error(tmp_path, monkeypatch):
    notifier = WeChatNotifier(
        "https://example.com/hook",
        max_retries=1,
        outbox_path=tmp_path / "outbox.jsonl",
    )

    def fail_post(*args, **kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(notifier.client, "post", fail_post)

    ok = notifier.send_failure(
        "测试失败",
        details={"原因": "boom"},
    )

    assert not ok
    lines = notifier.outbox_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["content"].startswith("【wechat-login-harvester】⚠️ 测试失败")
