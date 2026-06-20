# 주간 나들이 추천 봇 (weekly-outing-bot) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매주 수요일 오전 8시(KST), AI가 강동구 둔촌오륜역 인근 만 4세 여아용 나들이 장소를 생성해 텔레그램으로 푸시 알림을 보내고, 추천 기록을 깃에 저장한다.

**Architecture:** Python 스크립트를 GitHub Actions 주간 크론으로 실행한다. `recommender`가 Claude API(웹 검색 서버 도구)로 추천을 생성하고, `telegram`이 포맷·전송하며, `history`가 최근 10주 회피 목록과 기록을 관리하고, `generate`가 전체를 조율한다. 각 모듈은 독립적으로 테스트 가능하다.

**Tech Stack:** Python 3.11, `anthropic` SDK (모델 `claude-opus-4-8`, `web_search_20260209` 서버 도구, `output_config.format` 구조화 출력), `requests`(텔레그램 Bot API), 표준 `json`. 테스트는 `pytest`(Claude·텔레그램은 목 처리).

## Global Constraints

- 모델 ID는 정확히 `claude-opus-4-8` (날짜 접미사 없음).
- 추천 메시지의 이모지는 최대 3개, 핵심 위치(장소 `📍`, 지도 `🗺️`)에만 사용.
- 거주지: `서울 강동구 둔촌오륜역 인근`. 대상 아동: `만 4세 여아`.
- 발송 시각: 수요일 08:00 KST = 크론 `0 23 * * 2` (UTC, 화요일 23:00).
- 중복 회피: 최근 10주 추천 장소.
- 지도 링크: `https://map.naver.com/v5/search/<URL 인코딩된 검색어>`.
- 시크릿은 환경변수로만 주입: `ANTHROPIC_API_KEY`(SDK가 암묵적으로 읽음), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. 키를 코드에 하드코딩하지 않는다.
- 모든 파일 경로는 저장소 루트 기준. 패키지는 `src/`.

## File Structure

| 파일 | 책임 |
|------|------|
| `requirements.txt` | 런타임·테스트 의존성 |
| `src/__init__.py` | 패키지 마커 (빈 파일) |
| `src/config.py` | 상수(지역·아이·경로·회피 주수) 및 시크릿 로딩 |
| `src/history.py` | `history.json` 읽기/쓰기, 최근 N주 장소 목록 |
| `src/recommender.py` | Claude API 호출 → `Recommendation` 반환 (웹 검색 포함) |
| `src/telegram.py` | 지도 링크 생성, 메시지 포맷(HTML), 봇 전송 |
| `src/generate.py` | 진입점·조율: 로드 → 생성(재시도) → 전송 → 기록 |
| `history.json` | 추천 기록 저장 (초기값 `[]`) |
| `tests/test_config.py` | config 단위 테스트 |
| `tests/test_history.py` | history 단위 테스트 |
| `tests/test_telegram.py` | 지도 링크·포맷·전송 단위 테스트 |
| `tests/test_recommender.py` | recommender 단위 테스트(목 클라이언트) |
| `tests/test_generate.py` | 조율 로직 단위 테스트(전부 목) |
| `.github/workflows/weekly.yml` | 주간 크론 + 수동 실행 워크플로 |
| `.gitignore` | `__pycache__`, `.venv`, `*.pyc` 제외 |
| `README.md` | 보호자용 설치·시크릿 등록 안내서 |

### 공유 타입 (Task 4에서 정의, 이후 참조)

```python
@dataclass
class Recommendation:
    place_name: str    # 장소 이름
    intro: str         # 한 줄 소개
    reason: str        # 추천 이유 / 발달 포인트
    weather_note: str  # 이번 주 날씨 메모
    map_query: str     # 네이버 지도 검색어
    travel_note: str   # 둔촌오륜역 기준 이동 정보
    prep: str          # 준비물
```

`history.json` 엔트리 형식: `{"date": "2026-06-24", "place_name": "서울숲 공원"}`.

---

