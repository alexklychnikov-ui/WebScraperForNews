from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests

from news_digest.config import resolve_proxy_url
from news_digest.models import ProxyMode, ProxySettings, Source, SourceProxyMode

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; WebScraperForNews/0.1; +https://localhost)"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, text/html;q=0.9, */*;q=0.8",
}


@dataclass
class FetchAttempt:
    via: str
    ok: bool
    status_code: int | None = None
    error: str | None = None
    elapsed_ms: int | None = None


@dataclass
class FetchResult:
    ok: bool
    url: str
    used_via: str
    status_code: int | None
    content: bytes | None
    text: str | None
    final_url: str | None
    attempts: list[FetchAttempt]
    error: str | None = None


def effective_proxy_mode(
    source_mode: SourceProxyMode,
    global_mode: ProxyMode,
) -> ProxyMode:
    if source_mode == "inherit":
        return global_mode
    return source_mode


def _proxy_map(proxy_url: str) -> dict[str, str]:
    return {"http": proxy_url, "https": proxy_url}


def _host(url: str) -> str:
    return urlparse(url).netloc or url


def fetch_url(
    url: str,
    *,
    proxy: ProxySettings,
    source_proxy_mode: SourceProxyMode = "inherit",
    method: str = "GET",
    timeout: int | None = None,
    headers: dict[str, str] | None = None,
    stream: bool = False,
    max_bytes: int = 2_000_000,
) -> FetchResult:
    mode = effective_proxy_mode(source_proxy_mode, proxy.mode)
    timeout = timeout or proxy.timeout_seconds
    request_headers = {**DEFAULT_HEADERS, **(headers or {})}
    proxy_url = resolve_proxy_url(proxy)

    plans: list[tuple[str, dict[str, str] | None]]
    if mode == "off":
        plans = [("direct", None)]
    elif mode == "always":
        plans = [("proxy", _proxy_map(proxy_url))]
    else:
        plans = [("direct", None), ("proxy", _proxy_map(proxy_url))]

    attempts: list[FetchAttempt] = []
    last_error: str | None = None

    for via, proxies in plans:
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=request_headers,
                proxies=proxies,
                timeout=timeout,
                stream=stream or True,
                allow_redirects=True,
            )
            elapsed_ms = int(response.elapsed.total_seconds() * 1000)
            if response.status_code >= 400:
                attempts.append(
                    FetchAttempt(
                        via=via,
                        ok=False,
                        status_code=response.status_code,
                        error=f"HTTP {response.status_code}",
                        elapsed_ms=elapsed_ms,
                    )
                )
                last_error = f"HTTP {response.status_code} via {via}"
                response.close()
                continue

            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    response.close()
                    raise ValueError(f"response larger than {max_bytes} bytes")
                chunks.append(chunk)
            content = b"".join(chunks)
            response.close()
            text = content.decode(response.encoding or "utf-8", errors="replace")
            attempts.append(
                FetchAttempt(
                    via=via,
                    ok=True,
                    status_code=response.status_code,
                    elapsed_ms=elapsed_ms,
                )
            )
            return FetchResult(
                ok=True,
                url=url,
                used_via=via,
                status_code=response.status_code,
                content=content,
                text=text,
                final_url=response.url,
                attempts=attempts,
            )
        except Exception as exc:  # noqa: BLE001 - collect attempt errors for UI
            message = f"{type(exc).__name__}: {exc}"
            attempts.append(FetchAttempt(via=via, ok=False, error=message))
            last_error = f"{via} failed for {_host(url)}: {message}"

    return FetchResult(
        ok=False,
        url=url,
        used_via="none",
        status_code=None,
        content=None,
        text=None,
        final_url=None,
        attempts=attempts,
        error=last_error or "all fetch attempts failed",
    )


def probe_source(source: Source, proxy: ProxySettings) -> dict[str, Any]:
    result = fetch_url(
        source.url,
        proxy=proxy,
        source_proxy_mode=source.proxy_mode,
        method="GET",
        max_bytes=512_000,
    )
    preview = (result.text or "")[:240].replace("\n", " ").strip()
    return {
        "source_id": source.id,
        "name": source.name,
        "url": source.url,
        "ok": result.ok,
        "used_via": result.used_via,
        "status_code": result.status_code,
        "final_url": result.final_url,
        "error": result.error,
        "preview": preview,
        "attempts": [
            {
                "via": attempt.via,
                "ok": attempt.ok,
                "status_code": attempt.status_code,
                "error": attempt.error,
                "elapsed_ms": attempt.elapsed_ms,
            }
            for attempt in result.attempts
        ],
        "effective_mode": effective_proxy_mode(source.proxy_mode, proxy.mode),
        "proxy_url": resolve_proxy_url(proxy),
    }
