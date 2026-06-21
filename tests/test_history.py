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
