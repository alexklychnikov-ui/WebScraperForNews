from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

load_dotenv(ROOT / ".env")

from news_digest.dashboard import create_app  # noqa: E402


def main() -> None:
    host = os.getenv("DASHBOARD_HOST", "127.0.0.1")
    port = int(os.getenv("DASHBOARD_PORT", "8765"))
    app = create_app()
    print(f"Dashboard: http://{host}:{port}")
    print(f"Config:    {ROOT / 'config' / 'sources.json'}")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
