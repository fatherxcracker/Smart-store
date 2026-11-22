"""Phase 4 entry point. Reporting and BLE integration will be added here."""

from flask import Flask, render_template

from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    @app.get("/")
    def home():
        return render_template("index.html")

    # Register authenticated reporting routes as they are implemented.
    # Integrate Phase 3 accounts before exposing any customer or admin data.
    return app


if __name__ == "__main__":
    create_app().run(host=Config.HOST, port=Config.PORT, debug=False)
