import pytest
from datetime import datetime
from pathlib import Path

from integration_harness.accounts import Account
from integration_harness.main import (
    _append_compensation,
    _compensation_sources,
    _is_in_run_window,
    _prepare_accounts,
    _remove_compensation,
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
