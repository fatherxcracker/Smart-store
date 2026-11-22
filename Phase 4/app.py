"""Run Phase 3 store workflows and Phase 4 reporting in one application."""

import importlib.util
import sys
from pathlib import Path

from config import Config


def create_app(config=None):
    phase3 = Path(__file__).resolve().parent.parent / "Phase 3"
    if str(phase3) not in sys.path:
        sys.path.insert(0, str(phase3))
    name = "smartstore_phase3_app"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, phase3 / "app.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    settings = {"DATABASE_PATH": str(Config.PHASE3_DATABASE_PATH),
                "REPORT_TIMEZONE": Config.REPORT_TIMEZONE, "PHASE4_ENABLED": True}
    settings.update(config or {})
    app = sys.modules[name].create_app(settings)
    from reports import report_pages
    app.register_blueprint(report_pages)
    return app


if __name__ == "__main__":
    create_app().run(host=Config.HOST, port=Config.PORT, debug=False)
