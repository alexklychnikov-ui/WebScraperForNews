from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage

from news_digest.digest import DigestRender
from news_digest.settings import EnvSettings

log = logging.getLogger(__name__)


def build_message(
    digest: DigestRender,
    *,
    env: EnvSettings,
    recipients: list[str] | None = None,
) -> EmailMessage:
    to_list = recipients or env.email_to
    if not env.email_from:
        raise ValueError("EMAIL_FROM is required")
    if not to_list:
        raise ValueError("EMAIL_TO is required")

    msg = EmailMessage()
    msg["Subject"] = digest.title
    msg["From"] = env.email_from
    if len(to_list) == 1:
        msg["To"] = to_list[0]
    else:
        msg["To"] = env.email_from
        msg["Bcc"] = ", ".join(to_list)
    msg.set_content(digest.text)
    msg.add_alternative(digest.html, subtype="html")
    return msg


def send_digest(
    digest: DigestRender,
    *,
    env: EnvSettings,
    timeout: int = 30,
) -> None:
    message = build_message(digest, env=env)
    if not env.smtp_username or not env.smtp_password:
        raise ValueError("SMTP_USERNAME and SMTP_PASSWORD are required")

    log.info(
        "Sending digest via SMTP host=%s port=%s to=%s",
        env.smtp_host,
        env.smtp_port,
        len(env.email_to),
    )
    if env.smtp_port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            env.smtp_host,
            env.smtp_port,
            timeout=timeout,
            context=context,
        ) as smtp:
            smtp.login(env.smtp_username, env.smtp_password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(env.smtp_host, env.smtp_port, timeout=timeout) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
            smtp.login(env.smtp_username, env.smtp_password)
            smtp.send_message(message)
    log.info("Digest email sent successfully")
