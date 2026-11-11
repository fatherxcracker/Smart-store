"""
Smart Store - Phase 3
Tests / demo for the database, receipts and notifications.
Uses a separate test database, so your real smartstore.db is never touched.

    python test_database.py            # run all checks (no email sent)
    python test_database.py --email you@gmail.com   # also send a real receipt email
"""

import os
import sys
import tempfile

# Use a throw-away database for the test run
TEST_DB = os.path.join(tempfile.gettempdir(), "smartstore_test.db")
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
os.environ["DATABASE_PATH"] = TEST_DB

import db
import receipts
from notifications import notify, notify_error

passed = 0


def check(label, condition):
    global passed
    if not condition:
        print(f"  FAIL  {label}")
        sys.exit(1)
    passed += 1
    print(f"  ok    {label}")


def expect_error(label, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except db.DatabaseError as error:
        check(f"{label} -> \"{error}\"", True)
        return str(error)
    check(label + " (expected an error)", False)


print("Database setup")
db.init_db()
inventory = db.get_inventory()
check("sample products loaded", len(inventory) == 5)
check("initial stock is 24 each", all(p["in_stock"] == 24 for p in inventory))

print("\nProduct management")
pid = db.add_product("Red Bull 250ml", "Beverage", "3.49", "611269991000", "e28011700000020a1b2c3d99", "Red Bull GmbH")
check("add product", db.get_product(pid)["name"] == "Red Bull 250ml")
check("EPC stored in upper case", db.get_product(pid)["epc"] == "E28011700000020A1B2C3D99")
expect_error("duplicate UPC rejected", db.add_product, "Copy", "Beverage", 1, "611269991000", None, "X")
expect_error("UPC over 13 chars rejected", db.add_product, "X", "Y", 1, "12345678901234", None, "Z")
expect_error("EPC over 24 chars rejected", db.add_product, "X", "Y", 1, "123", "A" * 25, "Z")
db.update_product(pid, "Red Bull 250ml", "Energy Drink", 3.99, "611269991000", "E28011700000020A1B2C3D99", "Red Bull GmbH")
check("edit product (new price + category)", db.get_product(pid)["price"] == 3.99)
check("find by barcode (UPC)", db.find_by_upc("611269991000")["id"] == pid)
check("find by RFID (EPC)", db.find_by_epc("E28011700000020A1B2C3D99")["id"] == pid)
found = db.find_by_epcs(["E28011700000020A1B2C3D01", "E28011700000020A1B2C3D02", "UNKNOWNTAG"])
check("find many RFID tags at once (unknown ignored)", len(found) == 2)

print("\nInventory (one product, many receptions)")
db.receive_stock(pid, 10, note="Invoice 1001")
db.receive_stock(pid, 6, note="Invoice 1002")
check("two receptions recorded", len(db.get_receptions(pid)) == 2)
check("total in stock = 16", db.get_product(pid)["in_stock"] == 16)
expect_error("receive 0 rejected", db.receive_stock, pid, 0)

print("\nCustomer accounts")
acct = db.create_customer("Kiara Bartuccio", "Kiara@Example.com", "secret123", language="fr")
check("membership number auto-generated", acct["membership_number"].startswith("SS-"))
expect_error("duplicate email rejected", db.create_customer, "K2", "kiara@example.com", "secret123")
check("login with right password", db.login_customer("kiara@example.com", "secret123") is not None)
check("login with wrong password fails", db.login_customer("kiara@example.com", "nope") is None)
check("password hash never returned", "password_hash" not in db.get_customer(acct["id"]))
check("lookup by membership card", db.find_customer_by_membership(acct["membership_number"])["id"] == acct["id"])

print("\nCheckout -> receipt")
coke = db.find_by_upc("123456789012")
chips = db.find_by_upc("123456789029")
cart = [{"product_id": coke["id"], "quantity": 2}, {"product_id": chips["id"], "quantity": 1},
        {"product_id": coke["id"], "quantity": 1}]  # coke scanned again -> merged
result = receipts.complete_checkout(cart, customer_id=acct["id"], lang="fr", send_email=False)
r = result["receipt"]
check("purchase saved with 2 lines (duplicates merged)", len(r["items"]) == 2)
check("subtotal = 3 x 2.49 + 4.99 = 12.46", r["subtotal"] == 12.46)
check("GST 5% = 0.62", r["gst"] == 0.62)
check("QST 9.975% = 1.24", r["qst"] == 1.24)
check("total = 14.32", r["total"] == 14.32)
check("points earned = 12 (1 per $1)", r["points_earned"] == 12)
check("points added to account", db.get_customer(acct["id"])["points"] == 12)
check("stock went down (Coke 24 -> 21)", db.get_product(coke["id"])["in_stock"] == 21)
check("receipt in purchase history", len(db.get_purchase_history(acct["id"])) == 1)
check("notifications in French", "Paiement" in result["notifications"][0]["message"])

old_price = r["items"][0]["unit_price"]
db.update_product(coke["id"], coke["name"], coke["category"], 9.99, coke["upc"], coke["epc"], coke["producer"])
check("old receipt keeps old price after price change",
      db.get_purchase(result["purchase_id"])["items"][0]["unit_price"] == old_price)

guest = receipts.complete_checkout([{"product_id": chips["id"], "quantity": 1}], lang="en", send_email=False)
check("guest checkout works, 0 points", guest["receipt"]["points_earned"] == 0 and guest["receipt"]["customer"] is None)

expect_error("can't buy more than in stock", db.create_purchase, [{"product_id": pid, "quantity": 999}])
expect_error("empty cart rejected", db.create_purchase, [])
check("failed checkout left no half receipt", len(db.get_purchase_history(acct["id"])) == 1)

db.delete_product(pid)
check("deleted product gone from inventory", db.get_product(pid) is None)
check("its UPC can be reused", db.add_product("Red Bull 2", "Energy Drink", 3.99, "611269991000", None, "Red Bull GmbH") > 0)

print("\nNotifications")
n = notify("product_added", "en", name="Coca-Cola 500ml")
check("English message", n["message"] == 'Product "Coca-Cola 500ml" added successfully.')
e = notify_error("A product with this UPC already exists.", "fr")
check("error translated to French", e["message"] == "Un produit avec ce CUP existe déjà." and not e["success"])
check("notifications logged in database", len(db.get_notifications()) > 0)

print("\nSample receipt (text version, French):\n")
print(receipts.build_receipt_text(db.get_purchase(result["purchase_id"])))

if "--email" in sys.argv:
    to = sys.argv[sys.argv.index("--email") + 1]
    print(f"\nSending a real receipt email to {to} ...")
    c = db.create_customer("Email Test", to, "secret123")
    out = receipts.complete_checkout([{"product_id": chips["id"], "quantity": 2}], customer_id=c["id"])
    print("  ->", out["notifications"][-1]["message"])

print(f"\nAll {passed} checks passed.")
