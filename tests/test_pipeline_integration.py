from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from news_digest.articles import build_article
from news_digest.digest import render_digest, save_digest_html
from news_digest.filters import filter_and_tag
from news_digest.models import AppConfig, DigestSettings, ProxySettings, Source, Topic
from news_digest.settings import EnvSettings
from news_digest.state import ProcessedState, filter_unsent
from news_digest.summarizer import summarize_articles


def _config() -> AppConfig:
    return AppConfig(
        digest=DigestSettings(
            timezone="Asia/Shanghai",
            lookback_hours=24,
            max_candidates=30,
            max_articles=10,
            language="ru",
        ),
        proxy=ProxySettings(mode="off"),
        topics=[
            Topic(id="ai", name="Искусственный интеллект", keywords=["openai", "llm"]),
        ],
        sources=[
            Source(
                id="rss1",
                name="RSS One",
                type="rss",
                url="https://example.com/feed",
                topics=["ai"],
            ),
            Source(
                id="html1",
                name="HTML One",
                type="html",
                url="https://example.com/",
                topics=["ai"],
                selectors={"item": "a", "title": "a", "link": "a"},
            ),
            Source(
                id="tg1",
                name="TG One",
                type="telegram",
                url="https://t.me/s/example",
                topics=["ai"],
            ),
        ],
    )


def test_offline_pipeline_dry_run(tmp_path: Path) -> None:
    now = datetime(2026, 10, 30, 12, tzinfo=UTC)
    articles = [
        build_article(
            title="OpenAI LLM release",
            url="https://example.com/a",
            source="RSS One",
            published_at=now - timedelta(hours=2),
            excerpt="OpenAI released an LLM update.",
            content="OpenAI released an LLM update for developers.",
            source_type="rss",
            extra={"source_id": "rss1"},
        ),
        build_article(
            title="HTML OpenAI note",
            url="https://example.com/b",
            source="HTML One",
            published_at=now - timedelta(hours=3),
            excerpt="Page about OpenAI tools.",
            content="Page about OpenAI tools.",
            source_type="html",
            extra={"source_id": "html1"},
        ),
        build_article(
            title="TG post about LLM",
            url="https://t.me/example/1",
            source="TG One",
            published_at=now - timedelta(hours=1),
            excerpt="Telegram channel notes an LLM launch.",
            content="Telegram channel notes an LLM launch.",
            source_type="telegram",
            extra={"source_id": "tg1"},
        ),
        build_article(
            title="Old noise",
            url="https://example.com/old",
            source="RSS One",
            published_at=now - timedelta(hours=48),
            excerpt="OpenAI old",
            content="OpenAI old",
            source_type="rss",
            extra={"source_id": "rss1"},
        ),
    ]
    assert all(articles)

    config = _config()
    with patch("news_digest.collector.collect_articles", return_value=articles):
        from news_digest.collector import collect_articles

        collected = collect_articles(config)

    filtered = filter_and_tag(collected, config, now=now)
    assert len(filtered) == 3
    assert {a.source_type for a in filtered} == {"rss", "html", "telegram"}

    fresh = filter_unsent(filtered, ProcessedState.empty())
    env = EnvSettings(
        openai_api_key=None,
        openai_model="gpt-6-luna",
        smtp_host="smtp.mail.ru",
        smtp_port=465,
        smtp_username=None,
        smtp_password=None,
        email_from=None,
        email_to=[],
    )
    summarized = summarize_articles(
        fresh[: config.digest.max_articles],
        env=env,
        digest=config.digest,
        enabled=False,
    )
    assert all(item.summary for item in summarized)

    digest = render_digest(summarized, config, generated_at=now)
    assert "Новостной дайджест — 30.10.2026" in digest.title
    html_path = save_digest_html(digest.html, tmp_path / "digest.html")
    assert html_path.exists()
    assert "Искусственный интеллект" in html_path.read_text(encoding="utf-8")
