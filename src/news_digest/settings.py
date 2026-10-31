from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from news_digest.config import ROOT_DIR, load_config
from news_digest.models import AppConfig


class ConfigError(ValueError):
    """Invalid or incomplete runtime configuration."""


@dataclass(frozen=True)
class EnvSettings:
    openai_api_key: str | None
    openai_model: str
    smtp_host: str
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None
    email_from: str | None
    email_to: list[str]


def _split_emails(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.replace(";", ",").split(",") if part.strip()]


def load_env_settings(*, require_secrets: bool = False) -> EnvSettings:
    load_dotenv(ROOT_DIR / ".env")
    settings = EnvSettings(
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_model=os.getenv("OPENAI_MODEL") or "gpt-6-luna",
        smtp_host=os.getenv("SMTP_HOST") or "smtp.gmail.com",
        smtp_port=int(os.getenv("SMTP_PORT") or "587"),
        smtp_username=os.getenv("SMTP_USERNAME") or None,
        smtp_password=os.getenv("SMTP_PASSWORD") or None,
        email_from=os.getenv("EMAIL_FROM") or None,
        email_to=_split_emails(os.getenv("EMAIL_TO")),
    )
    if require_secrets:
        missing: list[str] = []
        if not settings.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not settings.smtp_username:
            missing.append("SMTP_USERNAME")
        if not settings.smtp_password:
            missing.append("SMTP_PASSWORD")
        if not settings.email_from:
            missing.append("EMAIL_FROM")
        if not settings.email_to:
            missing.append("EMAIL_TO")
        if missing:
            raise ConfigError(
                "Отсутствуют обязательные переменные окружения: " + ", ".join(missing)
            )
    return settings


def validate_app_config(config: AppConfig) -> None:
    errors: list[str] = []
    if not config.topics:
        errors.append("в config нет ни одной темы")
    if not config.sources:
        errors.append("в config нет ни одного источника")
    topic_ids = {topic.id for topic in config.topics}
    for topic in config.topics:
        if not topic.id:
            errors.append("тема без id")
        if not topic.keywords:
            errors.append(f"тема {topic.id!r} без keywords")
    source_ids: set[str] = set()
    for source in config.sources:
        if not source.id or not source.url:
            errors.append(f"источник без id/url: {source!r}")
            continue
        if source.id in source_ids:
            errors.append(f"дубликат source id: {source.id}")
        source_ids.add(source.id)
        for topic_id in source.topics:
            if topic_id not in topic_ids:
                errors.append(f"источник {source.id}: неизвестная тема {topic_id!r}")
    digest = config.digest
    if digest.lookback_hours < 1:
        errors.append("digest.lookback_hours должен быть >= 1")
    if digest.max_candidates < 1 or digest.max_articles < 1:
        errors.append("digest.max_candidates и max_articles должны быть >= 1")
    if not (0 <= digest.schedule_hour <= 23):
        errors.append("digest.schedule_hour должен быть 0..23")
    if errors:
        raise ConfigError("; ".join(errors))


def load_validated_config(*, require_secrets: bool = False) -> tuple[AppConfig, EnvSettings]:
    config = load_config()
    validate_app_config(config)
    env = load_env_settings(require_secrets=require_secrets)
    return config, env
