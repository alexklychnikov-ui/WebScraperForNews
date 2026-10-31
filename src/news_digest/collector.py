from __future__ import annotations

import logging

from news_digest.articles import Article
from news_digest.feeds import fetch_rss_source
from news_digest.models import AppConfig
from news_digest.scraper import fetch_html_source
from news_digest.telegram import fetch_telegram_source

log = logging.getLogger(__name__)


def collect_articles(config: AppConfig) -> list[Article]:
    """Collect from all enabled source types."""
    limit = config.digest.max_per_source
    collected: list[Article] = []

    for source in config.enabled_sources():
        try:
            if source.type == "rss":
                batch = fetch_rss_source(source, config.proxy, limit=limit)
            elif source.type == "html":
                batch = fetch_html_source(source, config.proxy, limit=limit)
            elif source.type == "telegram":
                batch = fetch_telegram_source(source, config.proxy, limit=limit)
            else:
                log.warning("Unknown source type %s for %s", source.type, source.id)
                continue
            collected.extend(batch)
        except Exception as exc:  # noqa: BLE001 - continue other sources
            log.error("Source %s failed: %s", source.id, exc)

    log.info("Collected %s articles from enabled sources", len(collected))
    return collected
