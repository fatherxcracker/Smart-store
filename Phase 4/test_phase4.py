"""Phase 4 tests: fridge monitoring (Phase 2 inside the store), MSP01 sensor,
dashboard, CSV export, low-stock limits per category and shared navigation.
Isolated databases; no real email, MQTT broker, GPIO or Bluetooth."""
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
import db
from monitoring import Monitor, motor_control
from sensors import latest, record_reading
from sensors.minew_msp01 import decode_service_data


class Phase4Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = create_app({"DATABASE_PATH": str(Path(self.temp.name) / "p4.db"), "TESTING": True,
                               "SECRET_KEY": "phase4-tests", "ALERT_COOLDOWN_SECONDS": 300})
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.addCleanup(self.ctx.pop)
        self.client = self.app.test_client()
        self.monitor = self.app.extensions["monitor"]
        with closing(db.get_connection()) as conn:
            self.admin = conn.execute("SELECT id FROM customers WHERE is_admin=1").fetchone()[0]
        self.member = db.create_customer("Member One", "member1@example.com", "secret123")["id"]

    def login(self, user_id):
        with self.client.session_transaction() as session:
            session["customer_id"] = user_id


class FridgeMonitoringTests(Phase4Base):
    def test_pages_need_login_and_admin(self):
        for path in ("/monitoring/", "/monitoring/api/readings", "/sensors/", "/sensors/api/latest", "/reports/dashboard"):
            self.assertEqual(self.client.get(path).status_code, 401, path)
        self.login(self.member)
        for path in ("/monitoring/", "/monitoring/api/readings", "/sensors/", "/sensors/api/latest", "/reports/dashboard", "/reports/api/dashboard"):
            self.assertEqual(self.client.get(path).status_code, 403, path)
        self.assertEqual(self.client.post("/monitoring/api/fan/toggle").status_code, 403)

    def test_admin_pages_render(self):
        self.login(self.admin)
        for path in ("/monitoring/", "/sensors/", "/reports/dashboard", "/reports/inventory", "/reports/"):
            response = self.client.get(path, follow_redirects=True)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn(b"embedded.js", response.data, path)

    def test_warm_reading_creates_one_alert_and_email_with_cooldown(self):
        with patch.object(Monitor, "send_alert_email", return_value=True) as send:
            self.monitor.handle_reading(1, 9.5, 40)
            self.monitor.handle_reading(1, 9.8, 40)  # within cooldown: no second email
            self.monitor.handle_reading(2, 20, 40)    # other fridge has its own cooldown
        self.assertEqual(send.call_count, 2)
        conn = db.get_connection()
        count = conn.execute("SELECT COUNT(*) FROM fridge_alerts WHERE fridge_id=1").fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)

    def test_cool_reading_sends_nothing(self):
        with patch.object(Monitor, "send_alert_email", return_value=True) as send:
            self.monitor.handle_reading(1, 4.0, 40)
        send.assert_not_called()

    def alert(self, fridge=1, temperature=12.0):
        return self.monitor.create_alert(fridge, temperature)

    def test_yes_turns_fan_on_once_and_no_does_nothing(self):
        token = self.alert()
        with patch.object(motor_control, "fan_on") as fan_on:
            self.monitor.handle_alert_response(token, "yes", "email reply")
            self.monitor.handle_alert_response(token, "yes", "email reply")  # same alert again
        fan_on.assert_called_once()
        self.assertEqual(self.monitor.fan["status"], "ON")
        self.monitor.fan["status"] = "OFF"
        other = self.alert(2, 13.0)
        with patch.object(motor_control, "fan_on") as fan_on:
            self.monitor.handle_alert_response(other, "no", "email reply")
        fan_on.assert_not_called()
        self.assertEqual(self.monitor.fan["status"], "OFF")

    def test_email_link_works_without_login_and_rejects_unknown_tokens(self):
        token = self.alert()
        with patch.object(motor_control, "fan_on") as fan_on:
            self.assertEqual(self.client.get(f"/monitoring/alert/confirm?token={token}&action=yes").status_code, 200)
        fan_on.assert_called_once()
        self.assertEqual(self.client.get("/monitoring/alert/confirm?token=nope&action=yes").status_code, 404)

    def test_reply_parsing(self):
        parse = Monitor.parse_reply_answer
        self.assertEqual(parse("YES\n\nOn Mon wrote:\n> Reply YES"), "yes")
        self.assertEqual(parse("  yes please"), "yes")
        self.assertEqual(parse("Oui."), "yes")
        self.assertEqual(parse("No thanks"), "no")
        self.assertIsNone(parse("> Reply to this email with YES"))
        self.assertIsNone(parse("Maybe later"))
        self.assertIsNone(parse(""))

    def test_threshold_and_fan_api_validation(self):
        self.login(self.admin)
        self.assertEqual(self.client.post("/monitoring/api/thresholds/1", json={"threshold": "abc"}).status_code, 400)
        self.assertEqual(self.client.post("/monitoring/api/thresholds/1", json={"threshold": 500}).status_code, 400)
        self.assertEqual(self.client.post("/monitoring/api/thresholds/9", json={"threshold": 5}).status_code, 404)
        self.assertEqual(self.client.post("/monitoring/api/thresholds/1", json={"threshold": 6.5}).status_code, 200)
        self.assertEqual(self.client.get("/monitoring/api/thresholds").get_json()["1"], 6.5)
        self.assertEqual(self.client.post("/monitoring/api/fan/speed", json={"duty_cycle": 101}).status_code, 400)
        with patch.object(motor_control, "fan_on"), patch.object(motor_control, "fan_off"):
            self.assertEqual(self.client.post("/monitoring/api/fan/toggle").get_json()["status"], "ON")
            self.assertEqual(self.client.post("/monitoring/api/fan/toggle").get_json()["status"], "OFF")

    def test_readings_and_history_are_available_to_the_dashboard(self):
        self.monitor.history_seconds_override = 0
        with patch.object(Monitor, "send_alert_email", return_value=True):
            self.monitor.handle_reading(1, 6.0, 50)
        self.login(self.admin)
        readings = self.client.get("/monitoring/api/readings").get_json()
        self.assertEqual(readings["1"]["temperature"], 6.0)
        self.assertEqual(readings["1"]["status"], "normal")
        self.assertEqual(len(self.client.get("/monitoring/api/history/1").get_json()), 1)
        feed = self.client.get("/reports/api/dashboard").get_json()
        self.assertEqual(feed["fridges"]["readings"]["1"]["temperature"], 6.0)

    def test_fridge_events_reach_the_store_notification_log(self):
        with patch.object(Monitor, "send_alert_email", return_value=True):
            self.monitor.handle_reading(1, 15.0, 50)
        messages = [n["message_en"] for n in db.get_notifications(10)]
        self.assertTrue(any("Temperature alert" in m for m in messages))


