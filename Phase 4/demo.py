"""Start a disposable, hardware-free Phase 4 demo on localhost."""

import argparse
from contextlib import closing
from datetime import datetime, time, timedelta, timezone
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from zoneinfo import ZoneInfo


SCAN_TAGS = ("E28011700000020A1B2C3DB1", "E28011700000020A1B2C3DB2")


def seed_demo(app):
    import db

    with app.app_context(), closing(db.get_connection()) as conn:
        customer = conn.execute("SELECT id FROM customers WHERE membership_number = ?", ("SS-00000002",)).fetchone()
        for upc, epc in zip(("123456789012", "123456789029"), SCAN_TAGS):
            product = conn.execute("SELECT id FROM products WHERE upc = ?", (upc,)).fetchone()
            db.receive_stock(product["id"], 1, note="Demo checkout stock", epcs=[epc])

        product_id = db.add_product("Demo Coffee", "Pantry", 4.99, "290000000019", None, "Demo")
        zone = ZoneInfo(app.config["REPORT_TIMEZONE"])
        today = datetime.now(zone).date()
        history = [(14, 9, 4.99), (2, 9, 5.49), (2, 15, 6.49)]
        for index, (days_ago, hour, price) in enumerate(history, start=1):
            db.update_product(product_id, "Demo Coffee", "Pantry", price, "290000000019", None, "Demo")
            epc = f"E28011700000020A1B2CFF{index:02X}"
            db.receive_stock(product_id, 1, note="Demo price history", epcs=[epc])
            purchase_id = db.create_purchase(
                [{"product_id": product_id, "quantity": 1}],
                customer_id=customer["id"],
                payment_method="cash",
                epcs=[epc],
            )
            local_stamp = datetime.combine(today - timedelta(days=days_ago), time(hour), zone)
            stamp = local_stamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            with conn:
                conn.execute("UPDATE purchases SET created_at = ? WHERE id = ?", (stamp, purchase_id))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5007, help="Local demo port (default: 5007).")
    args = parser.parse_args()

    # These settings are read when the app modules are imported.
    os.environ["RFID_SIMULATE"] = "1"
    os.environ["RFID_SIMULATED_TAGS"] = ",".join(SCAN_TAGS)
    os.environ["GPIOZERO_PIN_FACTORY"] = "mock"

    from app import create_app
    from sensors import record_reading
    from sensors.minew_msp01 import start_simulator

    with TemporaryDirectory(prefix="smart-store-demo-") as directory:
        app = create_app({"DATABASE_PATH": str(Path(directory) / "demo.sqlite3"),
                          "SEND_RECEIPT_EMAIL": False})
        seed_demo(app)
        stop = Event()
        simulator = start_simulator(app, record_reading, stop_event=stop)
        print(f"Demo ready at http://127.0.0.1:{args.port}. Restart to restore the sample data.", flush=True)
        try:
            app.run(host="127.0.0.1", port=args.port, use_reloader=False)
        finally:
            stop.set()
            simulator.join()


if __name__ == "__main__":
    main()
