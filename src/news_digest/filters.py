from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from news_digest.articles import Article, normalize_title
from news_digest.models import AppConfig, Topic

_TITLE_KEY_RE = re.compile(r"[^a-z0-9а-яё]+", re.IGNORECASE)


def title_fingerprint(title: str) -> str:
    normalized = normalize_title(title).lower()
    return _TITLE_KEY_RE.sub(" ", normalized).strip()


def within_lookback(article: Article, *, lookback_hours: int, now: datetime | None = None) -> bool:
    if article.published_at is None:
        return True
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return article.published_at >= current - timedelta(hours=lookback_hours)


def match_topics(article: Article, topics: list[Topic]) -> list[str]:
    haystack = " ".join(
        part for part in (article.title, article.excerpt, article.content) if part
    ).lower()
    matched: list[str] = []
    for topic in topics:
        for keyword in topic.keywords:
            if keyword.lower() in haystack:
                matched.append(topic.id)
                break
    return matched


def dedupe_articles(articles: list[Article]) -> list[Article]:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    result: list[Article] = []
    for article in articles:
        title_key = title_fingerprint(article.title)
        if article.url in seen_urls:
            continue
        if title_key and title_key in seen_titles:
            continue
        seen_urls.add(article.url)
        if title_key:
            seen_titles.add(title_key)
        result.append(article)
    return result


def filter_and_tag(
    articles: list[Article],
    config: AppConfig,
    *,
    lookback_hours: int | None = None,
    now: datetime | None = None,
) -> list[Article]:
    hours = lookback_hours or config.digest.lookback_hours
    topic_index = {topic.id: topic for topic in config.topics}
    tagged: list[Article] = []

    for article in articles:
        if not within_lookback(article, lookback_hours=hours, now=now):
            continue
        source_topic_ids = []
        source_id = (article.extra or {}).get("source_id")
        if source_id:
            source = config.source_by_id(str(source_id))
            if source:
                source_topic_ids = source.topics
        candidate_topics = [
            topic_index[tid] for tid in source_topic_ids if tid in topic_index
        ] or config.topics
        matched = match_topics(article, candidate_topics)
        if not matched:
            continue
        article.topic = matched[0]
        article.extra = {**(article.extra or {}), "topics": matched}
        tagged.append(article)

    deduped = dedupe_articles(tagged)
    return deduped[: config.digest.max_candidates]
