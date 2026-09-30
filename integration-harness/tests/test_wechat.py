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
    assert json.loads(lines[0]) == {"content": "【integration-harness】hello"}


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


def test_send_task_completed_includes_courses_and_next_target():
    notifier = WeChatNotifier("https://example.invalid", max_retries=1)
    sent = []
    notifier.send_markdown = lambda content: sent.append(content) or True

    assert (
        notifier.send_task_completed(
            app_id="app-1",
            token_prefix="token-prefix",
            device_id="device-1",
            session_id="session-1",
            task_title="公需课",
            completed_courses=["课程A", "课程B"],
            next_target="专业课：课程C",
            id_card="id-1",
            name="张三",
        )
        is True
    )

    content = sent[0]
    assert "任务：公需课" in content
    assert "- 课程A" in content
    assert "- 课程B" in content
    assert "下一门：专业课：课程C" in content
