from __future__ import annotations

from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

from news_digest.config import (
    delete_source,
    delete_topic,
    ensure_unique_id,
    load_config,
    save_config,
    upsert_source,
    upsert_topic,
)
from news_digest.http_client import probe_source
from news_digest.models import ProxySettings, Source, Topic

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def _parse_keywords(raw: str) -> list[str]:
    parts = []
    for chunk in raw.replace("\n", ",").split(","):
        value = chunk.strip()
        if value:
            parts.append(value)
    return parts


def create_app() -> Flask:
    app = Flask(__name__, template_folder=str(TEMPLATES_DIR))
    app.secret_key = "local-dashboard-dev-only"

    @app.get("/")
    def index():
        config = load_config()
        return render_template(
            "index.html",
            config=config,
            topic_map={topic.id: topic for topic in config.topics},
        )

    @app.post("/proxy")
    def update_proxy():
        config = load_config()
        mode = request.form.get("mode", "auto")
        if mode not in ("off", "always", "auto"):
            mode = "auto"
        timeout_raw = request.form.get("timeout_seconds", "15").strip()
        try:
            timeout = max(1, int(timeout_raw))
        except ValueError:
            timeout = 15
        config.proxy = ProxySettings(
            mode=mode,
            url=request.form.get("url", "").strip() or "socks5h://127.0.0.1:12335",
            timeout_seconds=timeout,
        )
        save_config(config)
        flash("Настройки прокси сохранены.", "ok")
        return redirect(url_for("index"))

    @app.post("/topics")
    def create_topic():
        config = load_config()
        name = request.form.get("name", "").strip()
        if not name:
            flash("Название темы обязательно.", "error")
            return redirect(url_for("index"))
        topic_id = request.form.get("id", "").strip() or ensure_unique_id(
            name, {item.id for item in config.topics}
        )
        topic = Topic(
            id=topic_id,
            name=name,
            keywords=_parse_keywords(request.form.get("keywords", "")),
        )
        save_config(upsert_topic(config, topic))
        flash(f"Тема «{topic.name}» сохранена.", "ok")
        return redirect(url_for("index") + "#topics")

    @app.post("/topics/<topic_id>/delete")
    def remove_topic(topic_id: str):
        config = load_config()
        save_config(delete_topic(config, topic_id))
        flash("Тема удалена.", "ok")
        return redirect(url_for("index") + "#topics")

    @app.post("/sources")
    def create_source():
        config = load_config()
        name = request.form.get("name", "").strip()
        url = request.form.get("url", "").strip()
        if not name or not url:
            flash("Имя и URL источника обязательны.", "error")
            return redirect(url_for("index") + "#sources")

        source_type = request.form.get("type", "rss")
        if source_type not in ("rss", "html", "telegram"):
            source_type = "rss"
        proxy_mode = request.form.get("proxy_mode", "inherit")
        if proxy_mode not in ("inherit", "off", "always", "auto"):
            proxy_mode = "inherit"

        source_id = request.form.get("id", "").strip() or ensure_unique_id(
            name, {item.id for item in config.sources}
        )
        selected_topics = request.form.getlist("topics")
        source = Source(
            id=source_id,
            name=name,
            type=source_type,
            url=url,
            enabled=request.form.get("enabled") == "on",
            topics=selected_topics,
            proxy_mode=proxy_mode,
        )
        save_config(upsert_source(config, source))
        flash(f"Источник «{source.name}» сохранён.", "ok")
        return redirect(url_for("index") + "#sources")

    @app.post("/sources/<source_id>/toggle")
    def toggle_source(source_id: str):
        config = load_config()
        source = config.source_by_id(source_id)
        if not source:
            flash("Источник не найден.", "error")
            return redirect(url_for("index") + "#sources")
        source.enabled = not source.enabled
        save_config(upsert_source(config, source))
        state = "включён" if source.enabled else "выключен"
        flash(f"Источник «{source.name}» {state}.", "ok")
        return redirect(url_for("index") + "#sources")

    @app.post("/sources/<source_id>/delete")
    def remove_source(source_id: str):
        config = load_config()
        save_config(delete_source(config, source_id))
        flash("Источник удалён.", "ok")
        return redirect(url_for("index") + "#sources")

    @app.post("/sources/<source_id>/probe")
    def probe(source_id: str):
        config = load_config()
        source = config.source_by_id(source_id)
        if not source:
            flash("Источник не найден.", "error")
            return redirect(url_for("index") + "#sources")
        result = probe_source(source, config.proxy)
        return render_template(
            "index.html",
            config=config,
            topic_map={topic.id: topic for topic in config.topics},
            probe_result=result,
        )

    @app.post("/proxy/probe")
    def probe_proxy_target():
        config = load_config()
        url = request.form.get("url", "").strip() or "https://example.com"
        fake = Source(
            id="probe",
            name="Probe",
            type="rss",
            url=url,
            enabled=True,
            topics=[],
            proxy_mode="inherit",
        )
        result = probe_source(fake, config.proxy)
        return render_template(
            "index.html",
            config=config,
            topic_map={topic.id: topic for topic in config.topics},
            probe_result=result,
        )

    return app
