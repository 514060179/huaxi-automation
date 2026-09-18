import os
from pathlib import Path

import pytest

from integration_harness.config import Config, load_config


def test_load_config_requires_token(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("HXACC_TOKEN", raising=False)
    monkeypatch.setenv("HXACC_DEVICE_ID", "device-id")
    with pytest.raises(RuntimeError, match="HXACC_TOKEN is required"):
        load_config()


def test_load_config_requires_device_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HXACC_TOKEN", "secret-token")
    monkeypatch.delenv("HXACC_DEVICE_ID", raising=False)
    with pytest.raises(RuntimeError, match="HXACC_DEVICE_ID is required"):
        load_config()


def test_load_config_reads_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "HXACC_TOKEN=secret-token\n"
        "HXACC_DEVICE_ID=device-id\n",
        encoding="utf-8",
    )
    config = load_config()
    assert config.token == "secret-token"
    assert config.token_prefix == "secret-token"
    assert config.device_id == "device-id"
    assert config.video_quality == "FD"


def test_config_runs_dir_is_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HXACC_TOKEN", "secret-token")
    monkeypatch.setenv("HXACC_DEVICE_ID", "device-id")
    monkeypatch.setenv("RUNS_DIR", "runs")
    config = load_config()
    assert config.runs_dir == tmp_path / "runs"


def test_load_config_cli_overrides_env_values(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HXACC_TOKEN", "env-token")
    monkeypatch.setenv("HXACC_DEVICE_ID", "env-device")
    monkeypatch.setenv("APP_ID", "env-app")

    config = load_config(
        {
            "HXACC_TOKEN": "cli-token",
            "HXACC_DEVICE_ID": "cli-device",
            "APP_ID": "cli-app",
        }
    )

    assert config.token == "cli-token"
    assert config.device_id == "cli-device"
    assert config.app_id == "cli-app"
