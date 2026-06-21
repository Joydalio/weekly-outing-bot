import html

import requests


def format_message(rec, date_label: str) -> str:
    e = html.escape
    lines = [f"<b>이번 주 나들이 · {e(date_label)}</b>"]
    for i, p in enumerate(rec.places, 1):
        lines.append(f"{i}. {e(p.name)} — {e(p.note)} / 대중교통 {e(p.transit)}·차 {e(p.car)}")
    lines.append(f"날씨: {e(rec.weather)}")
    lines.append(f"준비물: {e(rec.prep)}")
    return "\n".join(lines)


def send_message(token: str, chat_id: str, text: str) -> dict:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
