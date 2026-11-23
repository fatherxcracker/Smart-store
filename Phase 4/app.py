"""Smart Store - Phase 4: the complete system in one application.

    Phase 2  fridge monitoring: DHT11 sensors -> MQTT -> email alert -> reply YES -> fan   (monitoring/)
    Phase 3  accounts, inventory, RFID stock, checkout, receipts, notifications           (storefront.py ...)
    Phase 4  dashboard, admin and customer reports, CSV export, dark mode,
             Minew MSP01 BLE sensor                                                        (reports/, sensors/)

Run:  python app.py      then open http://localhost:5003
"""

import config  # loads .env first (db.py reads its settings when imported)
from config import Config

import storefront
from monitoring import init_monitoring, monitor_shutdown
from reports import report_pages
from sensors import init_sensors


def create_app(overrides=None, start_services=False):
    """start_services=True also starts the MQTT, mailbox and BLE threads (real server only)."""
    # The database is Phase 4/smartstore.db unless DATABASE_PATH is set in .env (read by db.py).
    settings = {"REPORT_TIMEZONE": Config.REPORT_TIMEZONE,
                "PHASE4_ENABLED": True,
                "SESSION_COOKIE_SAMESITE": "Lax",   # blocks cross-site form posts
                "SESSION_COOKIE_HTTPONLY": True}
    settings.update(overrides or {})
    app = storefront.create_app(settings)
    app.register_blueprint(report_pages)
    init_monitoring(app, start_background=start_services)
    init_sensors(app, start_background=start_services)
    return app


if __name__ == "__main__":
    application = create_app(start_services=True)
    try:
        application.run(host=Config.HOST, port=Config.PORT, debug=False, use_reloader=False)
    finally:
        monitor_shutdown(application)
