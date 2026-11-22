"""Paths and settings for the Phase 4 workspace."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5003"))
    # Reuse the existing store database for reports and checkout.
    PHASE3_DATABASE_PATH = Path(os.environ.get(
        "PHASE3_DATABASE_PATH", str(BASE_DIR.parent / "Phase 3" / "smartstore.db")
    ))
    # Future BLE observation storage, separate from store transactions.
    SENSOR_DATABASE_PATH = BASE_DIR / "database" / "sensors.db"
    MINEW_DEVICE_ADDRESS = os.environ.get("MINEW_DEVICE_ADDRESS", "")
    REPORT_TIMEZONE = os.environ.get("REPORT_TIMEZONE", "America/Toronto")
