from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from news_digest.articles import build_article, normalize_url, to_utc


def test_normalize_url_strips_tracking_and_fragment() -> None:
    url = normalize_url(
        "https://Example.com/path/story/?utm_source=x&fbclid=1&keep=1#section"
    )
    assert url == "https://example.com/path/story?keep=1"


def test_normalize_telegram_post_url() -> None:
    assert normalize_url("https://t.me/OpenAI/123?utm_source=tg") == "https://t.me/OpenAI/123"
    assert normalize_url("https://telegram.me/huggingface/9/") == "https://t.me/huggingface/9"


def test_build_article_requires_title_and_url() -> None:
    assert build_article(title="", url="https://x.test/a", source="s") is None
    assert build_article(title="Hello", url="", source="s") is None


def test_build_article_normalizes_naive_datetime_to_utc() -> None:
    naive = datetime(2026, 10, 30, 12, 0, 0)
    article = build_article(
        title="  AI news  ",
        url="https://news.example/a?utm_campaign=1",
        source="Example",
        published_at=naive,
        source_type="rss",
    )
    assert article is not None
    assert article.title == "AI news"
    assert article.url == "https://news.example/a"
    assert article.published_at == datetime(2026, 10, 30, 12, 0, 0, tzinfo=UTC)


def test_to_utc_converts_offset() -> None:
    local = datetime(2026, 10, 30, 12, 0, tzinfo=timezone(timedelta(hours=8)))
    assert to_utc(local) == datetime(2026, 10, 30, 4, 0, tzinfo=UTC)
