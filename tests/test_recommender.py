import json
from types import SimpleNamespace
from unittest.mock import MagicMock
from src import recommender


def _text_block(text):
    return SimpleNamespace(type="text", text=text)


def _make_client(response):
    client = MagicMock()
    client.messages.create.return_value = response
    return client


def test_build_prompt_includes_context():
    prompt = recommender.build_prompt(
        location="강동구", child="만 4세 여아", today="2026-06-24", avoid=["서울숲", "한강"]
    )
    assert "강동구" in prompt
    assert "만 4세 여아" in prompt
    assert "2026-06-24" in prompt
    assert "서울숲" in prompt and "한강" in prompt


def test_build_prompt_handles_empty_avoid():
    prompt = recommender.build_prompt(
        location="강동구", child="만 4세 여아", today="2026-06-24", avoid=[]
    )
    assert "없음" in prompt


def test_generate_recommendation_parses_json():
    payload = {
        "place_name": "어린이대공원",
        "intro": "동물원과 놀이터가 있어요.",
        "reason": "만 4세 오감 자극에 좋아요.",
        "weather_note": "주말 맑음.",
        "map_query": "서울 어린이대공원",
        "travel_note": "둔촌오륜역에서 약 30분",
        "prep": "간식·물",
    }
    response = SimpleNamespace(
        stop_reason="end_turn", content=[_text_block(json.dumps(payload, ensure_ascii=False))]
    )
    client = _make_client(response)
    rec = recommender.generate_recommendation(
        client, location="강동구", child="만 4세 여아", today="2026-06-24", avoid=[]
    )
    assert isinstance(rec, recommender.Recommendation)
    assert rec.place_name == "어린이대공원"
    assert rec.map_query == "서울 어린이대공원"


def test_generate_recommendation_resumes_on_pause_turn():
    payload = {
        "place_name": "한강공원",
        "intro": "자전거와 잔디밭.",
        "reason": "야외 활동.",
        "weather_note": "맑음.",
        "map_query": "광나루한강공원",
        "travel_note": "약 20분",
        "prep": "돗자리",
    }
    paused = SimpleNamespace(stop_reason="pause_turn", content=[])
    done = SimpleNamespace(
        stop_reason="end_turn", content=[_text_block(json.dumps(payload, ensure_ascii=False))]
    )
    client = MagicMock()
    client.messages.create.side_effect = [paused, done]
    rec = recommender.generate_recommendation(
        client, location="강동구", child="만 4세 여아", today="2026-06-24", avoid=[]
    )
    assert rec.place_name == "한강공원"
    assert client.messages.create.call_count == 2
    second_messages = client.messages.create.call_args_list[1].kwargs["messages"]
    assert second_messages[-1]["role"] == "assistant"
    assert second_messages[-1]["content"] == []


def test_generate_recommendation_uses_web_search_tool():
    payload = {
        "place_name": "X", "intro": "x", "reason": "x", "weather_note": "x",
        "map_query": "x", "travel_note": "x", "prep": "x",
    }
    response = SimpleNamespace(
        stop_reason="end_turn", content=[_text_block(json.dumps(payload))]
    )
    client = _make_client(response)
    recommender.generate_recommendation(
        client, location="강동구", child="만 4세 여아", today="2026-06-24", avoid=[]
    )
    _, kwargs = client.messages.create.call_args
    assert kwargs["model"] == "claude-opus-4-8"
    tool_types = [t["type"] for t in kwargs["tools"]]
    assert "web_search_20260209" in tool_types
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    assert kwargs["output_config"]["format"]["schema"] is recommender.RECOMMENDATION_SCHEMA
