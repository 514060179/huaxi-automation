from pathlib import Path

from wechat_login_harvester.config import Config, UserCredential
from wechat_login_harvester.reconcile import reconcile


def _make_config(tmp_path: Path, users: list[UserCredential]) -> Config:
    return Config(
        users=tuple(users),
        user_file=tmp_path / "user",
        account_dir=tmp_path / "account",
        capture_port=8888,
        login_url_marker="/index.php/api/user/wechatLogin",
        token_output_dir=tmp_path / "tokens",
        learn_base_url="https://learn.hxacc.com",
        oss_bucket="",
        oss_access_key_id="",
        oss_access_key_secret="",
        oss_endpoint="https://oss-cn-shenzhen.aliyuncs.com",
        watch_interval_seconds=5,
    )


def test_reconcile_deletes_skipped_accounts(tmp_path):
    account_dir = tmp_path / "account"
    account_dir.mkdir()
    skipped = account_dir / "id-skip.account"
    skipped.write_text("{}", encoding="utf-8")
    kept = account_dir / "id-keep.account"
    kept.write_text("{}", encoding="utf-8")

    config = _make_config(
        tmp_path,
        [
            UserCredential(name="跳过", id_card="id-skip", skip=True),
            UserCredential(name="保留", id_card="id-keep"),
            UserCredential(name="新增", id_card="id-new"),
        ],
    )

    result = reconcile(config)

    assert not skipped.exists()
    assert kept.exists()
    assert [u.id_card for u in result.to_harvest] == ["id-new"]
    assert result.deleted_local == ["id-skip"]