class SensorTests(Phase4Base):
    def test_record_and_latest_combine_partial_readings(self):
        record_reading({"temperature": 21.5, "humidity": 40})
        record_reading({"light": 300, "motion": True, "battery": 90})
        data = latest()
        self.assertEqual(data["temperature"]["value"], 21.5)
        self.assertEqual(data["light"]["value"], 300)
        self.assertTrue(data["online"])
        self.assertEqual(data["motion_last_hour"], 1)
        self.assertIsNotNone(data["last_motion_seconds"])

    def test_empty_database_is_offline_not_an_error(self):
        data = latest()
        self.assertFalse(data["online"])
        self.assertIsNone(data["temperature"])

    def test_stale_sensor_is_offline(self):
        record_reading({"temperature": 20})
        conn = db.get_connection()
        conn.execute("UPDATE sensor_readings SET recorded_at = datetime('now', '-1 hour')")
        conn.commit(); conn.close()
        self.assertFalse(latest()["online"])

    def test_invalid_readings_are_rejected(self):
        for bad in ({}, {"temperature": "hot"}, {"temperature": 500}, {"humidity": 120}, {"light": -1},
                    {"motion": "maybe"}, {"temperature": True}, [], "x"):
            with self.assertRaises(ValueError, msg=str(bad)):
                record_reading(bad)

    def test_ingest_needs_token_or_admin(self):
        self.assertEqual(self.client.post("/sensors/api/ingest", json={"temperature": 20}).status_code, 401)
        with patch.dict("os.environ", {"SENSOR_INGEST_TOKEN": "s3cret"}):
            self.assertEqual(self.client.post("/sensors/api/ingest", json={"temperature": 20},
                                              headers={"X-Sensor-Token": "wrong"}).status_code, 401)
            self.assertEqual(self.client.post("/sensors/api/ingest", json={"temperature": 20, "motion": 1},
                                              headers={"X-Sensor-Token": "s3cret"}).status_code, 201)
            self.assertEqual(self.client.post("/sensors/api/ingest", json={"temperature": 999},
                                              headers={"X-Sensor-Token": "s3cret"}).status_code, 400)
        self.login(self.admin)
        self.assertEqual(self.client.get("/sensors/api/latest").get_json()["temperature"]["value"], 20)
        self.assertEqual(len(self.client.get("/sensors/api/history?hours=1").get_json()), 1)
        self.assertEqual(self.client.get("/reports/api/dashboard").get_json()["sensor"]["motion_last_hour"], 1)

    def test_minew_frame_decoder(self):
        frame = bytes([0xA1, 0x08, 87, 23, 128, 45, 0])  # 23.5 C, 45 %, battery 87
        self.assertEqual(decode_service_data(frame), {"battery": 87, "temperature": 23.5, "humidity": 45.0})
        self.assertEqual(decode_service_data(bytes([0xA1, 0x08, 50])), {"battery": 50})
        self.assertEqual(decode_service_data(b""), {})
        self.assertEqual(decode_service_data(bytes([0x10, 1, 2, 3, 4, 5, 6])), {})


