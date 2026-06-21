from dataclasses import dataclass
from unittest.mock import MagicMock, patch
from src import telegram


@dataclass
class StubPlace:
    name: str
    note: str
    transit: str
    car: str


@dataclass
class StubRec:
    places: list
    weather: str = "주말 흐림, 우산 챙기기."
    prep: str = "간식·물·여벌옷."


def _rec():
    return StubRec(places=[
        StubPlace("길동생태공원", "곤충 관찰", "20분", "10분"),
        StubPlace("서울숲", "사슴 먹이주기", "35분", "25분"),
        StubPlace("어린이대공원", "동물원", "40분", "30분"),
    ])


def test_format_message_lists_three_places_with_times():
    msg = telegram.format_message(_rec(), "6/24")
    assert "1. 길동생태공원" in msg
    assert "2. 서울숲" in msg
    assert "3. 어린이대공원" in msg
    assert "대중교통 20분·차 10분" in msg


def test_format_message_has_weather_and_prep_lines_and_no_link():
    msg = telegram.format_message(_rec(), "6/24")
    assert "날씨: 주말 흐림" in msg
    assert "준비물: 간식·물" in msg
    assert "map.naver.com" not in msg  # 지도 링크 제거됨


def test_format_message_escapes_html():
    rec = StubRec(places=[StubPlace("<b>곳</b> & 터", "n", "1분", "2분")])
    msg = telegram.format_message(rec, "6/24")
    assert "&lt;b&gt;" in msg
    assert "&amp;" in msg


def test_send_message_posts_with_html_parse_mode():
    with patch("src.telegram.requests.post") as mock_post:
        mock_post.return_value = MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={"ok": True})
        )
        result = telegram.send_message("tok", "chat", "hello")
    args, kwargs = mock_post.call_args
    assert "bottok/sendMessage" in args[0]
    assert kwargs["json"]["chat_id"] == "chat"
    assert kwargs["json"]["parse_mode"] == "HTML"
    assert result == {"ok": True}
