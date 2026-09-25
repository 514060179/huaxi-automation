import pytest

from integration_harness.client import ApiError, HxaccClient
from integration_harness.config import load_config


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text
        self.content = b""


def test_get_video_bytes_preserves_401_status(monkeypatch):
    config = load_config(
        {
            "HXACC_TOKEN": "secret-token",
            "HXACC_DEVICE_ID": "device-id",
        }
    )
    client = HxaccClient(config)
    monkeypatch.setattr(
        client.client,
        "get",
        lambda url, headers=None: _FakeResponse(401, "unauthorized"),
    )

    with pytest.raises(ApiError) as exc_info:
        client.get_video_bytes("https://example.com/video.ts", retries=1)

    assert exc_info.value.status_code == 401
    client.close()
