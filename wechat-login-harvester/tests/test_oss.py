import logging

from wechat_login_harvester.oss import OssClient


class FakeBucket:
    def __init__(self) -> None:
        self.calls = []
        self.file_calls = []

    def put_object(self, key, content):
        self.calls.append((key, content))

    def put_object_from_file(self, key, file_path):
        self.file_calls.append((key, file_path))


def test_upload_text_logs_start_and_success(caplog, monkeypatch):
    oss = OssClient(
        access_key_id="a",
        access_key_secret="b",
        bucket_name="bucket",
        endpoint="https://example.com",
    )
    fake_bucket = FakeBucket()
    monkeypatch.setattr(oss, "bucket", fake_bucket)

    with caplog.at_level(logging.INFO, logger="wechat_login_harvester.oss"):
        oss.upload_text("hxacc/account/1/account.json", "{}")

    assert "OSS 上传开始：hxacc/account/1/account.json" in caplog.text
    assert "OSS 上传成功：hxacc/account/1/account.json" in caplog.text


def test_upload_file_logs_start_and_success(caplog, monkeypatch, tmp_path):
    oss = OssClient(
        access_key_id="a",
        access_key_secret="b",
        bucket_name="bucket",
        endpoint="https://example.com",
    )
    fake_bucket = FakeBucket()
    monkeypatch.setattr(oss, "bucket", fake_bucket)
    source = tmp_path / "id.account"
    source.write_text("{}", encoding="utf-8")

    with caplog.at_level(logging.INFO, logger="wechat_login_harvester.oss"):
        oss.upload_file(source, "hxacc/account/id/id.account")

    assert "OSS 上传文件开始" in caplog.text
    assert "OSS 上传文件成功：hxacc/account/id/id.account" in caplog.text
    assert fake_bucket.file_calls == [("hxacc/account/id/id.account", str(source))]
