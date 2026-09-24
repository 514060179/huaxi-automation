import pytest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from integration_harness.accounts import Account
from integration_harness.main import (
    _account_slot,
    _account_file_paths,
    _append_compensation,
    _compensation_sources,
    _is_in_run_window,
    _prepare_accounts,
    _remove_compensation,
    _resume_account,
    _single_account_command,
    _watch_accounts,
    build_parser,
)


def test_parser_accepts_account_dir():
    parser = build_parser()
    args = parser.parse_args(["run", "--account-dir", "/tmp/account"])
    assert args.account_dir == "/tmp/account"
    assert args.compensate is False


def test_parser_accepts_compensate_and_workers():
    parser = build_parser()
    args = parser.parse_args(["run", "--compensate", "--max-workers", "4"])
    assert args.compensate is True
    assert args.max_workers == 4


def test_parser_accepts_watch_and_single_account_file():
    parser = build_parser()
    args = parser.parse_args(
        ["watch", "--account-dir", "/tmp/account"]
    )
    assert args.command == "watch"
    assert args.account_dir == "/tmp/account"

    run_args = parser.parse_args(
        ["run", "--account-file", "/tmp/account/id.account"]
    )
    assert run_args.command == "run"
    assert run_args.account_file == "/tmp/account/id.account"


def test_parser_accepts_resume_and_id_card():
    parser = build_parser()
    args = parser.parse_args(["resume", "--id-card", "id-1"])
    assert args.command == "resume"
    assert args.id_card == "id-1"


def test_is_in_run_window_respects_hours():
    assert _is_in_run_window(datetime(2026, 9, 16, 5, 0), 5, 22) is True
    assert _is_in_run_window(datetime(2026, 9, 16, 21, 59), 5, 22) is True
    assert _is_in_run_window(datetime(2026, 9, 16, 22, 0), 5, 22) is False
    assert _is_in_run_window(datetime(2026, 9, 16, 4, 59), 5, 22) is False


def _account(tmp_path: Path, name: str) -> Account:
    source = tmp_path / f"{name}.account"
    return Account(
        id_card=name,
        name=name,
        replay=False,
        app_id="app-1",
        token="token-1",
        device_id="device-1",
        source_path=source,
    )


def test_compensation_queue_deduplicates_and_removes(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path / "runs"))
    account = _account(tmp_path, "id-1")

    _append_compensation(account, "first")
    _append_compensation(account, "second")
    assert _compensation_sources() == [str(account.source_path)]

    _remove_compensation(account)
    assert _compensation_sources() == []


def test_prepare_accounts_builds_parallel_tasks(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("ACCOUNT_DIR", str(tmp_path))
    accounts = [_account(tmp_path, "id-1"), _account(tmp_path, "id-2")]

    prepared, exit_code = _prepare_accounts(accounts)

    assert exit_code == 0
    assert [task.account.id_card for task in prepared] == ["id-1", "id-2"]
    for task in prepared:
        assert task.config.token == "token-1"


def test_account_file_paths_filters_account_files(tmp_path):
    (tmp_path / "a.account").write_text("{}", encoding="utf-8")
    (tmp_path / "b.txt").write_text("{}", encoding="utf-8")
    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "c.account").write_text("{}", encoding="utf-8")

    paths = _account_file_paths(tmp_path)

    assert [Path(path).name for path in sorted(paths)] == ["a.account"]


def test_single_account_command(tmp_path):
    account = tmp_path / "id.account"
    command = _single_account_command(account)

    assert command[-2:] == ["--account-file", str(account)]


def test_resume_account_deletes_stop_marker_and_notifies(monkeypatch):
    class FakeUploader:
        def __init__(self, **kwargs):
            self.deleted = []

        def object_exists(self, key):
            return True

        def delete_object(self, key):
            self.deleted.append(key)
            return SimpleNamespace(key=key, success=True, error=None)

    class FakeNotifier:
        def __init__(self, *args, **kwargs):
            self.sent = []

        def send_markdown(self, content):
            self.sent.append(content)
            return True

        def close(self):
            pass

    uploader = FakeUploader()
    monkeypatch.setattr(
        "integration_harness.main.load_config",
        lambda overrides=None: SimpleNamespace(
            wecom_webhook_url="https://example.com/hook",
            oss_bucket="bucket",
            oss_access_key_id="key",
            oss_access_key_secret="secret",
            oss_endpoint="https://example.com",
        ),
    )
    monkeypatch.setattr(
        "integration_harness.main.OssAccountUploader",
        lambda **kwargs: uploader,
    )
    monkeypatch.setattr(
        "integration_harness.main.WeChatNotifier",
        FakeNotifier,
    )

    result = _resume_account("id-1")

    assert result == 0
    assert uploader.deleted == ["hxacc/account/id-1/stop"]


def test_account_slot_is_stable_and_in_range():
    assert _account_slot("id-1", 16) == _account_slot("id-1", 16)
    assert 0 <= _account_slot("id-1", 16) < 16


class _FakePopen:
    instances = []

    def __init__(self, command, **kwargs):
        self.command = command
        self.kwargs = kwargs
        self.terminated = False
        self.killed = False
        self.waited = False
        _FakePopen.instances.append(self)

    def poll(self):
        return None

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        self.waited = True
        return 0


def test_watch_accounts_starts_and_stops_child(tmp_path, monkeypatch):
    account = tmp_path / "id.account"
    account.write_text(
        '{"appId":"app","token":"token","deviceId":"device","name":"张三","tokenExpiresAt":4102444800}',
        encoding="utf-8",
    )

    class FakeUploader:
        def list_prefixes(self, prefix):
            return ["hxacc/account/id/"]

        def object_exists(self, key):
            return False

        def upload_text(self, key, content=""):
            return SimpleNamespace(key=key, success=True, error=None)

        def delete_object(self, key):
            return SimpleNamespace(key=key, success=True, error=None)

    class FakeNotifier:
        def __init__(self, *args, **kwargs):
            self.sent = []

        def send_markdown(self, content):
            self.sent.append(content)
            return True

        def close(self):
            pass

    monkeypatch.setattr(
        "integration_harness.main._project_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "integration_harness.main.load_config",
        lambda overrides=None: SimpleNamespace(
            wecom_webhook_url="https://example.com/hook",
            runs_dir=tmp_path / "runs",
            oss_bucket="bucket",
            oss_access_key_id="key",
            oss_access_key_secret="secret",
            oss_endpoint="https://example.com",
        ),
    )
    monkeypatch.setattr(
        "integration_harness.main.OssAccountUploader",
        lambda **kwargs: FakeUploader(),
    )
    monkeypatch.setattr(
        "integration_harness.main.WeChatNotifier",
        FakeNotifier,
    )
    monkeypatch.setattr(
        "integration_harness.main._single_account_command",
        lambda path: ["fake-run", str(path)],
    )
    monkeypatch.setattr(
        "integration_harness.main.subprocess.Popen",
        _FakePopen,
    )

    def interrupt_sleep(_):
        raise KeyboardInterrupt

    monkeypatch.setattr("integration_harness.main.time.sleep", interrupt_sleep)
    _FakePopen.instances.clear()

    result = _watch_accounts(tmp_path)

    assert result == 0
    assert len(_FakePopen.instances) == 1
    assert _FakePopen.instances[0].terminated is True
    assert _FakePopen.instances[0].waited is True
