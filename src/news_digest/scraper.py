from __future__ import annotations

import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from news_digest.articles import Article, build_article
from news_digest.http_client import fetch_url
from news_digest.models import ProxySettings, Source

log = logging.getLogger(__name__)


def parse_html_listing(
    html: str,
    *,
    source: Source,
    limit: int,
    base_url: str | None = None,
) -> list[Article]:
    selectors = source.selectors or {}
    item_sel = selectors.get("item")
    title_sel = selectors.get("title", "a")
    link_sel = selectors.get("link", "a")
    if not item_sel:
        raise ValueError(f"HTML source {source.id} requires selectors.item")

    soup = BeautifulSoup(html, "html.parser")
    base = base_url or source.url
    articles: list[Article] = []

    for item in soup.select(item_sel)[:limit]:
        title_node = item.select_one(title_sel)
        link_node = item.select_one(link_sel) or title_node
        if title_node is None or link_node is None:
            continue
        title = title_node.get_text(" ", strip=True)
        href = link_node.get("href")
        if not href:
            continue
        url = urljoin(base, str(href))
        article = build_article(
            title=title,
            url=url,
            source=source.name,
            excerpt="",
            content="",
            source_type="html",
            extra={"source_id": source.id},
        )
        if article is None:
            continue
        articles.append(article)
    return articles


def fetch_html_source(
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
    if not result.ok or not result.text:
        raise RuntimeError(result.error or f"HTML fetch failed for {source.id}")
    articles = parse_html_listing(
        result.text,
        source=source,
        limit=limit,
        base_url=result.final_url or source.url,
    )
    log.info(
        "HTML %s: %s articles via %s",
        source.id,
        len(articles),
        result.used_via,
    )
    return articles