### Task 1: 프로젝트 스캐폴드 + config

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `history.json`
- Create: `.gitignore`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `config.LOCATION: str`, `config.CHILD: str`, `config.HISTORY_PATH: str`, `config.RECENT_WEEKS: int`
  - `config.load_secrets() -> dict` — 키 `"telegram_token"`, `"telegram_chat_id"`; 누락 시 `KeyError`

- [ ] **Step 1: 의존성 파일 작성**

`requirements.txt`:

```
anthropic>=0.50
requests>=2.31
pytest>=8.0
```

- [ ] **Step 2: 패키지 마커와 초기 데이터 파일 생성**

`src/__init__.py` — 빈 파일(내용 없음).

`history.json`:

```json
[]
```

`.gitignore`:

```
__pycache__/
*.pyc
.venv/
```

- [ ] **Step 3: 실패하는 테스트 작성**

`tests/test_config.py`:

```python
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
```

- [ ] **Step 4: 테스트 실패 확인**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.config'` (또는 `AttributeError`)

- [ ] **Step 5: config 구현**

`src/config.py`:

```python
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
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (3 passed)

- [ ] **Step 7: 커밋**

```bash
git add requirements.txt src/__init__.py src/config.py history.json .gitignore tests/test_config.py
git commit -m "feat: 프로젝트 스캐폴드와 config 모듈"
```

---

### Task 2: history 모듈

**Files:**
- Create: `src/history.py`
- Test: `tests/test_history.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `history.load_recent(path: str, n: int = 10) -> list[str]` — 최근 n개 엔트리의 `place_name` 목록(오래된→최신 순). 파일 없으면 `[]`.
  - `history.append_entry(path: str, date: str, place_name: str) -> None` — `{"date", "place_name"}` 추가 후 UTF-8 + indent=2로 저장.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_history.py`:

```python
import json
from src import history


def test_load_recent_missing_file_returns_empty(tmp_path):
    assert history.load_recent(str(tmp_path / "none.json")) == []


def test_load_recent_returns_last_n_place_names(tmp_path):
    p = tmp_path / "h.json"
    entries = [{"date": f"2026-01-{i:02d}", "place_name": f"장소{i}"} for i in range(1, 6)]
    p.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    assert history.load_recent(str(p), n=3) == ["장소3", "장소4", "장소5"]


def test_append_entry_creates_and_appends(tmp_path):
    p = tmp_path / "h.json"
    p.write_text("[]", encoding="utf-8")
    history.append_entry(str(p), "2026-06-24", "서울숲 공원")
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data == [{"date": "2026-06-24", "place_name": "서울숲 공원"}]


def test_append_entry_preserves_korean(tmp_path):
    p = tmp_path / "h.json"
    p.write_text("[]", encoding="utf-8")
    history.append_entry(str(p), "2026-06-24", "한강공원")
    raw = p.read_text(encoding="utf-8")
    assert "한강공원" in raw  # ensure_ascii=False 확인
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_history.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.history'`

- [ ] **Step 3: history 구현**

`src/history.py`:

```python
import json
from pathlib import Path


def load_recent(path: str, n: int = 10) -> list[str]:
    p = Path(path)
    if not p.exists():
        return []
    entries = json.loads(p.read_text(encoding="utf-8"))
    return [e["place_name"] for e in entries[-n:]]


def append_entry(path: str, date: str, place_name: str) -> None:
    p = Path(path)
    entries = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    entries.append({"date": date, "place_name": place_name})
    p.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_history.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/history.py tests/test_history.py
git commit -m "feat: history 읽기/쓰기 모듈"
```

---

### Task 3: telegram 모듈 (지도 링크 + 포맷 + 전송)

**Files:**
- Create: `src/telegram.py`
- Test: `tests/test_telegram.py`

**Interfaces:**
- Consumes: `Recommendation` 형태의 객체(속성 `place_name, intro, reason, weather_note, map_query, travel_note, prep`). Task 4 이전이므로 테스트에서는 동일 속성을 가진 간단한 stub 객체를 쓴다.
- Produces:
  - `telegram.build_map_link(map_query: str) -> str`
  - `telegram.format_message(rec, date_label: str) -> str` — HTML 문자열, 이모지 `📍`·`🗺️`만
  - `telegram.send_message(token: str, chat_id: str, text: str) -> dict` — Bot API `sendMessage` POST, `parse_mode="HTML"`, 실패 시 `raise_for_status()`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_telegram.py`:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_telegram.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.telegram'`

