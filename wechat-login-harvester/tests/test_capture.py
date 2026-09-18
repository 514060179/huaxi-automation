from pathlib import Path

from wechat_login_harvester.capture import (
    LoginCaptureAddon,
    _build_account_manifest,
    _extract_login_data,
    _extract_token,
    _jwt_expiry,
)


def test_extract_token_from_nested_data():
    assert (
        _extract_token({"data": {"token": "token-1"}})
        == "token-1"
    )


def test_extract_token_from_top_level():
    assert _extract_token({"token": "token-2"}) == "token-2"


def test_extract_token_returns_empty_when_missing():
    assert _extract_token({"data": {}}) == ""


def test_extract_login_data_from_external_shape():
    payload = {
        "appId": "app-1",
        "token": "token-1",
        "deviceId": "device-1",
        "idCard": "id-1",
        "name": "张三",
    }

    assert _extract_login_data(payload) == {
        "appId": "app-1",
        "token": "token-1",
        "deviceId": "device-1",
        "idCard": "id-1",
        "name": "张三",
    }


def test_jwt_expiry_returns_exp_claim():
    token = (
        "eyJhbGciOiJIUzI1NiJ9."
        "eyJpc3MiOiJoeGFjYy5jb20iLCJleHAiOjE3OTIxMjE3NDF9."
        "signature"
    )
    assert _jwt_expiry(token) == 1792121741


def test_jwt_expiry_returns_none_for_invalid_token():
    assert _jwt_expiry("not-a-jwt") is None


def test_build_account_manifest():
    assert _build_account_manifest("梁映芬", "440682198412203708") == {
        "username": "梁映芬",
        "id_card": "440682198412203708",
    }


class FakeOss:
    def __init__(self) -> None:
        self.uploaded_files = []
        self.uploaded_texts = []

    def upload_file(self, file_path, key):
        self.uploaded_files.append((file_path, key))

    def upload_text(self, key, content):
        self.uploaded_texts.append((key, content))


def test_write_account_file_uploads_dot_account_and_manifest(tmp_path):
    oss = FakeOss()
    addon = LoginCaptureAddon(
        login_url_marker="/index.php/api/user/wechatLogin",
        token_output_dir=tmp_path / "tokens",
        account_dir=tmp_path / "account",
        oss_client=oss,
    )

    addon._write_account_file(
        {
            "appId": "app-1",
            "token": "token-1",
            "deviceId": "device-1",
            "idCard": "id-1",
            "name": "张三",
        }
    )

    account_path = tmp_path / "account" / "id-1.account"
    assert account_path.exists()
    assert oss.uploaded_files == [
        (Path(account_path), "hxacc/account/id-1/id-1.account")
    ]
    assert oss.uploaded_texts[0][0] == "hxacc/account/id-1/account.json"
