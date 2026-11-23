"""Settings for the Phase 4 application (read from .env, see .env.example)."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
# Must run before db.py is imported: db.py reads DATABASE_PATH from the environment.
load_dotenv(BASE_DIR / ".env")


class Config:
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5003"))
    REPORT_TIMEZONE = os.environ.get("REPORT_TIMEZONE", "America/Toronto")
