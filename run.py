from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from news_digest.collector import collect_articles  # noqa: E402
from news_digest.digest import render_digest, save_digest_html  # noqa: E402
from news_digest.email_sender import send_digest  # noqa: E402
from news_digest.filters import filter_and_tag  # noqa: E402
from news_digest.lock import LockError, RunLock  # noqa: E402
from news_digest.settings import ConfigError, load_validated_config  # noqa: E402
from news_digest.state import (  # noqa: E402
    filter_unsent,
    load_state,
    mark_sent,
    prune_state,
    save_state,
)
from news_digest.summarizer import summarize_articles  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="News digest scraper")
    parser.add_argument("--dry-run", action="store_true", help="Не отправлять email")
    parser.add_argument("--no-ai", action="store_true", help="Пропустить OpenAI")
    parser.add_argument("--since-hours", type=int, default=None)
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    parser.add_argument(
        "--require-secrets",
        action="store_true",
        help="Требовать OPENAI/SMTP переменные при старте",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger("news_digest")
    try:
        with RunLock():
            require_secrets = args.require_secrets or not args.dry_run
            try:
                config, env = load_validated_config(
                    require_secrets=require_secrets and not args.dry_run
                )
            except ConfigError as exc:
                log.error("Конфигурация невалидна: %s", exc)
                return 2
            except Exception as exc:  # noqa: BLE001
                log.error("Не удалось загрузить конфигурацию: %s", exc)
                return 2

            lookback = args.since_hours or config.digest.lookback_hours
            log.info(
                "Конфиг OK: topics=%s sources=%s enabled=%s lookback=%sh model=%s dry_run=%s",
                len(config.topics),
                len(config.sources),
                len(config.enabled_sources()),
                lookback,
                env.openai_model,
                args.dry_run,
            )

            collected = collect_articles(config)
            filtered = filter_and_tag(collected, config, lookback_hours=lookback)
            state = prune_state(load_state())
            fresh = filter_unsent(filtered, state)
            selected = fresh[: config.digest.max_articles]
            summarized = summarize_articles(
                selected,
                env=env,
                digest=config.digest,
                enabled=not args.no_ai,
            )
            log.info(
                "Pipeline counts: collected=%s filtered=%s unsent=%s selected=%s",
                len(collected),
                len(filtered),
                len(fresh),
                len(summarized),
            )

            digest = render_digest(summarized, config)
            out_dir = ROOT / "output"
            out_dir.mkdir(parents=True, exist_ok=True)
            articles_path = out_dir / "articles.json"
            articles_path.write_text(
                json.dumps(
                    [article.to_dict() for article in summarized],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            html_path = save_digest_html(digest.html, out_dir / "digest.html")
            (out_dir / "digest.txt").write_text(digest.text, encoding="utf-8")
            log.info("Digest rendered title=%r html=%s", digest.title, html_path)

            if args.dry_run:
                log.info("Dry-run: email not sent, state not updated")
                return 0

            if not summarized:
                log.info("Нет статей для отправки; state не меняем")
                return 0

            try:
                send_digest(digest, env=env)
            except Exception as exc:  # noqa: BLE001
                log.error("SMTP failed, state not updated: %s", exc)
                return 1

            save_state(mark_sent(state, summarized))
            log.info("State updated with %s sent URLs", len(summarized))
            return 0
    except LockError as exc:
        log.error("%s", exc)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
