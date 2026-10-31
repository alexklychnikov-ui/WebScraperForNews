# Web-скрапер новостей с AI-суммаризацией

![Автоматический сбор новостей NODEX](Docs/Автоматический%20сбор%20новостей%20NODEX.png)

Локальный пайплайн: сбор новостей (RSS / HTML / Telegram `t.me/s`) → фильтр по темам → AI-summary → HTML-дайджест на почту.

## Стек

- Python 3.11+
- `feedparser`, BeautifulSoup, OpenAI, Jinja2, Flask
- SMTP (Mail.ru и др.), опционально SOCKS5 (`socks5h://127.0.0.1:12335`)

## Быстрый старт (Windows)

```powershell
cd C:\Python\Projects\WebScraperForNews
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

Заполни `.env`: `OPENAI_API_KEY`, SMTP (`SMTP_*`, `EMAIL_FROM`, `EMAIL_TO`).

```powershell
# дашборд источников / тем / прокси
.\.venv\Scripts\python.exe run_dashboard.py
# http://127.0.0.1:8765

# предпросмотр
.\.venv\Scripts\python.exe run.py --dry-run

# отправка дайджеста
.\.venv\Scripts\python.exe run.py
```

Если `Activate.ps1` режется политикой — не активируй venv, зови `.\.venv\Scripts\python.exe` напрямую.

## Как устроено

1. Читает `config/sources.json` (темы, источники, proxy mode).
2. Тянет свежие материалы за `lookback_hours`, дедуп по `data/processed_articles.json`.
3. Фильтрует по keywords тем, лимиты `max_articles` / `max_per_source`.
4. Саммари через OpenAI (`OPENAI_MODEL`, по умолчанию `gpt-6-luna`); `--no-ai` — excerpt без API.
5. Рендер `templates/digest.html.j2` → `output/digest.html` (+ txt/json).
6. SMTP; state обновляется **только после успешной отправки**.

Прокси: `auto` (direct → SOCKS при ошибке) / `always` / `off`. Per-source `proxy_mode`: `inherit|auto|always|off`.  
Telegram: только публичные каналы через `https://t.me/s/<channel>`.

## Структура

```
run.py / run_dashboard.py
config/sources.json
src/news_digest/          # collector, feeds, scraper, telegram, AI, SMTP, dashboard
templates/digest.html.j2
data/                     # processed state
output/                   # последний дайджест
scripts/register_daily_task.ps1
Docs/                     # установка, ТЗ, скрины, демо, visual-бриф
```

## Расписание

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\register_daily_task.ps1
```

Задача `WebScraperForNews-DailyDigest`, по умолчанию 08:00 (таймзона в `config/sources.json`).

## Тесты

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Документация (`Docs/`)

- [Docs/Автоматический сбор новостей NODEX.png](Docs/Автоматический%20сбор%20новостей%20NODEX.png) — мокап / обложка
- [Docs/INSTALL.md](Docs/INSTALL.md) — установка, `.env`, SMTP, ограничения
- [Docs/TZ_WebScraperForNews.docx](Docs/TZ_WebScraperForNews.docx) — техническое задание
- [Docs/visual.md](Docs/visual.md) — бриф демо-ролика
- [Docs/webscraperfornews.mp4](Docs/webscraperfornews.mp4) — демо-ролик
- [Docs/dashboard_01_proxy.png](Docs/dashboard_01_proxy.png) — дашборд: прокси
- [Docs/dashboard_02_topics.png](Docs/dashboard_02_topics.png) — дашборд: темы
- [Docs/dashboard_03_sources.png](Docs/dashboard_03_sources.png) — дашборд: источники
- [Docs/Скриншот 31-10-2026 111600.png](Docs/Скриншот%2031-10-2026%20111600.png) — пример HTML-дайджеста в почте
