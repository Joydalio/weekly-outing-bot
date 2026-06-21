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


def _payload():
    return {
        "places": [
            {"name": "길동생태공원", "note": "곤충·습지 관찰", "transit": "20분", "car": "10분"},
            {"name": "서울숲", "note": "사슴 먹이주기", "transit": "35분", "car": "25분"},
            {"name": "어린이대공원", "note": "동물원", "transit": "40분", "car": "30분"},
        ],
        "weather": "주말 흐림, 우산 챙기기.",
        "prep": "간식·물·여벌옷.",
    }


def test_build_prompt_includes_context():
    prompt = recommender.build_prompt(
        location="강동구", child="만 4세 여아", today="2026-06-24", avoid=["서울숲", "한강"]
    )
    assert "강동구" in prompt
    assert "만 4세 여아" in prompt
    assert "2026-06-24" in prompt
    assert "서울숲" in prompt and "한강" in prompt
    assert "3곳" in prompt   # 대안 3가지
    assert "200자" in prompt  # 전체 200자 이내


def test_build_prompt_handles_empty_avoid():
    prompt = recommender.build_prompt(
        location="강동구", child="만 4세 여아", today="2026-06-24", avoid=[]
    )
    assert "없음" in prompt


def test_generate_recommendation_parses_three_places():
    response = SimpleNamespace(
        stop_reason="end_turn",
        content=[_text_block(json.dumps(_payload(), ensure_ascii=False))],
    )
    rec = recommender.generate_recommendation(
        _make_client(response), location="강동구", child="만 4세 여아",
        today="2026-06-24", avoid=[],
    )
    assert isinstance(rec, recommender.Recommendation)
    assert len(rec.places) == 3
    assert rec.places[0].name == "길동생태공원"
    assert rec.places[0].transit == "20분" and rec.places[0].car == "10분"
    assert rec.weather == "주말 흐림, 우산 챙기기."
    assert rec.prep == "간식·물·여벌옷."


def test_generate_recommendation_resumes_on_pause_turn():
    paused = SimpleNamespace(stop_reason="pause_turn", content=[])
    done = SimpleNamespace(
        stop_reason="end_turn",
        content=[_text_block(json.dumps(_payload(), ensure_ascii=False))],
    )
    client = MagicMock()
    client.messages.create.side_effect = [paused, done]
    rec = recommender.generate_recommendation(
        client, location="강동구", child="만 4세 여아", today="2026-06-24", avoid=[]
    )
    assert rec.places[0].name == "길동생태공원"
    assert client.messages.create.call_count == 2
    second_messages = client.messages.create.call_args_list[1].kwargs["messages"]
    assert second_messages[-1]["role"] == "assistant"
    assert second_messages[-1]["content"] == []


def test_generate_recommendation_uses_web_search_without_output_config():
    response = SimpleNamespace(
        stop_reason="end_turn", content=[_text_block(json.dumps(_payload()))]
    )
    client = _make_client(response)
    recommender.generate_recommendation(
        client, location="강동구", child="만 4세 여아", today="2026-06-24", avoid=[]
    )
    _, kwargs = client.messages.create.call_args
    assert kwargs["model"] == "claude-opus-4-8"
    assert "web_search_20260209" in [t["type"] for t in kwargs["tools"]]
    # output_config(구조화 출력)는 웹검색 루프를 망가뜨리므로 보내지 않는다
    assert "output_config" not in kwargs


def test_generate_recommendation_uses_last_text_block_and_strips_prose():
    # 라이브 버그 재현: 검색 전 placeholder 블록 + 산문/코드펜스로 감싼 최종 JSON 블록
    early = _text_block("둔촌오륜역 인근을 검색하겠습니다.")
    final = _text_block("추천드려요:\n```json\n" + json.dumps(_payload(), ensure_ascii=False) + "\n```")
    client = _make_client(SimpleNamespace(stop_reason="end_turn", content=[early, final]))
    rec = recommender.generate_recommendation(
        client, location="강동구", child="만 4세 여아", today="2026-06-24", avoid=[]
    )
    assert len(rec.places) == 3
    assert rec.places[1].name == "서울숲"
