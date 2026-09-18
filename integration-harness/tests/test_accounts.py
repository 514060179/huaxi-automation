import json

import pytest

from integration_harness.accounts import (
    AccountLoadError,
    discover_account_files,
    load_account_file,
)


def test_load_account_file_reads_filename_as_id_card(tmp_path):
    path = tmp_path / "440682199309042146.account"
    path.write_text(
        json.dumps(
            {
                "idCard": "440682199309042146",
                "name": "张三",
                "replay": True,
                "appId": "app-1",
                "token": "token-1",
                "deviceId": "device-1",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    account = load_account_file(path)

    assert account.id_card == "440682199309042146"
    assert account.name == "张三"
    assert account.replay is True
    assert account.app_id == "app-1"
    assert account.token == "token-1"
    assert account.device_id == "device-1"


def test_load_account_file_rejects_missing_fields(tmp_path):
    path = tmp_path / "id.account"
    path.write_text(
        '{"appId":"app","token":"token","deviceId":"device"}',
        encoding="utf-8",
    )

    with pytest.raises(AccountLoadError, match="缺少"):
        load_account_file(path)


def test_discover_account_files_sorts_and_filters(tmp_path):
    (tmp_path / "b.account").write_text("{}", encoding="utf-8")
    (tmp_path / "a.account").write_text("{}", encoding="utf-8")
    (tmp_path / "ignore.txt").write_text("{}", encoding="utf-8")

    files = discover_account_files(tmp_path)

    assert [path.name for path in files] == ["a.account", "b.account"]
