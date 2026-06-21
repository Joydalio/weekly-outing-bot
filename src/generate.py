import argparse
import datetime

import anthropic

from src import config, history, recommender, telegram


def today_kst() -> datetime.date:
    kst = datetime.timezone(datetime.timedelta(hours=9))
    return datetime.datetime.now(kst).date()


def _generate_with_retry(client, today, avoid, attempts: int = 2):
    for i in range(attempts):
        try:
            return recommender.generate_recommendation(
                client,
                location=config.LOCATION,
                child=config.CHILD,
                today=today.isoformat(),
                avoid=avoid,
            )
        except Exception:
            if i == attempts - 1:
                return None
    return None


def run(dry_run: bool = False) -> None:
    today = today_kst()
    date_label = f"{today.month}/{today.day}"
    avoid = config.EXCLUDE + history.load_recent(config.HISTORY_PATH, config.RECENT_WEEKS)

    client = anthropic.Anthropic()
    rec = _generate_with_retry(client, today, avoid)

    if rec is None:
        message = "이번 주 추천 생성에 실패했어요. 다음 주에 다시 시도할게요."
    else:
        message = telegram.format_message(rec, date_label)

    if dry_run:
        print(message)
        return

    secrets = config.load_secrets()
    telegram.send_message(secrets["telegram_token"], secrets["telegram_chat_id"], message)

    if rec is not None:
        history.append_entry(config.HISTORY_PATH, today.isoformat(), rec.place_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
