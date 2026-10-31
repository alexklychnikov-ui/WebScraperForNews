from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path

from news_digest.models import AppConfig, ProxySettings, Source, Topic

_LOCK = threading.Lock()

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT_DIR / "config" / "sources.json"

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = _SLUG_RE.sub("-", value).strip("-")
    return value or "item"


def config_path() -> Path:
    override = os.getenv("SOURCES_CONFIG_PATH")
    return Path(override) if override else DEFAULT_CONFIG_PATH


def load_config(path: Path | None = None) -> AppConfig:
    target = path or config_path()
    with _LOCK:
        raw = json.loads(target.read_text(encoding="utf-8"))
    return AppConfig.from_dict(raw)


def save_config(config: AppConfig, path: Path | None = None) -> None:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(config.to_dict(), ensure_ascii=False, indent=2) + "\n"
    with _LOCK:
        tmp = target.with_suffix(".tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(target)


def resolve_proxy_url(proxy: ProxySettings) -> str:
    return (os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or proxy.url).strip()


def ensure_unique_id(base: str, existing: set[str]) -> str:
    candidate = slugify(base)
    if candidate not in existing:
        return candidate
    index = 2
    while f"{candidate}-{index}" in existing:
        index += 1
    return f"{candidate}-{index}"


def upsert_topic(config: AppConfig, topic: Topic) -> AppConfig:
    topics = [item for item in config.topics if item.id != topic.id]
    topics.append(topic)
    topics.sort(key=lambda item: item.name.lower())
    config.topics = topics
    return config


def delete_topic(config: AppConfig, topic_id: str) -> AppConfig:
    config.topics = [item for item in config.topics if item.id != topic_id]
    for source in config.sources:
        source.topics = [tid for tid in source.topics if tid != topic_id]
    return config


def upsert_source(config: AppConfig, source: Source) -> AppConfig:
    sources = [item for item in config.sources if item.id != source.id]
    sources.append(source)
    sources.sort(key=lambda item: item.name.lower())
    config.sources = sources
    return config


def delete_source(config: AppConfig, source_id: str) -> AppConfig:
    config.sources = [item for item in config.sources if item.id != source_id]
    return config
