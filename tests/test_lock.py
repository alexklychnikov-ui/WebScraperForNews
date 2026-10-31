from __future__ import annotations

from pathlib import Path

import pytest

from news_digest.lock import LockError, RunLock


def test_run_lock_exclusive(tmp_path: Path) -> None:
    lock_path = tmp_path / "run.lock"
    with RunLock(lock_path):
        with pytest.raises(LockError):
            RunLock(lock_path).acquire()
    # released
    with RunLock(lock_path):
        assert lock_path.exists()
    assert not lock_path.exists()
