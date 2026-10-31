from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from news_digest.articles import Article
from news_digest.config import ROOT_DIR

_LOCK = threading.Lock()
DEFAULT_STATE_PATH = ROOT_DIR / "data" / "processed_articles.json"


@dataclass
class ProcessedState:
    items: dict[str, str]

    @classmethod
    def empty(cls) -> ProcessedState:
        return cls(items={})


def state_path() -> Path:
    return DEFAULT_STATE_PATH


def load_state(path: Path | None = None) -> ProcessedState:
    target = path or state_path()
    if not target.exists():
        return ProcessedState.empty()
    with _LOCK:
        raw = json.loads(target.read_text(encoding="utf-8"))
    items = raw.get("items", raw) if isinstance(raw, dict) else {}
    cleaned = {str(k): str(v) for k, v in items.items()}
    return ProcessedState(items=cleaned)


def save_state(state: ProcessedState, path: Path | None = None) -> None:
    target = path or state_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"items": state.items}
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with _LOCK:
        tmp = target.with_suffix(".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(target)


def prune_state(state: ProcessedState, *, retain_days: int = 30) -> ProcessedState:
    cutoff = datetime.now(UTC) - timedelta(days=retain_days)
    kept: dict[str, str] = {}
    for key, stamp in state.items.items():
        try:
            when = datetime.fromisoformat(stamp)
        except ValueError:
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        if when >= cutoff:
            kept[key] = stamp
    return ProcessedState(items=kept)


def filter_unsent(articles: list[Article], state: ProcessedState) -> list[Article]:
    return [article for article in articles if article.url not in state.items]


def mark_sent(state: ProcessedState, articles: list[Article]) -> ProcessedState:
    stamp = datetime.now(UTC).isoformat()
    items = dict(state.items)
    for article in articles:
        items[article.url] = stamp
    return ProcessedState(items=items)
