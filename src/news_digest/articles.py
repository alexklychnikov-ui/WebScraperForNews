from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = frozenset(
    {
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
        "igshid",
        "si",
        "ref",
        "ref_src",
    }
)

_TITLE_NOISE_RE = re.compile(r"\s+")


@dataclass
class Article:
    title: str
    url: str
    source: str
    published_at: datetime | None = None
    topic: str | None = None
    excerpt: str = ""
    content: str = ""
    summary: str = ""
    source_type: str = "rss"
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.published_at is not None:
            payload["published_at"] = self.published_at.astimezone(UTC).isoformat()
        return payload


def to_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def normalize_title(title: str) -> str:
    return _TITLE_NOISE_RE.sub(" ", title or "").strip()


def normalize_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""

    parts = urlsplit(raw)
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    path = parts.path or "/"

    if netloc in {"t.me", "telegram.me", "www.t.me"}:
        tg = re.match(
            r"^/(?P<channel>[A-Za-z0-9_]+)/(?P<msg_id>\d+)/?$",
            path,
        )
        if tg:
            return f"https://t.me/{tg.group('channel')}/{tg.group('msg_id')}"

    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    query_items = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        key_l = key.lower()
        if key_l in TRACKING_QUERY_KEYS:
            continue
        if any(key_l.startswith(prefix) for prefix in TRACKING_QUERY_PREFIXES):
            continue
        query_items.append((key, value))
    query = urlencode(query_items, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def is_valid_article_fields(title: str, url: str) -> bool:
    return bool(normalize_title(title) and normalize_url(url))


def build_article(
    *,
    title: str,
    url: str,
    source: str,
    published_at: datetime | None = None,
    topic: str | None = None,
    excerpt: str = "",
    content: str = "",
    summary: str = "",
    source_type: str = "rss",
    extra: dict[str, Any] | None = None,
) -> Article | None:
    clean_title = normalize_title(title)
    clean_url = normalize_url(url)
    if not clean_title or not clean_url:
        return None
    return Article(
        title=clean_title,
        url=clean_url,
        source=source,
        published_at=to_utc(published_at),
        topic=topic,
        excerpt=(excerpt or "").strip(),
        content=(content or "").strip(),
        summary=(summary or "").strip(),
        source_type=source_type,
        extra=extra or {},
    )
