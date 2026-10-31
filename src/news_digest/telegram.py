from __future__ import annotations

import logging
import re
from datetime import datetime
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from news_digest.articles import Article, build_article
from news_digest.http_client import fetch_url
from news_digest.models import ProxySettings, Source

log = logging.getLogger(__name__)

_CHANNEL_RE = re.compile(r"^[A-Za-z0-9_]{3,}$")


def normalize_telegram_preview_url(raw: str) -> str:
    value = (raw or "").strip()
    if value.startswith("@"):
        value = value[1:]
    if _CHANNEL_RE.match(value):
        return f"https://t.me/s/{value}"

    parts = urlsplit(value)
    host = parts.netloc.lower()
    path = parts.path.strip("/")
    if host in {"t.me", "telegram.me", "www.t.me"}:
        chunks = [chunk for chunk in path.split("/") if chunk]
        if not chunks:
            raise ValueError(f"invalid telegram url: {raw}")
        if chunks[0] == "s" and len(chunks) >= 2:
            channel = chunks[1]
        else:
            channel = chunks[0]
        if channel.startswith("+"):
            raise ValueError("private invite links are not supported")
        if not _CHANNEL_RE.match(channel):
            raise ValueError(f"invalid telegram channel: {channel}")
        return f"https://t.me/s/{channel}"
    raise ValueError(f"unsupported telegram url: {raw}")


def _channel_from_preview(url: str) -> str:
    path = urlsplit(url).path.strip("/")
    parts = path.split("/")
    if len(parts) >= 2 and parts[0] == "s":
        return parts[1]
    raise ValueError(f"cannot extract channel from {url}")


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def parse_telegram_preview(
    html: str,
    *,
    source: Source,
    limit: int,
    preview_url: str,
) -> list[Article]:
    soup = BeautifulSoup(html, "html.parser")
    channel = _channel_from_preview(preview_url)
    articles: list[Article] = []

    messages = soup.select("div.tgme_widget_message.js-widget_message")
    if not messages:
        messages = soup.select("div.tgme_widget_message")

    for node in messages:
        data_post = node.get("data-post") or ""
        msg_id = None
        if "/" in data_post:
            _, msg_id = data_post.rsplit("/", 1)
        if not msg_id:
            date_link = node.select_one("a.tgme_widget_message_date")
            href = date_link.get("href") if date_link else None
            if href and "/" in str(href):
                msg_id = str(href).rstrip("/").rsplit("/", 1)[-1]
        if not msg_id or not str(msg_id).isdigit():
            continue

        text = ""
        for sel in (
            "div.tgme_widget_message_text",
            "div.tgme_widget_message_caption",
        ):
            node_text = node.select_one(sel)
            if node_text:
                text = node_text.get_text("\n", strip=True)
                if text:
                    break
        if not text:
            continue

        time_node = node.select_one("time")
        published = _parse_datetime(time_node.get("datetime") if time_node else None)
        title = text.split("\n", 1)[0][:180]
        url = f"https://t.me/{channel}/{msg_id}"
        article = build_article(
            title=title,
            url=url,
            source=source.name,
            published_at=published,
            excerpt=text[:500],
            content=text,
            source_type="telegram",
            extra={"source_id": source.id, "channel": channel, "msg_id": msg_id},
        )
        if article is None:
            continue
        articles.append(article)
        if len(articles) >= limit:
            break

    return articles


def fetch_telegram_source(
    source: Source,
    proxy: ProxySettings,
    *,
    limit: int,
) -> list[Article]:
    preview_url = normalize_telegram_preview_url(source.url)
    result = fetch_url(
        preview_url,
        proxy=proxy,
        source_proxy_mode=source.proxy_mode,
        max_bytes=2_000_000,
    )
    if not result.ok or not result.text:
        raise RuntimeError(result.error or f"Telegram fetch failed for {source.id}")
    if "tgme_widget_message" not in result.text:
        raise RuntimeError(
            f"Telegram preview unavailable for {preview_url} "
            "(channel may be private or without public /s/ page)"
        )
    articles = parse_telegram_preview(
        result.text,
        source=source,
        limit=limit,
        preview_url=preview_url,
    )
    log.info(
        "Telegram %s: %s posts via %s (%s)",
        source.id,
        len(articles),
        result.used_via,
        preview_url,
    )
    return articles
