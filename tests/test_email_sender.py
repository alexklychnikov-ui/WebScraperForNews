from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from news_digest.digest import DigestRender
from news_digest.email_sender import build_message, send_digest
from news_digest.settings import EnvSettings


def _env(**overrides: object) -> EnvSettings:
    base = {
        "openai_api_key": None,
        "openai_model": "gpt-6-luna",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "user@example.com",
        "smtp_password": "secret",
        "email_from": "user@example.com",
        "email_to": ["a@example.com", "b@example.com"],
    }
    base.update(overrides)
    return EnvSettings(**base)


def test_build_message_uses_bcc_for_multiple_recipients() -> None:
    digest = DigestRender(html="<p>Hi</p>", text="Hi", title="Digest")
    msg = build_message(digest, env=_env())
    assert msg["Subject"] == "Digest"
    assert msg["Bcc"] == "a@example.com, b@example.com"
    assert msg.get_body(preferencelist=("html",)).get_content() == "<p>Hi</p>\n"


def test_send_digest_success_starttls() -> None:
    digest = DigestRender(html="<p>Hi</p>", text="Hi", title="Digest")
    smtp = MagicMock()
    smtp.__enter__.return_value = smtp
    with patch("news_digest.email_sender.smtplib.SMTP", return_value=smtp) as ctor:
        send_digest(digest, env=_env())
    ctor.assert_called_once()
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("user@example.com", "secret")
    smtp.send_message.assert_called_once()


def test_send_digest_failure_does_not_hide_error() -> None:
    digest = DigestRender(html="<p>Hi</p>", text="Hi", title="Digest")
    smtp = MagicMock()
    smtp.__enter__.return_value = smtp
    smtp.send_message.side_effect = RuntimeError("smtp down")
    with patch("news_digest.email_sender.smtplib.SMTP", return_value=smtp):
        with pytest.raises(RuntimeError, match="smtp down"):
            send_digest(digest, env=_env())
