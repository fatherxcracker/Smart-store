"""Run Phase 4 reporting and its own copy of the store application."""

import importlib.util
import sys
from pathlib import Path

from config import Config


def create_app(config=None):
    root = Path(__file__).resolve().parent
    store = root / "store"
    if str(store) not in sys.path:
        sys.path.insert(0, str(store))
    for dependency in ("db", "cart", "checkout", "receipts", "notifications", "rfid_reader"):
        loaded = sys.modules.get(dependency)
        if loaded and not Path(loaded.__file__).resolve().is_relative_to(store):
            raise RuntimeError("Start Phase 4 in a fresh Python process so it uses only its own store modules.")
    name = "smartstore_phase4_store_app"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, store / "app.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    settings = {"DATABASE_PATH": str(Config.DATABASE_PATH),
                "REPORT_TIMEZONE": Config.REPORT_TIMEZONE, "PHASE4_ENABLED": True}
    settings.update(config or {})
    database_path = Path(settings["DATABASE_PATH"]).resolve()
    for phase in ("Phase 1", "Phase 2", "Phase 3"):
        if database_path.is_relative_to((root.parent / phase).resolve()):
            raise ValueError("Phase 4 must use its own database, not a previous phase's database.")
    settings["DATABASE_PATH"] = str(database_path)
    app = sys.modules[name].create_app(settings)
    from reports import report_pages
    app.register_blueprint(report_pages)
    return app


if __name__ == "__main__":
    create_app().run(host=Config.HOST, port=Config.PORT, debug=False)
