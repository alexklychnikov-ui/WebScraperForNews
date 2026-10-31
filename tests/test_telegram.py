from __future__ import annotations

from pathlib import Path

import pytest

from news_digest.models import Source
from news_digest.telegram import normalize_telegram_preview_url, parse_telegram_preview

FIXTURES = Path(__file__).parent / "fixtures"


def test_normalize_telegram_preview_url() -> None:
    assert normalize_telegram_preview_url("@OpenAI") == "https://t.me/s/OpenAI"
    assert normalize_telegram_preview_url("https://t.me/OpenAI") == "https://t.me/s/OpenAI"
    assert normalize_telegram_preview_url("https://t.me/s/huggingface") == "https://t.me/s/huggingface"


def test_normalize_rejects_invite() -> None:
    with pytest.raises(ValueError):
        normalize_telegram_preview_url("https://t.me/+abc123")


def test_parse_telegram_preview_fixture() -> None:
    source = Source(
        id="tg-openai-news",
        name="OpenAI News Telegram",
        type="telegram",
        url="https://t.me/s/OpenAINews",
    )
    html = (FIXTURES / "telegram_s_sample.html").read_text(encoding="utf-8")
    articles = parse_telegram_preview(
        html,
        source=source,
        limit=10,
        preview_url="https://t.me/s/OpenAI",
    )
    assert len(articles) == 2
    assert articles[0].url == "https://t.me/OpenAI/101"
    assert articles[0].source_type == "telegram"
    assert "GPT launch" in articles[0].content
