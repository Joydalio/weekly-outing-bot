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
