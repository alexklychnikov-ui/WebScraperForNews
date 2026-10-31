from __future__ import annotations

from news_digest.config import load_config
from news_digest.settings import load_validated_config, validate_app_config


def test_sources_config_has_mvp_boundaries() -> None:
    config = load_config()
    validate_app_config(config)

    assert config.digest.timezone == "Asia/Shanghai"
    assert config.digest.schedule_hour == 8
    assert config.digest.lookback_hours == 24
    assert config.digest.max_candidates == 30
    assert config.digest.max_articles == 10
    assert config.digest.language == "ru"

    types = {source.type for source in config.sources}
    assert "rss" in types
    assert "html" in types
    assert "telegram" in types
    assert len(config.enabled_sources()) >= 4
    assert any(s.type == "telegram" for s in config.sources)


def test_load_validated_config_without_secrets() -> None:
    config, env = load_validated_config(require_secrets=False)
    assert config.topics
    assert env.openai_model
