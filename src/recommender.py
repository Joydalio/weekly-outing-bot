import json
from dataclasses import dataclass

MODEL = "claude-opus-4-8"

FIELDS = [
    "place_name", "intro", "reason", "weather_note",
    "map_query", "travel_note", "prep",
]


@dataclass
class Recommendation:
    place_name: str
    intro: str
    reason: str
    weather_note: str
    map_query: str
    travel_note: str
    prep: str


def build_prompt(*, location: str, child: str, today: str, avoid: list[str]) -> str:
    avoid_text = ", ".join(avoid) if avoid else "없음"
    return (
        "당신은 부모를 돕는 나들이 추천 도우미입니다.\n"
        f"대상 아동: {child}\n"
        f"거주지: {location}\n"
        f"오늘 날짜: {today}\n"
        f"최근 추천했던 장소(중복 회피): {avoid_text}\n\n"
        f"먼저 웹 검색으로 이번 주 {location} 인근의 실제 날씨와 가볼 만한 장소·행사를 "
        "조사하세요. 검색을 모두 마친 뒤, 이번 주말에 아이와 함께 갈 만한 나들이 장소 "
        "한 곳을 추천하세요. 최근 추천 장소는 피하고, 아이 발달 단계에 맞는 곳을 고르세요. "
        "intro·reason은 한국어로 자연스럽게, travel_note는 둔촌오륜역 기준 대중교통 "
        "소요시간으로 작성하세요.\n\n"
        "검색이 끝난 마지막 메시지에서만, 아래 키를 가진 JSON 객체 하나를 출력하세요: "
        f"{', '.join(FIELDS)}."
    )


def _extract_json(text: str) -> dict:
    # ponytail: 모델이 JSON을 산문·코드펜스로 감싸므로 가장 바깥 객체만 떼어낸다
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"응답에서 JSON을 찾지 못함: {text[:200]}")
    return json.loads(text[start:end + 1])


def generate_recommendation(client, *, location: str, child: str,
                            today: str, avoid: list[str]) -> Recommendation:
    prompt = build_prompt(location=location, child=child, today=today, avoid=avoid)
    messages = [{"role": "user", "content": prompt}]
    for _ in range(5):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            messages=messages,
        )
        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continue
        break
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"추천 생성 미완료: stop_reason={response.stop_reason}")
    texts = [b.text for b in response.content if b.type == "text"]
    if not texts:
        raise RuntimeError("응답에 텍스트 블록이 없음")
    data = _extract_json(texts[-1])  # 마지막 블록 = 검색을 끝낸 최종 답
    return Recommendation(**{k: data[k] for k in FIELDS})
