from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from news_digest.articles import build_article
from news_digest.filters import dedupe_articles, filter_and_tag, within_lookback
from news_digest.models import AppConfig, DigestSettings, ProxySettings, Source, Topic
from news_digest.state import filter_unsent, load_state, mark_sent, prune_state, save_state


def _config() -> AppConfig:
    return AppConfig(
        digest=DigestSettings(lookback_hours=24, max_candidates=30),
        proxy=ProxySettings(),
        topics=[
            Topic(id="ai", name="AI", keywords=["openai", "llm"]),
            Topic(id="industry", name="Industry", keywords=["startup"]),
        ],
        sources=[
            Source(
                id="s1",
                name="S1",
                type="rss",
                url="https://example.com/feed",
                topics=["ai"],
            )
        ],
    )


def test_within_lookback_and_keywords() -> None:
    now = datetime(2026, 10, 30, 12, tzinfo=UTC)
    fresh = build_article(
        title="OpenAI ships LLM",
        url="https://example.com/a",
        source="S1",
        published_at=now - timedelta(hours=2),
        content="OpenAI model",
        extra={"source_id": "s1"},
    )
    old = build_article(
        title="OpenAI old",
        url="https://example.com/old",
        source="S1",
        published_at=now - timedelta(hours=48),
        content="OpenAI",
        extra={"source_id": "s1"},
    )
    assert fresh and old
    assert within_lookback(fresh, lookback_hours=24, now=now)
    assert not within_lookback(old, lookback_hours=24, now=now)
    result = filter_and_tag([fresh, old], _config(), now=now)
    assert len(result) == 1
    assert result[0].topic == "ai"


def test_dedupe_by_url_and_title() -> None:
    a = build_article(title="Same Title!", url="https://ex.com/1", source="s")
    b = build_article(title="same title", url="https://ex.com/2", source="s")
    c = build_article(title="Same Title!", url="https://ex.com/1?utm_source=x", source="s")
    assert a and b and c
    # c normalizes to same url as a
    assert c.url == a.url
    assert len(dedupe_articles([a, b, c])) == 1


def test_state_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "processed.json"
    article = build_article(title="Hello", url="https://ex.com/x", source="s")
    assert article
    state = mark_sent(load_state(path), [article])
    save_state(state, path)
    loaded = load_state(path)
    assert filter_unsent([article], loaded) == []
    pruned = prune_state(loaded, retain_days=30)
    assert article.url in pruned.items
