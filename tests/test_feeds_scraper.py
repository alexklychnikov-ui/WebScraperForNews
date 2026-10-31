from __future__ import annotations

from pathlib import Path

from news_digest.feeds import parse_rss_bytes
from news_digest.models import Source
from news_digest.scraper import parse_html_listing

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_rss_fixture() -> None:
    source = Source(
        id="sample",
        name="Sample",
        type="rss",
        url="https://example.com/feed",
    )
    payload = (FIXTURES / "sample_rss.xml").read_bytes()
    articles = parse_rss_bytes(payload, source=source, limit=10)
    assert len(articles) == 2
    assert articles[0].url == "https://news.example.com/openai-model"
    assert articles[0].published_at is not None
    assert articles[0].source_type == "rss"


def test_parse_html_fixture() -> None:
    source = Source(
        id="hn",
        name="HN",
        type="html",
        url="https://news.ycombinator.com/",
        selectors={
            "item": "tr.athing",
            "title": "span.titleline > a",
            "link": "span.titleline > a",
        },
    )
    html = (FIXTURES / "sample_hn.html").read_text(encoding="utf-8")
    articles = parse_html_listing(html, source=source, limit=10)
    assert len(articles) == 2
    assert articles[0].url == "https://example.com/a"
    assert articles[1].url == "https://news.ycombinator.com/item?id=2"
    assert articles[1].title == "Relative story"