class ReportFeatureTests(Phase4Base):
    def setUp(self):
        super().setUp()
        self.milk = db.add_product("Milk", "Dairy", 4, "888001", None, "Farm")
        self.gum = db.add_product("Gum", "Candy", 1.5, "888002", None, "Sweet Co")
        db.receive_stock(self.milk, 8, epcs=[f"C{i:04X}" for i in range(8)])
        db.receive_stock(self.gum, 8, epcs=[f"D{i:04X}" for i in range(8)])

    def levels(self):
        from reports import inventory
        conn = db.get_connection()
        try:
            return {p["name"]: p["stock_level"] for p in inventory.generate(conn)["products"]}
        finally:
            conn.close()

    def test_category_limit_changes_level_and_is_admin_only(self):
        self.login(self.member)
        self.assertEqual(self.client.post("/reports/inventory/limits", data={"category": "Dairy", "low_stock": "10"}).status_code, 403)
        self.login(self.admin)
        before = self.levels()
        self.assertEqual(before["Milk"], "moderate")          # 8 units, limit 5 -> below twice the limit
        response = self.client.post("/reports/inventory/limits", data={"category": "Dairy", "low_stock": "10"})
        self.assertEqual(response.status_code, 302)
        after = self.levels()
        self.assertEqual(after["Milk"], "low")                 # 8 < 10
        self.assertEqual(after["Gum"], "moderate")             # Candy keeps the default limit
        self.assertEqual(db.low_stock_limit("Dairy"), 10)

    def test_invalid_limits_are_refused(self):
        self.login(self.admin)
        for category, value in (("Nope", "5"), ("Dairy", "-1"), ("Dairy", "abc"), ("Dairy", "999999999")):
            response = self.client.post("/reports/inventory/limits", data={"category": category, "low_stock": value}, follow_redirects=True)
            self.assertIn(b"banner bad", response.data, (category, value))
        self.assertEqual(db.low_stock_limit("Dairy"), db.DEFAULT_LOW_STOCK)

    def test_checkout_low_stock_notice_uses_the_category_limit(self):
        import receipts
        tags = [t["epc"] for t in db.get_product_tags(self.milk)]
        db.set_category_threshold("Dairy", 8)
        # 8 -> 7 in stock: below this category's limit of 8, so the admin is warned
        result = receipts.complete_checkout([{"product_id": self.milk, "quantity": 1}], epcs=tags[:1], send_email=False)
        self.assertEqual(len(result["store_notifications"]), 1)
        # Gum keeps the default limit of 5: 8 -> 7 in stock is fine
        gum_tags = [t["epc"] for t in db.get_product_tags(self.gum)]
        result = receipts.complete_checkout([{"product_id": self.gum, "quantity": 1}], epcs=gum_tags[:1], send_email=False)
        self.assertEqual(result["store_notifications"], [])

    def test_csv_exports(self):
        tags = [t["epc"] for t in db.get_product_tags(self.milk)][:2]
        db.create_purchase([{"product_id": self.milk, "quantity": 2}], customer_id=self.member, epcs=tags)
        self.login(self.admin)
        for path, header in (("/reports/inventory?format=csv", "Product,Product ID"),
                             ("/reports/sales?format=csv", "Product,Product ID"),
                             ("/reports/sales?format=csv&table=daily", "Date,Orders"),
                             ("/reports/customers?format=csv", "Date,Customers"),
                             ("/reports/purchases?format=csv", "Date and time")):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertTrue(response.mimetype == "text/csv", path)
            self.assertIn("attachment", response.headers["Content-Disposition"])
            self.assertTrue(response.get_data(as_text=True).startswith("﻿" + header), path)
        self.assertIn("Milk", self.client.get("/reports/inventory?format=csv").get_data(as_text=True))

    def test_csv_neutralises_spreadsheet_formulas(self):
        from reports.exports import csv_response
        text = csv_response("x.csv", ["a"], [["=HYPERLINK(\"http://evil\")"], ["+1"], ["@x"], ["safe"]]).get_data(as_text=True)
        self.assertIn("'=HYPERLINK", text)
        self.assertIn("'+1", text)
        self.assertNotIn("\n=HYPERLINK", text)

    def test_member_csv_only_contains_own_purchases(self):
        other = db.create_customer("Other", "other@example.com", "secret123")["id"]
        tags = [t["epc"] for t in db.get_product_tags(self.gum)][:1]
        db.create_purchase([{"product_id": self.gum, "quantity": 1}], customer_id=other, epcs=tags)
        self.login(self.member)
        self.assertNotIn("Gum", self.client.get("/reports/purchases?format=csv").get_data(as_text=True))
        self.assertEqual(self.client.get("/reports/sales?format=csv").status_code, 403)
        self.assertEqual(self.client.get("/reports/inventory?format=csv").status_code, 403)

    def test_dashboard_numbers(self):
        tags = [t["epc"] for t in db.get_product_tags(self.milk)][:2]
        db.create_purchase([{"product_id": self.milk, "quantity": 2}], customer_id=self.member, epcs=tags)
        self.login(self.admin)
        data = self.client.get("/reports/api/dashboard").get_json()
        self.assertEqual(data["today"]["orders"], 1)
        self.assertEqual(data["today"]["customers"], 1)
        self.assertGreater(data["today"]["total"], 8)  # 2 x $4 plus tax
        self.assertEqual(len(data["week"]["daily"]), 7)

    def test_purchases_page_has_spending_chart(self):
        self.login(self.member)
        response = self.client.get("/reports/purchases")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Spending over time", response.data)
        self.assertIn(b'class="ss-top" role="banner"', response.data)
        self.assertIn(b'href="/account#dashboard">Back to dashboard</a>', response.data)
        self.assertIn(b'id="print-report"', response.data)

    def test_report_pages_offer_french(self):
        self.login(self.admin)
        for path in ("/reports/dashboard", "/reports/inventory", "/monitoring/", "/sensors/"):
            data = self.client.get(path).data
            for marker in (b"i18n.js", b'id="lang-fr"'):
                self.assertIn(marker, data, (path, marker))

    def test_every_dashboard_text_has_a_french_version(self):
        import re
        source = (Path(__file__).parent / "static" / "i18n.js").read_text(encoding="utf-8")
        for text in ("Sales today (incl. tax)", "Low-stock limit per category", "Fan control", "Inflation report: price history",
                     "Busiest days", "Motion events", "Download CSV", "Recent notifications"):
            self.assertIn('"' + text + '"', source, text)

    def test_admin_gets_one_page_dashboard_and_customers_do_not(self):
        self.login(self.admin)
        page = self.client.get("/reports/").data
        for marker in (b'id="stage"', b"shell.js", b'data-section="notifications"', b'data-section="fridges"',
                       b'data-section="users"', b'data-section="products"', b'data-section="sales"'):
            self.assertIn(marker, page, marker)
        menu = page.split(b'<aside class="side"', 1)[1].split(b'</aside>', 1)[0]
        self.assertEqual(menu.count(b'data-section='), 8)
        self.assertIn(b'data-section="sensor"', menu)
        self.assertIn(b'data-section="fridges"', menu)
        self.assertEqual(self.client.get("/reports/notifications").status_code, 200)
        self.login(self.member)
        response = self.client.get("/reports/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/reports/purchases"))
        self.assertEqual(self.client.get("/reports/notifications").status_code, 403)

    def test_every_page_carries_the_shared_sidebar(self):
        self.login(self.admin)
        for path in ("/", "/cart", "/inventory", "/admin/users", "/inventory/receive", "/inventory/receptions"):
            data = self.client.get(path).data
            self.assertIn(b"nav_shell.js", data, path)
            self.assertIn(b"nav_shell.css", data, path)
        shell = self.client.get("/reports/").data
        for marker in (b'class="ss-top"', b'class="ss-logo"', b'id="lang-fr"', b'id="logout"'):
            self.assertIn(marker, shell, marker)
        account = self.client.get("/").data
        for marker in (b'class="ss-top"', b'class="ss-logo"', b'id="account-nav"', b'data-page="history"'):
            self.assertIn(marker, account, marker)

    def test_embedded_mode_hooks_exist(self):
        root = Path(__file__).parent / "static"
        self.assertIn("embedded", (root / "embedded.js").read_text(encoding="utf-8"))
        self.assertIn("html.embedded .topbar", (root / "nav_shell.css").read_text(encoding="utf-8"))
        self.assertIn("html.embedded header", (root / "css" / "reports.css").read_text(encoding="utf-8"))

    def test_account_header_has_sign_in_and_checkout(self):
        data = self.client.get("/").data
        top_bar = data.split(b'<header class="ss-top">', 1)[1].split(b'</header>', 1)[0]
        self.assertIn(b'href="/cart" data-ss="checkout">Self-checkout</a>', top_bar)
        self.assertEqual(data.count(b'data-ss="checkout"'), 1)
        self.assertLess(top_bar.index(b'class="ss-logo"'), top_bar.index(b'data-ss="signIn"'))
        self.assertLess(top_bar.index(b'data-ss="signIn"'), top_bar.index(b'data-ss="checkout"'))
        for marker in (b'data-page="history"', b'data-page="profile"', b'data-ss="reports"'):
            self.assertIn(marker, top_bar)
        dashboard = data.split(b'id="dashboard-page"', 1)[1].split(b'</section>', 1)[0]
        self.assertIn(b'id="membership-number"', dashboard)
        self.assertIn(b'id="customer-points"', dashboard)
        self.assertNotIn(b'id="customer-email"', dashboard)
        for page in (b'history', b'profile'):
            section = data.split(b'id="' + page + b'-page"', 1)[1].split(b'</section>', 1)[0]
            self.assertIn(b'data-page="dashboard"', section)

    def test_store_and_report_pages_use_light_theme(self):
        self.login(self.admin)
        for path in ("/", "/cart", "/inventory", "/reports/", "/reports/dashboard", "/monitoring/", "/sensors/"):
            data = self.client.get(path).data
            for marker in (b"theme.js", b"theme.css", b'id="theme-toggle"'):
                self.assertNotIn(marker, data, path)


if __name__ == "__main__":
    unittest.main()
