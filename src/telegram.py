import html
import urllib.parse

import requests


def build_map_link(map_query: str) -> str:
    return "https://map.naver.com/v5/search/" + urllib.parse.quote(map_query)


def format_message(rec, date_label: str) -> str:
    e = html.escape
    link = build_map_link(rec.map_query)
    return (
        f"<b>이번 주 나들이 추천 · {e(date_label)}</b>\n\n"
        f"📍 <b>{e(rec.place_name)}</b>\n"
        f"{e(rec.intro)}\n\n"
        f"왜 좋은가 — {e(rec.reason)}\n\n"
        f"날씨 — {e(rec.weather_note)}\n\n"
        f'🗺️ <a href="{e(link)}">지도 보기</a> · {e(rec.travel_note)}\n\n'
        f"준비물 — {e(rec.prep)}"
    )


def send_message(token: str, chat_id: str, text: str) -> dict:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
