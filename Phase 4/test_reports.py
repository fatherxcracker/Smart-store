"""Integration tests using isolated databases, no real email or hardware."""
import csv
from datetime import datetime
from io import StringIO
import sqlite3
from zoneinfo import ZoneInfo
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = create_app({"DATABASE_PATH": str(Path(self.temp.name) / "test.db"),
                               "TESTING": True, "SECRET_KEY": "report-tests"})
        self.context = self.app.app_context()
        self.context.push()
        self.addCleanup(self.context.pop)
        import db
        self.db = db
        self.client = self.app.test_client()
        with db.get_connection() as conn:
            self.admin = conn.execute("SELECT id FROM customers WHERE is_admin=1").fetchone()[0]
            self.member = conn.execute("SELECT id FROM customers WHERE is_admin=0").fetchone()[0]
            conn.execute("UPDATE customers SET points=100 WHERE id=?", (self.member,))
        conn.close()
        self.other = db.create_customer("Other Person", "other@example.com", "secret123")["id"]
        self.tea = db.add_product("Tea", "Pantry", 10, "999001", None, "Test")
        self.coffee = db.add_product("Coffee", "Pantry", 5, "999002", None, "Test")
        db.receive_stock(self.tea, 20, epcs=[f"A{i:04X}" for i in range(20)])
        db.receive_stock(self.coffee, 20, epcs=[f"B{i:04X}" for i in range(20)])
        self.before = self.sale(self.member, [(self.tea, 1)], "2026-10-31 16:00:00")
        self.first = self.sale(self.member, [(self.tea, 2)], "2026-11-01 15:00:00", 20)
        self.second = self.sale(self.other, [(self.tea, 1), (self.coffee, 1)], "2026-11-02 15:00:00")
        self.third = self.sale(self.member, [(self.tea, 1)], "2026-11-02 17:00:00")
        self.guest = self.sale(None, [(self.coffee, 1)], "2026-11-03 15:00:00")
        self.db.update_product(self.tea, "Tea changed", "Pantry", 99, "999001", None, "Test")

    def sale(self, customer, items, timestamp, points=0):
        tags = []
        for pid, qty in items:
            tags.extend([tag["epc"] for tag in self.db.get_product_tags(pid) if tag["sold_purchase_id"] is None][:qty])
        purchase = self.db.create_purchase([{"product_id": pid, "quantity": qty} for pid, qty in items],
                                           customer_id=customer, points_redeemed=points, epcs=tags)
        conn = self.db.get_connection()
        try:
            conn.execute("UPDATE purchases SET created_at=? WHERE id=?", (timestamp, purchase))
            conn.commit()
        finally:
            conn.close()
        return purchase

    def login(self, user=None):
        with self.client.session_transaction() as session:
            session["customer_id"] = user or self.admin

    def request_context(self, path="/reports/sales?start=2026-11-01&end=2026-11-05"):
        return self.app.test_request_context(path)

    def test_all_report_pages_require_authentication(self):
        for page in ("inventory", "sales", "customers", "purchases"):
            self.assertEqual(self.client.get("/reports/" + page).status_code, 401)
        self.assertEqual(self.client.get("/reports/").status_code, 302)

    def test_member_cannot_open_admin_reports(self):
        self.login(self.member)
        for page in ("inventory", "sales", "customers"):
            self.assertEqual(self.client.get("/reports/" + page).status_code, 403)
        response = self.client.get("/reports/purchases?start=2026-11-01&end=2026-11-05")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Other Person", response.data)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    def test_admin_pages_and_store_workflows_render(self):
        self.login()
        for page in ("/", "/cart", "/inventory", "/reports/inventory", "/reports/sales", "/reports/customers", "/reports/purchases"):
            with self.subTest(page=page):
                self.assertEqual(self.client.get(page).status_code, 200)
        self.assertIn(b"/reports/", self.client.get("/").data)
        for asset in ("css/reports.css", "js/reports.js"):
            with self.client.get("/reports/assets/" + asset) as response:
                self.assertEqual(response.status_code, 200)

    def test_sales_preserve_historical_prices_and_do_not_duplicate_totals(self):
        from reports.common import Period, snapshot
        from reports.sales import generate
        with self.request_context(), snapshot() as conn:
            data = generate(conn, Period())
        tea = next(p for p in data["products"] if p["id"] == self.tea)
        self.assertEqual(tea["units"], 4)
        self.assertEqual(tea["gross"], 40)
        self.assertEqual(data["orders"], 4)
        self.assertEqual(data["units"], 6)
        self.assertEqual(data["totals"]["subtotal"], 50)
        self.assertEqual(data["totals"]["net_sales"], 48)
        self.assertEqual(data["totals"]["points_discount"], 2)
        self.assertEqual(data["totals"]["total"], 55.2)
        self.assertEqual(sum(day["orders"] for day in data["daily"]), 4)
        self.assertEqual(data["daily"][-1]["total"], 0)

    def test_rankings_include_zero_sales_and_historical_deleted_products(self):
        from reports.common import Period, snapshot
        from reports.sales import generate
        self.db.delete_product(self.tea)
        with self.request_context(), snapshot() as conn:
            data = generate(conn, Period(), 1)
        self.assertEqual(data["top"][0]["id"], self.tea)
        self.assertEqual(data["bottom"][0]["units"], 0)
        self.assertFalse(data["top"][0]["is_active"])

    def test_customers_are_distinct_and_guest_orders_are_separate(self):
        from reports.common import Period, snapshot
        from reports.customers import generate
        with self.request_context(), snapshot() as conn:
            data = generate(conn, Period())
        self.assertEqual(data["total_customers"], 2)
        self.assertEqual(data["new_customers"], 1)
        self.assertEqual(data["returning_customers"], 1)
        self.assertEqual(data["guest_orders"], 1)
        self.assertEqual([d["date"] for d in data["busiest"]], ["2026-11-02"])
        self.assertEqual([d["date"] for d in data["quietest"]], ["2026-11-03", "2026-11-04", "2026-11-05"])

    def test_personal_filters_and_price_history_cannot_leak_other_accounts(self):
        from reports.common import Period, snapshot
        from reports.purchases import generate
        with self.request_context(), snapshot() as conn:
            data = generate(conn, Period(), self.member, "tea", self.tea)
        self.assertEqual(data["receipt_count"], 2)
        self.assertEqual(data["purchase_times"], 2)
        self.assertEqual(data["units"], 3)
        self.assertEqual(data["total_spent"], 32.2)
        self.assertEqual([(point["date"][:10], point["price"]) for point in data["price_history"]],
                         [("2026-10-31", 10), ("2026-11-01", 10), ("2026-11-02", 10)])
        self.assertEqual({r["id"] for r in data["receipts"]}, {self.first, self.third})
        self.login(self.member)
        page = self.client.get(f"/reports/purchases?start=2026-11-01&end=2026-11-05&customer_id={self.other}")
        self.assertNotIn(self.db.get_purchase(self.second)["receipt_number"].encode(), page.data)

    def test_simulated_checkout_updates_inventory_sales_and_customer_receipt(self):
        admin = self.client
        self.login()
        customer = self.app.test_client()
        with customer.session_transaction() as session:
            session["customer_id"] = self.member
        membership = self.db.get_customer(self.member)["membership_number"]
        products = (self.tea, self.coffee)
        tags = [next(tag["epc"] for tag in self.db.get_product_tags(product_id)
                     if tag["sold_purchase_id"] is None) for product_id in products]
        day = datetime.now(ZoneInfo(self.app.config["REPORT_TIMEZONE"])).date()
        period = f"start={day}&end={day}"

        def rows(client, url):
            response = client.get(url)
            self.assertEqual(response.status_code, 200)
            content = response.data.decode("utf-8-sig")
            return list(csv.DictReader(StringIO(content)))

        def quantities(url, field):
            return {int(row["Product ID"]): int(row[field]) for row in rows(admin, url)
                    if int(row["Product ID"]) in products}

        inventory_url = "/reports/inventory?format=csv"
        sales_url = f"/reports/sales?{period}&format=csv"
        stock_before = quantities(inventory_url, "Available quantity")
        sold_before = quantities(sales_url, "Sold quantity")

        with patch("rfid_reader.SIMULATE", True), patch("rfid_reader.SIMULATED_TAGS", tags):
            scan = customer.post("/api/cart/rfid/scan", json={"manual": True})
        self.assertEqual(scan.status_code, 200)
        self.assertEqual(scan.json["cart"]["item_count"], 2)
        with patch("receipts.send_receipt_email") as send_email:
            self.app.config["SEND_RECEIPT_EMAIL"] = False
            checkout = customer.post("/api/checkout", json={"payment_method": "cash",
                                                            "membership_number": membership})
            send_email.assert_not_called()
        self.assertEqual(checkout.status_code, 200)
        self.assertEqual(checkout.json["cart"]["item_count"], 0)
        receipt = checkout.json["receipt"]["receipt_number"]
        history = customer.get("/api/account/history").json
        self.assertIn(receipt, [entry["receipt_number"] for entry in history])
        purchased = [row for row in rows(customer, f"/reports/purchases?{period}&format=csv")
                     if row["Receipt"] == receipt]
        self.assertCountEqual([(row["Product"], int(row["Quantity"])) for row in purchased],
                              [(self.db.get_product(product_id)["name"], 1) for product_id in products])
        self.assertEqual(quantities(inventory_url, "Available quantity"),
                         {product_id: stock_before[product_id] - 1 for product_id in products})
        self.assertEqual(quantities(sales_url, "Sold quantity"),
                         {product_id: sold_before[product_id] + 1 for product_id in products})

    def test_inventory_changes_after_purchase_and_filters_category(self):
        from reports.common import snapshot
        from reports.inventory import generate
        with snapshot() as conn:
            before = generate(conn, "Pantry")
        self.assertEqual({p["id"] for p in before["products"]}, {self.tea, self.coffee})
        self.assertEqual(next(p for p in before["products"] if p["id"] == self.tea)["in_stock"], 15)
        self.sale(None, [(self.tea, 1)], "2026-11-03 16:00:00")
        with snapshot() as conn:
            after = generate(conn, "Pantry")
        self.assertEqual(after["units"], before["units"] - 1)

    def test_price_chart_records_price_changes_at_purchase_time(self):
        from reports.common import Period, snapshot
        from reports.purchases import generate
        self.sale(self.member, [(self.tea, 1)], "2026-11-04 16:00:00")
        with self.request_context(), snapshot() as conn:
            data = generate(conn, Period(), self.member, product_id=self.tea)
        self.assertEqual([point["price"] for point in data["price_history"]], [10, 10, 10, 99])
        self.login(self.member)
        page = self.client.get(f"/reports/purchases?start=2026-11-04&end=2026-11-04&product_id={self.tea}")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'data-time-axis="true"', page.data)
        self.assertIn(b'View price history table', page.data)
        old_purchase = data["price_history"][0]["date"][:16].replace("T", " ")
        self.assertIn(old_purchase.encode(), page.data)

    def test_empty_period_has_zero_totals_and_no_personal_receipts(self):
        from reports.common import Period, snapshot
        from reports import sales, customers, purchases
        with self.request_context("/reports/sales?start=2026-09-01&end=2026-09-02"), snapshot() as conn:
            period = Period()
            self.assertEqual(sales.generate(conn, period)["totals"]["total"], 0)
            activity = customers.generate(conn, period)
            self.assertEqual(activity["total_customers"], 0)
            self.assertEqual(len(activity["quietest"]), 2)
            self.assertEqual(purchases.generate(conn, period, self.member)["receipts"], [])

    def test_single_day_dst_uses_25_hour_local_day(self):
        from reports.common import Period
        with self.request_context("/reports/sales?start=2026-11-01&end=2026-11-01"):
            period = Period()
        self.assertEqual(period.bounds, ("2026-11-01 04:00:00", "2026-11-02 05:00:00"))
        self.assertEqual(period.local_day("2026-11-02 04:59:59"), "2026-11-01")

    def test_date_boundaries_are_inclusive_for_day_exclusive_for_next_day(self):
        from reports.common import Period, snapshot
        from reports.sales import generate
        self.sale(None, [(self.coffee, 1)], "2026-11-01 04:00:00")
        self.sale(None, [(self.coffee, 1)], "2026-11-02 04:59:59")
        self.sale(None, [(self.coffee, 1)], "2026-11-02 05:00:00")
        with self.request_context("/reports/sales?start=2026-11-01&end=2026-11-01"), snapshot() as conn:
            data = generate(conn, Period())
        self.assertEqual(data["orders"], 3)

    def test_invalid_filters_return_readable_400(self):
        self.login()
        for query in ("start=bad", "start=2026-11-10&end=2026-11-01", "start=2020-01-01&end=2026-11-01", "limit=0", "limit=bad", "start=2026-11-01&end=9999-12-31"):
            with self.subTest(query=query):
                response = self.client.get("/reports/sales?" + query)
                self.assertEqual(response.status_code, 400)
                self.assertIn(b"Check your filters", response.data)

    def test_read_snapshot_does_not_allow_writes(self):
        from reports.common import snapshot
        with snapshot() as conn, self.assertRaises(sqlite3.OperationalError):
            conn.execute("DELETE FROM purchases")

    def test_two_applications_keep_database_paths_separate(self):
        other = create_app({"DATABASE_PATH": str(Path(self.temp.name) / "second.db"), "TESTING": True})
        with other.app_context():
            self.assertIsNone(self.db.find_by_upc("999001"))
        self.assertIsNotNone(self.db.find_by_upc("999001"))

    def test_login_route_uses_shared_session(self):
        response = self.client.post("/api/account/login", json={"email":"other@example.com", "password":"secret123"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/reports/purchases").status_code, 200)
        self.client.post("/api/account/logout")
        self.assertEqual(self.client.get("/reports/purchases").status_code, 401)


if __name__ == "__main__":
    unittest.main()
