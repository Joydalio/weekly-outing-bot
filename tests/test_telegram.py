from dataclasses import dataclass
from unittest.mock import MagicMock, patch
from src import telegram


@dataclass
class StubRec:
    place_name: str = "서울숲 공원"
    intro: str = "사슴 먹이주기 체험이 있어요."
    reason: str = "초여름 야외 활동에 좋아요."
    weather_note: str = "수·목 맑음(26도)."
    map_query: str = "서울숲 공원"
    travel_note: str = "둔촌오륜역에서 약 35분"
    prep: str = "여벌 옷·간식"


def test_build_map_link_encodes_query():
    link = telegram.build_map_link("서울숲 공원")
    assert link.startswith("https://map.naver.com/v5/search/")
    assert " " not in link  # 공백이 인코딩됨


def test_format_message_has_at_most_three_emojis():
    msg = telegram.format_message(StubRec(), "6/24")
    emoji_count = sum(msg.count(e) for e in ["📍", "🗺️", "🌤️"])
    assert emoji_count <= 3
    assert "📍" in msg and "🗺️" in msg


def test_format_message_includes_fields_and_link():
    msg = telegram.format_message(StubRec(), "6/24")
    assert "서울숲 공원" in msg
    assert "6/24" in msg
    assert "지도 보기" in msg
    assert "https://map.naver.com/v5/search/" in msg
    assert "둔촌오륜역에서 약 35분" in msg


def test_format_message_escapes_html():
    rec = StubRec(intro="<b>주의</b> & 안전")
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
