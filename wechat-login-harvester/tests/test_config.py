import json

from wechat_login_harvester.config import load_config


def test_load_config_accepts_user_array(tmp_path, monkeypatch):
    user_file = tmp_path / "user"
    user_file.write_text(
        json.dumps(
                [
                    {"name": "张三", "id_card": "id-1"},
                    {"name": "李四", "id_card": "id-2"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("USER_FILE", str(user_file))
    monkeypatch.setenv("TOKEN_OUTPUT_DIR", str(tmp_path / "tokens"))

    config = load_config()

    assert [(user.name, user.id_card) for user in config.users] == [
        ("张三", "id-1"),
        ("李四", "id-2"),
    ]


def test_load_config_reads_skip_flag(tmp_path, monkeypatch):
    user_file = tmp_path / "user"
    user_file.write_text(
        json.dumps(
            [
                {"name": "张三", "id_card": "id-1", "skip": True},
                {"name": "李四", "id_card": "id-2"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("USER_FILE", str(user_file))
    monkeypatch.setenv("TOKEN_OUTPUT_DIR", str(tmp_path / "tokens"))

    config = load_config()

    assert [(user.name, user.skip) for user in config.users] == [
        ("张三", True),
        ("李四", False),
    ]


def test_load_config_reads_delay_and_wecom(tmp_path, monkeypatch):
    user_file = tmp_path / "user"
    user_file.write_text(
        json.dumps([{"name": "张三", "id_card": "id-1"}]),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("USER_FILE", str(user_file))
    monkeypatch.setenv("TOKEN_OUTPUT_DIR", str(tmp_path / "tokens"))
    monkeypatch.setenv("LOGIN_LOGOUT_DELAY_SECONDS", "45")
    monkeypatch.setenv("WECOM_WEBHOOK_URL", "https://example.com/hook")

    config = load_config()

    assert config.login_logout_delay_seconds == 45
    assert config.wecom_webhook_url == "https://example.com/hook"
