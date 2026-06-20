import os
import pytest
from src import config


def test_constants_present():
    assert config.LOCATION == "서울 강동구 둔촌오륜역 인근"
    assert config.CHILD == "만 4세 여아"
    assert config.HISTORY_PATH == "history.json"
    assert config.RECENT_WEEKS == 10


def test_load_secrets_reads_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat456")
    secrets = config.load_secrets()
    assert secrets["telegram_token"] == "tok123"
    assert secrets["telegram_chat_id"] == "chat456"


def test_load_secrets_missing_raises(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with pytest.raises(KeyError):
        config.load_secrets()