- [ ] **Step 3: telegram 구현**

`src/telegram.py`:

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_telegram.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/telegram.py tests/test_telegram.py
git commit -m "feat: 텔레그램 포맷·전송 모듈"
```

---

### Task 4: recommender 모듈 (Claude API + 웹 검색)

**Files:**
- Create: `src/recommender.py`
- Test: `tests/test_recommender.py`

**Interfaces:**
- Consumes: 없음 (anthropic 클라이언트는 인자로 주입받음 → 테스트에서 목 가능)
- Produces:
  - `recommender.Recommendation` 데이터클래스 (위 "공유 타입" 참조)
  - `recommender.RECOMMENDATION_SCHEMA: dict` — JSON schema
  - `recommender.build_prompt(*, location: str, child: str, today: str, avoid: list[str]) -> str`
  - `recommender.generate_recommendation(client, *, location: str, child: str, today: str, avoid: list[str]) -> Recommendation`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_recommender.py`:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_recommender.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.recommender'`

- [ ] **Step 3: recommender 구현**

`src/recommender.py`:

```python
import json
from dataclasses import dataclass

MODEL = "claude-opus-4-8"

RECOMMENDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "place_name": {"type": "string"},
        "intro": {"type": "string"},
        "reason": {"type": "string"},
        "weather_note": {"type": "string"},
        "map_query": {"type": "string"},
        "travel_note": {"type": "string"},
        "prep": {"type": "string"},
    },
    "required": [
        "place_name", "intro", "reason", "weather_note",
        "map_query", "travel_note", "prep",
    ],
    "additionalProperties": False,
}


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
        f"웹 검색으로 이번 주 {location} 인근의 실제 날씨와 가볼 만한 장소·행사를 "
        "조사한 뒤, 이번 주말에 아이와 함께 갈 만한 나들이 장소 한 곳을 추천하세요. "
        "최근 추천 장소는 피하고, 아이 발달 단계에 맞는 곳을 고르세요. "
        "intro·reason은 한국어로 자연스럽게, travel_note는 둔촌오륜역 기준 대중교통 "
        "소요시간으로 작성하세요."
    )


def generate_recommendation(client, *, location: str, child: str,
                            today: str, avoid: list[str]) -> Recommendation:
    prompt = build_prompt(location=location, child=child, today=today, avoid=avoid)
    messages = [{"role": "user", "content": prompt}]
    response = None
    for _ in range(5):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            output_config={
                "format": {"type": "json_schema", "schema": RECOMMENDATION_SCHEMA}
            },
            messages=messages,
        )
        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continue
        break
    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)
    return Recommendation(**data)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_recommender.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/recommender.py tests/test_recommender.py
git commit -m "feat: Claude 웹검색 기반 추천 생성 모듈"
```

---

### Task 5: generate 조율 모듈

**Files:**
- Create: `src/generate.py`
- Test: `tests/test_generate.py`

**Interfaces:**
- Consumes: `config`, `history`, `recommender`, `telegram` (전부 위 태스크에서 정의됨)
- Produces:
  - `generate.today_kst() -> datetime.date`
  - `generate.run(dry_run: bool = False) -> None`
  - `__main__` 블록: `--dry-run` 플래그 파싱 후 `run()` 호출

동작 규약:
1. `today_kst()`로 오늘 날짜, `date_label`은 `"{month}/{day}"`.
2. `history.load_recent`로 회피 목록 로드.
3. `recommender.generate_recommendation`을 최대 2회 시도(예외 시 재시도). 모두 실패하면 `rec=None`.
4. `rec`가 있으면 `telegram.format_message`, 없으면 실패 안내 메시지.
5. `dry_run`이면 메시지를 `print`만 하고 종료(전송·기록 없음).
6. 아니면 `telegram.send_message`로 전송. `rec`가 있을 때만 `history.append_entry`.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_generate.py`:

```python
import datetime
from unittest.mock import MagicMock, patch
from src import generate, recommender


