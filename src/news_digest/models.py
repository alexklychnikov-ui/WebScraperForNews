from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

ProxyMode = Literal["off", "always", "auto"]
SourceProxyMode = Literal["inherit", "off", "always", "auto"]
SourceType = Literal["rss", "html", "telegram"]


@dataclass
class DigestSettings:
    timezone: str = "Asia/Shanghai"
    schedule_hour: int = 8
    lookback_hours: int = 24
    max_candidates: int = 30
    max_articles: int = 10
    max_per_source: int = 15
    language: str = "ru"
    summary_style: str = "2-3 фактических предложения без домыслов и Markdown"

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> DigestSettings:
        data = data or {}
        return cls(
            timezone=str(data.get("timezone") or "Asia/Shanghai"),
            schedule_hour=int(data.get("schedule_hour") or 8),
            lookback_hours=int(data.get("lookback_hours") or 24),
            max_candidates=int(data.get("max_candidates") or 30),
            max_articles=int(data.get("max_articles") or 10),
            max_per_source=int(data.get("max_per_source") or 15),
            language=str(data.get("language") or "ru"),
            summary_style=str(
                data.get("summary_style")
                or "2-3 фактических предложения без домыслов и Markdown"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProxySettings:
    mode: ProxyMode = "auto"
    url: str = "socks5h://127.0.0.1:12335"
    timeout_seconds: int = 15

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ProxySettings:
        data = data or {}
        mode = data.get("mode", "auto")
        if mode not in ("off", "always", "auto"):
            mode = "auto"
        return cls(
            mode=mode,
            url=str(data.get("url") or "socks5h://127.0.0.1:12335"),
            timeout_seconds=int(data.get("timeout_seconds") or 15),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Topic:
    id: str
    name: str
    keywords: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Topic:
        return cls(
            id=str(data["id"]).strip(),
            name=str(data.get("name") or data["id"]).strip(),
            keywords=[str(k).strip() for k in data.get("keywords", []) if str(k).strip()],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Source:
    id: str
    name: str
    type: SourceType
    url: str
    enabled: bool = True
    topics: list[str] = field(default_factory=list)
    proxy_mode: SourceProxyMode = "inherit"
    selectors: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Source:
        source_type = data.get("type", "rss")
        if source_type not in ("rss", "html", "telegram"):
            source_type = "rss"
        proxy_mode = data.get("proxy_mode", "inherit")
        if proxy_mode not in ("inherit", "off", "always", "auto"):
            proxy_mode = "inherit"
        return cls(
            id=str(data["id"]).strip(),
            name=str(data.get("name") or data["id"]).strip(),
            type=source_type,
            url=str(data["url"]).strip(),
            enabled=bool(data.get("enabled", True)),
            topics=[str(t).strip() for t in data.get("topics", []) if str(t).strip()],
            proxy_mode=proxy_mode,
            selectors={str(k): str(v) for k, v in (data.get("selectors") or {}).items()},
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if not payload["selectors"]:
            payload.pop("selectors")
        return payload


@dataclass
class AppConfig:
    digest: DigestSettings
    proxy: ProxySettings
    topics: list[Topic]
    sources: list[Source]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        return cls(
            digest=DigestSettings.from_dict(data.get("digest")),
            proxy=ProxySettings.from_dict(data.get("proxy")),
            topics=[Topic.from_dict(item) for item in data.get("topics", [])],
            sources=[Source.from_dict(item) for item in data.get("sources", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "digest": self.digest.to_dict(),
            "proxy": self.proxy.to_dict(),
            "topics": [topic.to_dict() for topic in self.topics],
            "sources": [source.to_dict() for source in self.sources],
        }

    def topic_by_id(self, topic_id: str) -> Topic | None:
        for topic in self.topics:
            if topic.id == topic_id:
                return topic
        return None

    def source_by_id(self, source_id: str) -> Source | None:
        for source in self.sources:
            if source.id == source_id:
                return source
        return None

    def enabled_sources(self) -> list[Source]:
        return [source for source in self.sources if source.enabled]
