# Установка и запуск WebScraperForNews (Windows 10)

## Требования

- Python 3.11+
- Доступ в интернет (для части источников может понадобиться SOCKS-прокси)
- OpenAI API key
- SMTP (Mail.ru / другой) + пароль приложения

## Установка

```powershell
cd C:\Python\Projects\WebScraperForNews
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

Если `Activate.ps1` блокируется политикой PowerShell — не активируй venv, вызывай интерпретатор напрямую:

```powershell
.\.venv\Scripts\python.exe ...
```

## Настройка `.env`

Обязательные поля для отправки:

- `OPENAI_API_KEY`
- `OPENAI_MODEL` (по умолчанию `gpt-6-luna`)
- `SMTP_HOST` / `SMTP_PORT` (Mail.ru: `smtp.mail.ru` / `465`)
- `SMTP_USERNAME` / `SMTP_PASSWORD` (пароль приложения)
- `EMAIL_FROM` / `EMAIL_TO`

Опционально:

- `HTTPS_PROXY=socks5h://127.0.0.1:12335` — для недоступных источников и OpenAI
- `DASHBOARD_HOST` / `DASHBOARD_PORT`

Секреты хранить только в `.env` (файл в `.gitignore`). Не коммитить ключи.

## Источники и темы

Файл: `config/sources.json`  
Или дашборд:

```powershell
.\.venv\Scripts\python.exe run_dashboard.py
```

Открыть: http://127.0.0.1:8765

Типы источников: `rss`, `html`, `telegram` (`https://t.me/s/<channel>`).

## Запуск дайджеста

```powershell
# предпросмотр без отправки
.\.venv\Scripts\python.exe run.py --dry-run

# без OpenAI (fallback excerpt)
.\.venv\Scripts\python.exe run.py --dry-run --no-ai

# боевая отправка
.\.venv\Scripts\python.exe run.py
```

Артефакты: `output/digest.html`, `output/digest.txt`, `output/articles.json`  
Состояние отправленных: `data/processed_articles.json`

## Ежедневный запуск (Task Scheduler)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\register_daily_task.ps1
```

По умолчанию задача `WebScraperForNews-DailyDigest` в 08:00 локального времени.

Проверка:

```powershell
Get-ScheduledTask -TaskName WebScraperForNews-DailyDigest
```

## Безопасность

- Парсить только публичные новости
- Не хранить полные тексты дольше нужного для summary
- Использовать app password, не основной пароль почты
- Не логировать API/SMTP секреты

## Ограничения

- Вёрстка сайтов и `t.me/s` может меняться
- Paywall / robots / CAPTCHA не обходятся
- Telegram: только публичные каналы с `/s/` preview
- OpenAI: стоимость, rate limit, региональные ограничения (часто нужен proxy)
- SMTP: лимиты провайдера
- AI может ошибаться; в промпте запрещены домыслы, но 100% гарантии нет
