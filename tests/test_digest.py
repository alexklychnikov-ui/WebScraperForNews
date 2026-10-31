from __future__ import annotations

from datetime import UTC, datetime

from news_digest.articles import build_article
from news_digest.digest import render_digest
from news_digest.models import AppConfig, DigestSettings, ProxySettings, Source, Topic


def test_render_digest_groups_and_escapes() -> None:
    config = AppConfig(
        digest=DigestSettings(language="ru", lookback_hours=24, timezone="Asia/Shanghai"),
        proxy=ProxySettings(),
        topics=[Topic(id="ai", name="ИИ", keywords=["ai"])],
        sources=[Source(id="s", name="S", type="rss", url="https://ex.com", topics=["ai"])],
    )
    article = build_article(
        title='Alert <script>alert(1)</script>',
        url="https://ex.com/a",
        source="S",
        summary="Краткое русское summary",
        topic="ai",
        published_at=datetime(2026, 10, 29, 19, 56, tzinfo=UTC),
    )
    assert article
    rendered = render_digest(
        [article],
        config,
        generated_at=datetime(2026, 10, 30, 3, 0, tzinfo=UTC),
    )
    assert "Новостной дайджест — 30.10.2026" in rendered.html
    assert "30.10.2026 03:56" in rendered.html  # Asia/Shanghai = UTC+8
    assert "ИИ" in rendered.html
    assert "&lt;script&gt;" in rendered.html
    assert "<script>alert(1)</script>" not in rendered.html
    assert "Краткое русское summary" in rendered.text
    assert "https://ex.com/a" in rendered.text
    assert "News Digest" not in rendered.html
    assert "%Y-%m-%d" not in rendered.html
    assert "2026-10-30" not in rendered.title