def _rec():
    return recommender.Recommendation(
        place_name="서울숲 공원", intro="i", reason="r", weather_note="w",
        map_query="서울숲 공원", travel_note="t", prep="p",
    )


def test_today_kst_returns_date():
    assert isinstance(generate.today_kst(), datetime.date)


def test_run_dry_run_prints_and_does_not_send(capsys):
    with patch("src.generate.history.load_recent", return_value=[]), \
         patch("src.generate.recommender.generate_recommendation", return_value=_rec()), \
         patch("src.generate.anthropic.Anthropic"), \
         patch("src.generate.telegram.send_message") as mock_send, \
         patch("src.generate.history.append_entry") as mock_append:
        generate.run(dry_run=True)
    out = capsys.readouterr().out
    assert "서울숲 공원" in out
    mock_send.assert_not_called()
    mock_append.assert_not_called()


def test_run_sends_and_records_on_success():
    with patch("src.generate.history.load_recent", return_value=["과거장소"]), \
         patch("src.generate.recommender.generate_recommendation", return_value=_rec()), \
         patch("src.generate.anthropic.Anthropic"), \
         patch("src.generate.config.load_secrets",
               return_value={"telegram_token": "tok", "telegram_chat_id": "chat"}), \
         patch("src.generate.telegram.send_message") as mock_send, \
         patch("src.generate.history.append_entry") as mock_append:
        generate.run(dry_run=False)
    mock_send.assert_called_once()
    assert mock_send.call_args[0][0] == "tok"
    mock_append.assert_called_once()
    assert mock_append.call_args[0][2] == "서울숲 공원"


def test_run_sends_failure_message_after_retries():
    with patch("src.generate.history.load_recent", return_value=[]), \
         patch("src.generate.recommender.generate_recommendation",
               side_effect=RuntimeError("boom")) as mock_gen, \
         patch("src.generate.anthropic.Anthropic"), \
         patch("src.generate.config.load_secrets",
               return_value={"telegram_token": "tok", "telegram_chat_id": "chat"}), \
         patch("src.generate.telegram.send_message") as mock_send, \
         patch("src.generate.history.append_entry") as mock_append:
        generate.run(dry_run=False)
    assert mock_gen.call_count == 2  # 1회 재시도
    sent_text = mock_send.call_args[0][2]
    assert "실패" in sent_text
    mock_append.assert_not_called()  # 실패 시 기록 안 함
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_generate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.generate'`

- [ ] **Step 3: generate 구현**

`src/generate.py`:

```python
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
    avoid = history.load_recent(config.HISTORY_PATH, config.RECENT_WEEKS)

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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_generate.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 전체 테스트 통과 확인**

Run: `python -m pytest -v`
Expected: PASS (모든 테스트 통과, 21개)

- [ ] **Step 6: 커밋**

```bash
git add src/generate.py tests/test_generate.py
git commit -m "feat: generate 조율 모듈과 진입점"
```

---

### Task 6: GitHub Actions 워크플로 + 설치 안내서

**Files:**
- Create: `.github/workflows/weekly.yml`
- Create: `README.md`

**Interfaces:**
- Consumes: `python -m src.generate` 진입점, 시크릿 3개
- Produces: 주간 크론 자동 실행 + 수동 실행 트리거; 보호자용 설치 문서

이 태스크는 단위 테스트 대상이 아니다(외부 인프라). 검증은 Step 3의 로컬 dry-run과 설정 후 GitHub의 수동 실행(`workflow_dispatch`)으로 한다.

- [ ] **Step 1: 워크플로 작성**

`.github/workflows/weekly.yml`:

```yaml
name: weekly-outing

on:
  schedule:
    - cron: "0 23 * * 2"   # 화 23:00 UTC = 수 08:00 KST
  workflow_dispatch:        # GitHub에서 수동 실행 버튼

jobs:
  send:
    runs-on: ubuntu-latest
    permissions:
      contents: write       # history.json 커밋용
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - name: Generate and send
        run: python -m src.generate
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
      - name: Commit history
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add history.json
          git diff --staged --quiet || git commit -m "chore: 주간 추천 기록 업데이트"
          git push
