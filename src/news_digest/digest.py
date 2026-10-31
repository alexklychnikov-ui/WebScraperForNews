from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape

from news_digest.articles import Article
from news_digest.config import ROOT_DIR
from news_digest.models import AppConfig

TEMPLATES_DIR = ROOT_DIR / "templates"


@dataclass
class DigestRender:
    html: str
    text: str
    title: str


def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(enabled_extensions=("html", "xml", "j2")),
    )


def _tz(config: AppConfig) -> ZoneInfo:
    try:
        return ZoneInfo(config.digest.timezone)
    except Exception:  # noqa: BLE001 - Windows may need tzdata package
        return ZoneInfo("Etc/UTC")


def format_date_ru(value: datetime, tz: ZoneInfo) -> str:
    return value.astimezone(tz).strftime("%d.%m.%Y")


def format_datetime_ru(value: datetime, tz: ZoneInfo) -> str:
    return value.astimezone(tz).strftime("%d.%m.%Y %H:%M")


def group_by_topic(articles: list[Article], config: AppConfig) -> list[dict]:
    buckets: dict[str, list[Article]] = defaultdict(list)
    for article in articles:
        topic_id = article.topic or "other"
        buckets[topic_id].append(article)

    groups: list[dict] = []
    known_ids = [topic.id for topic in config.topics]
    ordered_ids = [tid for tid in known_ids if tid in buckets] + [
        tid for tid in buckets if tid not in known_ids
    ]
    tz = _tz(config)
    for topic_id in ordered_ids:
        topic = config.topic_by_id(topic_id)
        name = topic.name if topic else ("Прочее" if topic_id == "other" else topic_id)
        items = []
        for article in buckets[topic_id]:
            published = ""
            if article.published_at is not None:
                published = format_datetime_ru(article.published_at, tz)
            items.append(
                {
                    "title": article.title,
                    "url": article.url,
                    "source": article.source,
                    "summary": article.summary or article.excerpt or article.title,
                    "published_at": published,
                }
            )
        groups.append({"id": topic_id, "name": name, "items": items})
    return groups


def render_text(groups: list[dict], *, title: str, subtitle: str) -> str:
    lines = [title, subtitle, ""]
    if not groups:
        lines.append("За выбранный период релевантных новостей не найдено.")
        return "\n".join(lines)
    for group in groups:
        lines.append(group["name"])
        lines.append("")
        for item in group["items"]:
            lines.append(f"• {item['title']}")
            meta = f"  {item['source']}"
            if item["published_at"]:
                meta += f" · {item['published_at']}"
            lines.append(meta)
            lines.append(f"  {item['summary']}")
            lines.append(f"  {item['url']}")
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_digest(
    articles: list[Article],
    config: AppConfig,
    *,
    generated_at: datetime | None = None,
) -> DigestRender:
    when = generated_at or datetime.now(UTC)
    tz = _tz(config)
    title = f"Новостной дайджест — {format_date_ru(when, tz)}"
    subtitle = (
        f"Период: последние {config.digest.lookback_hours} ч · "
        f"новостей: {len(articles)}"
    )
    groups = group_by_topic(articles, config)
    html = _jinja_env().get_template("digest.html.j2").render(
        title=title,
        subtitle=subtitle,
        language=config.digest.language or "ru",
        groups=groups,
    )
    text = render_text(groups, title=title, subtitle=subtitle)
    return DigestRender(html=html, text=text, title=title)


def save_digest_html(html: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path
