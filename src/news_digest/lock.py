from __future__ import annotations

import atexit
import os
from pathlib import Path

from news_digest.config import ROOT_DIR

DEFAULT_LOCK_PATH = ROOT_DIR / "data" / "run.lock"


class LockError(RuntimeError):
    """Another instance is already running."""


class RunLock:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DEFAULT_LOCK_PATH
        self._held = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise LockError(f"Already running: {self.path}") from exc
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        self._held = True
        atexit.register(self.release)

    def release(self) -> None:
        if not self._held:
            return
        try:
            self.path.unlink(missing_ok=True)
        finally:
            self._held = False

    def __enter__(self) -> RunLock:
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