```

- [ ] **Step 2: 설치 안내서 작성**

`README.md`:

````markdown
# 주간 나들이 추천 봇

매주 수요일 오전 8시(KST), 만 4세 여아와 함께 갈 강동구 둔촌오륜역 인근
나들이 장소를 AI가 추천해 텔레그램으로 보내줍니다.

## 한 번만 하면 되는 설치

### 1. 텔레그램 봇 만들기
1. 텔레그램에서 `@BotFather` 검색 → `/newbot` → 안내대로 이름 입력
2. 받은 **봇 토큰**(예: `123456:ABC-...`)을 복사해 둡니다.

### 2. 내 chat_id 얻기
1. 방금 만든 봇과의 대화창에서 아무 메시지나 보냅니다.
2. 브라우저에서 `https://api.telegram.org/bot<봇토큰>/getUpdates` 접속
3. 응답에서 `"chat":{"id": 숫자}`의 **숫자**가 chat_id 입니다.

### 3. Anthropic API 키
[console.anthropic.com](https://console.anthropic.com) → API Keys에서 발급.

### 4. GitHub 저장소 + 시크릿
1. 이 코드를 GitHub 저장소에 올립니다.
2. 저장소 **Settings → Secrets and variables → Actions → New repository secret**에서
   다음 3개를 등록:
   - `ANTHROPIC_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

### 5. 동작 확인
저장소 **Actions** 탭 → `weekly-outing` → **Run workflow**로 즉시 테스트 발송.
이후 매주 수요일 오전 8시에 자동으로 도착합니다.

## 로컬에서 미리보기 (전송 없이)
```bash
pip install -r requirements.txt
ANTHROPIC_API_KEY=... python -m src.generate --dry-run
```
````

- [ ] **Step 3: 로컬 dry-run 안내 확인**

`README.md`의 dry-run 명령이 `src/generate.py`의 `--dry-run` 플래그와 일치하는지, 워크플로의 `python -m src.generate`가 실제 진입점과 일치하는지 눈으로 확인한다. (실제 dry-run 실행은 유효한 `ANTHROPIC_API_KEY`가 있을 때만 가능 — 키가 있으면 한 번 실행해 메시지 출력이 정상인지 확인하면 좋다.)

- [ ] **Step 4: 커밋**

```bash
git add .github/workflows/weekly.yml README.md
git commit -m "feat: 주간 크론 워크플로와 설치 안내서"
```

---

## Self-Review

**1. Spec coverage** (스펙 섹션 → 태스크 매핑):
- 목적/지역/아이/주간 AI 생성 → Task 4 (recommender), Task 5 (generate)
- 전체 구조(Python + GH Actions) → Task 6
- 구성 요소 generate/recommender/telegram/history/config → Task 5/4/3/2/1
- 데이터 흐름(로드→생성→포맷→전송→기록) → Task 5 `run()`
- 추천 JSON 스키마 → Task 4 `RECOMMENDATION_SCHEMA`/`Recommendation`
- 메시지 형식(이모지 ≤3, 📍·🗺️) → Task 3 `format_message` + 테스트
- 에러 처리(1회 재시도 + 실패 안내 메시지) → Task 5 `_generate_with_retry` + 실패 메시지 테스트
- 테스트(dry-run, 수동 실행, 단위 테스트) → 각 태스크 테스트 + Task 5/6
- 발송 시각 크론 → Task 6 `0 23 * * 2`
- 사전 준비물 4단계 안내 → Task 6 README
- 범위 밖(피드백/타 카테고리/다중) → 어떤 태스크에도 포함하지 않음 ✓

빠진 항목 없음.

**2. Placeholder scan:** "TBD"/"적절히 처리" 등 없음. 모든 코드 단계에 실제 코드 포함. ✓

**3. Type consistency:** `Recommendation` 7개 필드(`place_name, intro, reason, weather_note, map_query, travel_note, prep`)가 스키마·데이터클래스·`format_message`·테스트 stub·`history.append_entry`(place_name) 전반에서 일치. `generate_recommendation`/`load_recent`/`append_entry`/`send_message`/`format_message` 시그니처가 호출부와 일치. 모델 ID `claude-opus-4-8` 일관. ✓
