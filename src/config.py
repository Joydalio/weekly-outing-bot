import os

LOCATION = "서울 강동구 둔촌오륜역 인근"
CHILD = "만 4세 여아"
HISTORY_PATH = "history.json"
RECENT_WEEKS = 10


def load_secrets() -> dict:
    return {
        "telegram_token": os.environ["TELEGRAM_BOT_TOKEN"],
        "telegram_chat_id": os.environ["TELEGRAM_CHAT_ID"],
    }
