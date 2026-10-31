from __future__ import annotations

import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
from time import mktime
from typing import Any

import feedparser

from news_digest.articles import Article, build_article
from news_digest.http_client import fetch_url
from news_digest.models import ProxySettings, Source

log = logging.getLogger(__name__)


def _entry_datetime(entry: Any) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime.fromtimestamp(mktime(parsed))
            except (OverflowError, TypeError, ValueError):
                pass
    for key in ("published", "updated"):
        raw = entry.get(key)
        if not raw:
            continue
        try:
            return parsedate_to_datetime(raw)
        except (TypeError, ValueError, IndexError):
            continue
    return None


def parse_rss_bytes(
    payload: bytes | str,
    *,
    source: Source,
    limit: int,
) -> list[Article]:
    feed = feedparser.parse(payload)
    articles: list[Article] = []
    for entry in feed.entries[:limit]:
        title = getattr(entry, "title", "") or ""
        link = getattr(entry, "link", "") or ""
        excerpt = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
        article = build_article(
            title=title,
            url=link,
            source=source.name,
            published_at=_entry_datetime(entry),
            excerpt=excerpt,
            content=excerpt,
            source_type="rss",
            extra={"source_id": source.id},
        )
        if article is None:
            continue
        articles.append(article)
    return articles


def fetch_rss_source(
    source: Source,
    proxy: ProxySettings,
    *,
    limit: int,
) -> list[Article]:
    result = fetch_url(
        source.url,
        proxy=proxy,
        source_proxy_mode=source.proxy_mode,
        max_bytes=2_000_000,
    )
    if not result.ok or result.content is None:
        raise RuntimeError(result.error or f"RSS fetch failed for {source.id}")
    articles = parse_rss_bytes(result.content, source=source, limit=limit)
    log.info(
        "RSS %s: %s articles via %s",
        source.id,
        len(articles),
        result.used_via,
    )
    return articles
