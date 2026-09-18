import json

from integration_harness.wechat import WeChatNotifier


def test_failed_send_writes_outbox(tmp_path):
    outbox_path = tmp_path / "wecom_outbox.jsonl"
    notifier = WeChatNotifier(
        "https://example.invalid",
        max_retries=1,
        outbox_path=outbox_path,
    )
    notifier._post_with_retries = lambda content: False

    assert notifier.send_markdown("hello") is False

    lines = outbox_path.read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0]) == {"content": "hello"}


def test_flush_outbox_removes_delivered_messages(tmp_path):
    outbox_path = tmp_path / "wecom_outbox.jsonl"
    outbox_path.write_text(
        json.dumps({"content": "hello"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    notifier = WeChatNotifier(
        "https://example.invalid",
        max_retries=1,
        outbox_path=outbox_path,
    )
    notifier._post_with_retries = lambda content: True

    assert notifier.flush_outbox() == 1
    assert not outbox_path.exists()
