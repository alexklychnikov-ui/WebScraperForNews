from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.shared import Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Docs" / "TZ_WebScraperForNews.docx"


def add_heading(doc: Document, text: str, level: int = 1) -> None:
    doc.add_heading(text, level=level)


def add_para(doc: Document, text: str) -> None:
    p = doc.add_paragraph(text)
    for run in p.runs:
        run.font.size = Pt(11)


def add_bullets(doc: Document, items: list[str]) -> None:
    for item in items:
        doc.add_paragraph(item, style="List Bullet")


def main() -> None:
    doc = Document()
    add_heading(doc, "Техническое задание", 0)
    add_heading(doc, "WebScraperForNews — новостной дайджест с AI", 1)

    add_heading(doc, "1. Название и описание проекта", 1)
    add_para(
        doc,
        "WebScraperForNews — локальный Python-скрипт, который собирает публичные новости "
        "из RSS/HTML и публичных Telegram-каналов (t.me/s), фильтрует по ключевым словам, "
        "суммаризирует через OpenAI и ежедневно отправляет HTML-дайджест на email.",
    )

    add_heading(doc, "2. Целевая аудитория и боли", 1)
    add_para(doc, "Целевая аудитория:")
    add_bullets(
        doc,
        [
            "специалисты и руководители, которым нужен отраслевой мониторинг;",
            "аналитики и основатели стартапов, отслеживающие конкурентов и рынок;",
            "пользователи, которым нужен короткий персональный дайджест без ручного чтения лент.",
        ],
    )
    add_para(doc, "Боли:")
    add_bullets(
        doc,
        [
            "информационный шум и потеря времени на чтение множества источников;",
            "сложность ежедневного ручного сбора и группировки новостей;",
            "необходимость быстро понимать суть новости без полного текста;",
            "недоступность части источников без прокси.",
        ],
    )

    add_heading(doc, "3. Функциональные требования", 1)
    add_bullets(
        doc,
        [
            "Сбор новостей из RSS/Atom, HTML-листингов и публичных Telegram-каналов через t.me/s.",
            "Фильтрация по ключевым словам и временному окну (по умолчанию 24 часа).",
            "Дедупликация по каноническому URL и нормализованному заголовку.",
            "AI-суммаризация каждой выбранной новости (2–3 предложения на русском).",
            "Группировка материалов по темам.",
            "Генерация HTML- и text-дайджеста (Jinja2, email-совместимая вёрстка).",
            "Ежедневная отправка на email через SMTP; dry-run без отправки.",
            "Локальный дашборд для настройки источников, тем и прокси.",
            "Поддержка SOCKS5-прокси с режимами off/always/auto.",
            "Сохранение состояния уже отправленных материалов; повторно не отправлять.",
        ],
    )

    add_heading(doc, "4. Нефункциональные и технические требования", 1)
    add_bullets(
        doc,
        [
            "Язык реализации: Python 3.11+.",
            "Библиотеки: requests, beautifulsoup4, feedparser, openai, jinja2, flask, smtplib.",
            "Конфигурация источников: config/sources.json; секреты: .env.",
            "Запуск: run.py; дашборд: run_dashboard.py; планировщик: Task Scheduler.",
            "Парсить только публичные новости; хранить ссылки и краткие summary.",
        ],
    )

    add_heading(doc, "5. Ограничения и риски", 1)
    add_bullets(
        doc,
        [
            "Бюджет: стоимость OpenAI API и возможный платный прокси/VPS.",
            "Изменение HTML-вёрстки сайтов и страниц t.me/s ломает парсеры.",
            "Paywall, CAPTCHA, антибот-защита и приватные TG-каналы вне скоупа.",
            "Региональная недоступность источников/OpenAI без proxy.",
            "SMTP-лимиты провайдера и необходимость пароля приложения.",
            "AI может ошибаться; промпт запрещает домыслы, но 100% гарантии нет.",
            "Нехватка релевантных новостей за сутки — дайджест может быть пустым.",
            "Telegram-группы и Bot API/Telethon не поддерживаются в MVP.",
        ],
    )

    add_heading(doc, "6. Критерии приёмки", 1)
    add_bullets(
        doc,
        [
            "Конфигурируются источники и темы через JSON/дашборд.",
            "Dry-run формирует output/digest.html без SMTP и без sent-state.",
            "Боевой запуск шлёт письмо; state обновляется только после SMTP OK.",
            "Повторный запуск не дублирует уже отправленные материалы.",
            "Автотесты проходят без сети, OpenAI и реальной почты.",
        ],
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
