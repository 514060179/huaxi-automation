from integration_harness.oss_upload import OssAccountUploader


def test_upload_file_success(tmp_path, monkeypatch):
    class FakeBucket:
        def __init__(self):
            self.key = None
            self.file_path = None

        def put_object_from_file(self, key, file_path):
            self.key = key
            self.file_path = file_path

    uploader = OssAccountUploader(
        access_key_id="key",
        access_key_secret="secret",
        bucket_name="bucket",
        endpoint="https://example.invalid",
    )
    fake_bucket = FakeBucket()
    monkeypatch.setattr(uploader, "bucket", fake_bucket)

    source = tmp_path / "id.account"
    source.write_text("{}", encoding="utf-8")
    result = uploader.upload_file(source, "hxacc/account/id")

    assert result.success is True
    assert fake_bucket.key == "hxacc/account/id"
    assert fake_bucket.file_path == str(source)


def test_upload_file_returns_failure(monkeypatch):
    class FakeBucket:
        def put_object_from_file(self, key, file_path):
            raise RuntimeError("boom")

    uploader = OssAccountUploader(
        access_key_id="key",
        access_key_secret="secret",
        bucket_name="bucket",
        endpoint="https://example.invalid",
    )
    monkeypatch.setattr(uploader, "bucket", FakeBucket())

    result = uploader.upload_file(__file__, "hxacc/account/id")

    assert result.success is False
    assert "boom" in result.error


def test_upload_text_success(monkeypatch):
    class FakeBucket:
        def put_object(self, key, content):
            self.key = key
            self.content = content

    uploader = OssAccountUploader(
        access_key_id="key",
        access_key_secret="secret",
        bucket_name="bucket",
        endpoint="https://example.invalid",
    )
    fake_bucket = FakeBucket()
    monkeypatch.setattr(uploader, "bucket", fake_bucket)

    result = uploader.upload_text("hxacc/account/id/20260917000000.success")

    assert result.success is True
    assert fake_bucket.key == "hxacc/account/id/20260917000000.success"
    assert fake_bucket.content == b""


def test_upload_bytes_success(monkeypatch):
    class FakeBucket:
        def put_object(self, key, content):
            self.key = key
            self.content = content

    uploader = OssAccountUploader(
        access_key_id="key",
        access_key_secret="secret",
        bucket_name="bucket",
        endpoint="https://example.invalid",
    )
    fake_bucket = FakeBucket()
    monkeypatch.setattr(uploader, "bucket", fake_bucket)

    result = uploader.upload_bytes("hxacc/account/id/pointCode.png", b"png")

    assert result.success is True
    assert fake_bucket.content == b"png"
