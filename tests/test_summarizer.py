from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from news_digest.articles import build_article
from news_digest.models import DigestSettings
from news_digest.settings import EnvSettings
from news_digest.summarizer import summarize_articles, summarize_one


def _env(**overrides: object) -> EnvSettings:
    base = EnvSettings(
        openai_api_key="test-key",
        openai_model="gpt-6-luna",
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_username=None,
        smtp_password=None,
        email_from=None,
        email_to=[],
    )
    return EnvSettings(**{**base.__dict__, **overrides})


def test_summarize_disabled_uses_fallback() -> None:
    article = build_article(
        title="Hello",
        url="https://ex.com/a",
        source="s",
        excerpt="Short excerpt about news.",
    )
    assert article
    out = summarize_articles(
        [article],
        env=_env(),
        digest=DigestSettings(),
        enabled=False,
    )
    assert out[0].summary.startswith("Short excerpt")


def test_summarize_one_success_and_retry(monkeypatch) -> None:
    article = build_article(
        title="OpenAI update",
        url="https://ex.com/b",
        source="s",
        content="OpenAI released something important today.",
    )
    assert article
    client = MagicMock()
    ok = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Короткое summary."))]
    )
    client.chat.completions.create.side_effect = [TimeoutError("boom"), ok]

    # speed up retries
    monkeypatch.setattr("news_digest.summarizer.time.sleep", lambda *_: None)
    result = summarize_one(
        article,
        client=client,
        model="gpt-6-luna",
        digest=DigestSettings(),
        retries=3,
    )
    assert result.summary == "Короткое summary."
    assert client.chat.completions.create.call_count == 2


def test_summarize_one_fallback_on_total_failure(monkeypatch) -> None:
    article = build_article(
        title="Title only",
        url="https://ex.com/c",
        source="s",
        excerpt="Fallback text here",
    )
    assert article
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("down")
    monkeypatch.setattr("news_digest.summarizer.time.sleep", lambda *_: None)
    result = summarize_one(
        article,
        client=client,
        model="gpt-6-luna",
        digest=DigestSettings(),
        retries=2,
    )
    assert "Fallback text" in result.summary
