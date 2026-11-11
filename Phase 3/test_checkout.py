"""Checkout regression tests. Uses isolated databases and never sends email.

Run: python -m unittest -v test_checkout
"""
import concurrent.futures
from contextlib import closing
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import app
import db
import receipts


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_db = db.DATABASE_PATH
        db.DATABASE_PATH = os.path.join(self.temp.name, "checkout.db")
        self.application = app.create_app()
        self.application.config.update(TESTING=True, SECRET_KEY="regression-tests")
        self.client = self.application.test_client()
        self.email = patch("receipts.send_receipt_email", return_value=None)
        self.email.start()
        self.addCleanup(self.email.stop)
        self.pid = db.add_product("Test item", "Test", 10, "900000000001", None, "Test producer")
        db.receive_stock(self.pid, 10)
        self.customer = db.create_customer("Private Name", "private@example.com", "secret123", phone="555-1234")

    def tearDown(self):
        db.DATABASE_PATH = self.original_db
        self.temp.cleanup()

    def add_barcode(self):
        response = self.client.post("/api/cart/barcode", json={"upc": "900000000001"})
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def checkout(self, client=None, **details):
        return (client or self.client).post("/api/checkout", json={"payment_method": "credit", **details})

    def purchase_count(self):
        with closing(db.get_connection()) as conn:
            return conn.execute("SELECT COUNT(*) FROM purchases").fetchone()[0]

    def test_stale_cookie_retry_returns_same_purchase(self):
        self.add_barcode()
        with self.client.session_transaction() as session:
            old_session = dict(session)
        second_client = self.application.test_client()
        with second_client.session_transaction() as session:
            session.update(old_session)
        details = {"membership_number": self.customer["membership_number"]}
        first = self.checkout(**details)
        second = self.checkout(second_client, **details)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json["purchase_id"], second.json["purchase_id"])
        self.assertEqual(self.purchase_count(), 1)
        self.assertEqual(db.get_product(self.pid)["in_stock"], 9)
        self.assertEqual(db.get_customer(self.customer["id"])["points"], 10)
        self.assertEqual(receipts.send_receipt_email.call_count, 1)

    def test_concurrent_database_retries_create_one_sale(self):
        def pay(_):
            return db.create_purchase([{"product_id": self.pid, "quantity": 1}],
                                      customer_id=self.customer["id"], checkout_key="same-cart")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            ids = list(pool.map(pay, range(2)))
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(self.purchase_count(), 1)
        self.assertEqual(db.get_customer(self.customer["id"])["points"], 10)

    def test_new_cart_can_purchase_again(self):
        self.add_barcode()
        first = self.checkout()
        self.add_barcode()
        second = self.checkout()
        self.assertNotEqual(first.json["purchase_id"], second.json["purchase_id"])
        self.assertEqual(self.purchase_count(), 2)

    def test_rfid_retry_returns_sale_even_after_tags_are_sold(self):
        db.register_product_tag(self.pid, "CC01")
        self.client.post("/api/cart/rfid", json={"epcs": ["CC01"]})
        second_client = self.application.test_client()
        with self.client.session_transaction() as session:
            old_session = dict(session)
        with second_client.session_transaction() as session:
            session.update(old_session)
        first = self.checkout()
        second = self.checkout(second_client)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json["purchase_id"], second.json["purchase_id"])
        self.assertEqual(self.purchase_count(), 1)

    def test_membership_card_does_not_expose_profile(self):
        self.add_barcode()
        receipts.send_receipt_email.return_value = {
            "event": "receipt_emailed", "message": "Sent to private@example.com",
            "message_en": "Sent to private@example.com", "message_fr": "private@example.com",
        }
        response = self.checkout(membership_number=self.customer["membership_number"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["receipt"]["customer"], {
            "membership_number": self.customer["membership_number"],
        })
        for secret in ("private@example.com", "555-1234", "Private Name", "checkout_key", "password_hash", "Total points"):
            self.assertNotIn(secret, response.get_data(as_text=True))

    def test_owner_receipt_uses_minimum_profile_fields(self):
        with self.client.session_transaction() as session:
            session["customer_id"] = self.customer["id"]
        self.add_barcode()
        response = self.checkout(membership_number=self.customer["membership_number"])
        self.assertEqual(set(response.json["receipt"]["customer"]), {"name", "membership_number", "points"})
        self.assertNotIn("private@example.com", response.get_data(as_text=True))

    def test_notification_failure_keeps_sale_successful(self):
        self.add_barcode()
        with patch("receipts.notify", side_effect=sqlite3.OperationalError("locked")), self.assertLogs(level="ERROR"):
            response = self.checkout()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["success"])
        self.assertEqual(response.json["notifications"][-1]["level"], "warning")
        self.assertEqual(self.purchase_count(), 1)
        self.assertEqual(self.client.get("/api/cart").json["cart"]["items"], [])

    def test_receipt_lookup_failure_after_commit_keeps_sale_successful(self):
        self.add_barcode()
        with patch("receipts.db.get_purchase", side_effect=sqlite3.OperationalError("locked")), self.assertLogs(level="ERROR"):
            response = self.checkout()
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json["receipt"])
        self.assertEqual(self.purchase_count(), 1)
        self.assertEqual(self.client.get("/api/cart").json["cart"]["items"], [])

    def test_email_failure_keeps_sale_successful(self):
        self.add_barcode()
        receipts.send_receipt_email.side_effect = RuntimeError("email service unavailable")
        with self.assertLogs(level="ERROR"):
            response = self.checkout(membership_number=self.customer["membership_number"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.purchase_count(), 1)
        self.assertEqual(response.json["notifications"][-1]["level"], "warning")

    def test_receipt_render_failure_keeps_sale_successful(self):
        self.add_barcode()
        with patch("receipts.build_receipt_html", side_effect=RuntimeError("render unavailable")), self.assertLogs(level="ERROR"):
            response = self.checkout(membership_number=self.customer["membership_number"])
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Private Name", response.json["receipt_html"])
        self.assertEqual(self.purchase_count(), 1)

    def test_tagged_stock_requires_rfid_before_payment(self):
        for index in range(10):
            db.register_product_tag(self.pid, f"AA{index:02X}")
        response = self.client.post("/api/cart/barcode", json={"upc": "900000000001"})
        self.assertEqual(response.status_code, 400)
        with self.client.session_transaction() as session:
            session["shopping_cart"] = {str(self.pid): 1}
        self.assertFalse(self.client.get("/api/cart").json["cart"]["can_checkout"])
        self.client.delete("/api/cart")
        response = self.client.post("/api/cart/rfid", json={"epcs": ["AA00"]})
        self.assertTrue(response.json["cart"]["can_checkout"])
        self.assertEqual(self.checkout().status_code, 200)

    def test_mixed_barcode_and_rfid_quantities(self):
        for index in range(9):
            db.register_product_tag(self.pid, f"BB{index:02X}")
        self.add_barcode()
        self.assertEqual(self.client.post("/api/cart/barcode", json={"upc": "900000000001"}).status_code, 400)
        scanned = self.client.post("/api/cart/rfid", json={"epcs": ["BB00", "BB01"]})
        self.assertTrue(scanned.json["cart"]["can_checkout"])
        self.assertEqual(scanned.json["cart"]["item_count"], 3)
        self.assertEqual(self.checkout().status_code, 200)

    def test_notifications_require_admin(self):
        self.assertEqual(self.client.get("/api/notifications").status_code, 403)
        with self.client.session_transaction() as session:
            session["customer_id"] = self.customer["id"]
        self.assertEqual(self.client.get("/api/notifications").status_code, 403)
        with closing(db.get_connection()) as conn:
            conn.execute("UPDATE customers SET is_admin = 1 WHERE id = ?", (self.customer["id"],))
            conn.commit()
        self.assertEqual(self.client.get("/api/notifications").status_code, 200)

    def test_language_preference_requires_owner_session(self):
        self.assertEqual(self.client.post("/api/account/language", json={"language": "fr"}).status_code, 401)
        with self.client.session_transaction() as session:
            session["customer_id"] = self.customer["id"]
        self.assertEqual(self.client.post("/api/account/language", json={"language": "fr"}).status_code, 200)
        self.assertEqual(db.get_customer(self.customer["id"])["language"], "fr")
        self.assertEqual(self.client.post("/api/account/language", json={"language": "xx"}).status_code, 400)

    def test_checkout_honors_selected_language(self):
        self.add_barcode()
        response = self.checkout(membership_number=self.customer["membership_number"], language="fr")
        self.assertIn("Paiement", response.json["receipt_html"])

    def test_nonfinite_prices_rejected(self):
        for price in ("inf", "-inf", "nan", "1e999"):
            with self.subTest(price=price), self.assertRaises(db.DatabaseError):
                db.add_product("Invalid", "Test", price, "invalid", None, "Test")

    def test_startup_migrates_existing_purchase_table(self):
        # Exercise the migration on a separate minimal legacy table.
        legacy = os.path.join(self.temp.name, "legacy.db")
        with closing(sqlite3.connect(legacy)) as conn:
            conn.execute("CREATE TABLE purchases (id INTEGER PRIMARY KEY, receipt_number TEXT, customer_id INTEGER, created_at TIMESTAMP)")
            conn.execute("INSERT INTO purchases (id, receipt_number) VALUES (1, 'legacy-receipt')")
            conn.commit()
        db.DATABASE_PATH = legacy
        db.init_db(seed=False)
        with closing(db.get_connection()) as conn:
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(purchases)")}
            self.assertEqual(conn.execute("SELECT receipt_number FROM purchases WHERE id = 1").fetchone()[0], "legacy-receipt")
        self.assertIn("checkout_key", columns)


if __name__ == "__main__":
    unittest.main()
