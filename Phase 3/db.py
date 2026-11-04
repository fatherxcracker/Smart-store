"""
Smart Store - Phase 3
Database layer (SQLite). Every other part of the project (admin pages,
self-checkout, customer accounts, receipts) calls these functions instead of
writing SQL directly, so the whole group works against the same schema.

    import db
    db.init_db()                      # creates smartstore.db + tables (safe to run every start)
    db.add_product(name=..., ...)     # products
    db.receive_stock(product_id, 24)  # inventory
    db.create_customer(...)           # accounts
    db.create_purchase(cart, ...)     # checkout -> receipt
"""

import os
import secrets
import sqlite3
from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "smartstore.db"))
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")
SEED_PATH = os.path.join(BASE_DIR, "database", "seed.sql")

# Quebec sales taxes
GST_RATE = 0.05
QST_RATE = 0.09975

# Loyalty strategy: 1 point for every full dollar of the subtotal (before tax).
POINTS_PER_DOLLAR = 1


class DatabaseError(Exception):
    """Raised with a user-friendly message (e.g. 'UPC already exists')."""


# ---------------------------------------------------------------------------
# Connection / setup
# ---------------------------------------------------------------------------
def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(seed=True):
    """Create all tables and the inventory view. Adds sample products the
    first time if seed=True. Safe to call every time the app starts."""
    conn = get_connection()
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    if seed and conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        with open(SEED_PATH, encoding="utf-8") as f:
            conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"[database] Ready at {DATABASE_PATH}")


def _rows(rows):
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Products (admin: register / edit / delete)
# ---------------------------------------------------------------------------
def _validate_product(name, category, price, upc, epc, producer):
    if not name or not category or not producer:
        raise DatabaseError("Name, category and producer are required.")
    try:
        price = round(float(price), 2)
    except (TypeError, ValueError):
        raise DatabaseError("Price must be a number.")
    if price < 0:
        raise DatabaseError("Price can't be negative.")
    upc = (upc or "").strip()
    epc = (epc or "").strip().upper() or None
    if not upc or len(upc) > 13:
        raise DatabaseError("UPC is required and must be at most 13 characters.")
    if epc and len(epc) > 24:
        raise DatabaseError("EPC must be at most 24 characters.")
    return price, upc, epc


def add_product(name, category, price, upc, epc, producer, image_url=None, expiry_date=None):
    price, upc, epc = _validate_product(name, category, price, upc, epc, producer)
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO products (name, category, price, upc, epc, producer, image_url, expiry_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name.strip(), category.strip(), price, upc, epc, producer.strip(), image_url, expiry_date),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError as error:
        raise DatabaseError(_duplicate_message(error))
    finally:
        conn.close()


def update_product(product_id, name, category, price, upc, epc, producer, image_url=None, expiry_date=None):
    price, upc, epc = _validate_product(name, category, price, upc, epc, producer)
    conn = get_connection()
    try:
        cur = conn.execute(
            """UPDATE products
               SET name = ?, category = ?, price = ?, upc = ?, epc = ?, producer = ?,
                   image_url = ?, expiry_date = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ? AND is_active = 1""",
            (name.strip(), category.strip(), price, upc, epc, producer.strip(),
             image_url, expiry_date, product_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise DatabaseError("Product not found.")
    except sqlite3.IntegrityError as error:
        raise DatabaseError(_duplicate_message(error))
    finally:
        conn.close()


def delete_product(product_id):
    """Soft delete: the product disappears from the store and inventory, but
    old receipts that contain it stay intact. Its UPC/EPC are freed so they
    can be reused by a new product."""
    conn = get_connection()
    cur = conn.execute(
        """UPDATE products
           SET is_active = 0,
               upc = 'DEL' || id,
               epc = NULL,
               updated_at = CURRENT_TIMESTAMP
           WHERE id = ? AND is_active = 1""",
        (product_id,),
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise DatabaseError("Product not found.")


def _duplicate_message(error):
    text = str(error)
    if "products.upc" in text:
        return "A product with this UPC already exists."
    if "products.epc" in text:
        return "A product with this EPC already exists."
    return "This product conflicts with an existing one."


def get_product(product_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM inventory WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def find_by_upc(upc):
    """Barcode scanner lookup."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM inventory WHERE upc = ?", ((upc or "").strip(),)).fetchone()
    conn.close()
    return dict(row) if row else None


def find_by_epc(epc):
    """RFID reader lookup."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM inventory WHERE epc = ?", ((epc or "").strip().upper(),)).fetchone()
    conn.close()
    return dict(row) if row else None


def find_by_epcs(epcs):
    """Look up many RFID tags at once (all items scanned simultaneously).
    Returns {epc: product_dict}; unknown tags are simply left out."""
    epcs = [e.strip().upper() for e in epcs if e and e.strip()]
    if not epcs:
        return {}
    conn = get_connection()
    placeholders = ",".join("?" for _ in epcs)
    rows = conn.execute(f"SELECT * FROM inventory WHERE epc IN ({placeholders})", epcs).fetchall()
    conn.close()
    return {r["epc"]: dict(r) for r in rows}


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------
def receive_stock(product_id, quantity, note=None, received_at=None):
    """Record a reception (quantity + date received)."""
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        raise DatabaseError("Quantity must be a whole number.")
    if quantity <= 0:
        raise DatabaseError("Quantity must be greater than 0.")
    if not get_product(product_id):
        raise DatabaseError("Product not found.")
    conn = get_connection()
    if received_at:
        cur = conn.execute(
            "INSERT INTO receptions (product_id, quantity, note, received_at) VALUES (?, ?, ?, ?)",
            (product_id, quantity, note, received_at),
        )
    else:
        cur = conn.execute(
            "INSERT INTO receptions (product_id, quantity, note) VALUES (?, ?, ?)",
            (product_id, quantity, note),
        )
    conn.commit()
    conn.close()
    return cur.lastrowid


def get_inventory():
    """Everything the inventory dashboard needs: one row per product with
    total_received, total_sold and in_stock."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM inventory ORDER BY category, name").fetchall()
    conn.close()
    return _rows(rows)


def get_receptions(product_id=None):
    conn = get_connection()
    sql = """SELECT r.*, p.name AS product_name
             FROM receptions r JOIN products p ON p.id = r.product_id"""
    if product_id:
        rows = conn.execute(sql + " WHERE r.product_id = ? ORDER BY r.received_at DESC", (product_id,)).fetchall()
    else:
        rows = conn.execute(sql + " ORDER BY r.received_at DESC").fetchall()
    conn.close()
    return _rows(rows)


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
def _new_membership_number(conn):
    while True:
        number = f"SS-{secrets.randbelow(10**8):08d}"
        if not conn.execute("SELECT 1 FROM customers WHERE membership_number = ?", (number,)).fetchone():
            return number


def create_customer(name, email, password, phone=None, language="en"):
    if not name or not email or not password:
        raise DatabaseError("Name, email and password are required.")
    if "@" not in email:
        raise DatabaseError("Enter a valid email address.")
    if len(password) < 6:
        raise DatabaseError("Password must be at least 6 characters.")
    conn = get_connection()
    try:
        number = _new_membership_number(conn)
        cur = conn.execute(
            """INSERT INTO customers (name, email, phone, membership_number, password_hash, language)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name.strip(), email.strip().lower(), phone, number,
             generate_password_hash(password), language if language in ("en", "fr") else "en"),
        )
        conn.commit()
        return {"id": cur.lastrowid, "membership_number": number}
    except sqlite3.IntegrityError:
        raise DatabaseError("An account with this email already exists.")
    finally:
        conn.close()


def _public_customer(row):
    if not row:
        return None
    data = dict(row)
    data.pop("password_hash", None)  # never send the hash to the browser
    return data


def login_customer(email, password):
    """Returns the customer (without password) or None if wrong email/password."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM customers WHERE email = ?", ((email or "").strip().lower(),)).fetchone()
    conn.close()
    if row and check_password_hash(row["password_hash"], password or ""):
        return _public_customer(row)
    return None


def get_customer(customer_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    conn.close()
    return _public_customer(row)


def find_customer_by_membership(membership_number):
    """Used at checkout when the customer scans/types their membership card."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM customers WHERE membership_number = ?", ((membership_number or "").strip().upper(),)
    ).fetchone()
    conn.close()
    return _public_customer(row)


def get_purchase_history(customer_id):
    """List of past receipts for the customer account page (newest first)."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.*, COUNT(i.id) AS line_count, COALESCE(SUM(i.quantity), 0) AS item_count
           FROM purchases p LEFT JOIN purchase_items i ON i.purchase_id = p.id
           WHERE p.customer_id = ?
           GROUP BY p.id ORDER BY p.created_at DESC, p.id DESC""",
        (customer_id,),
    ).fetchall()
    conn.close()
    return _rows(rows)


# ---------------------------------------------------------------------------
# Checkout -> purchase (receipt)
# ---------------------------------------------------------------------------
def calculate_totals(subtotal):
    subtotal = round(subtotal, 2)
    gst = round(subtotal * GST_RATE, 2)
    qst = round(subtotal * QST_RATE, 2)
    total = round(subtotal + gst + qst, 2)
    points = int(subtotal) * POINTS_PER_DOLLAR
    return {"subtotal": subtotal, "gst": gst, "qst": qst, "total": total, "points_earned": points}


def create_purchase(cart, customer_id=None, payment_method="card"):
    """Turn the confirmed shopping list into a receipt.

    cart = [{"product_id": 1, "quantity": 2}, ...]
    Checks stock, saves the purchase + its items with the CURRENT price,
    adds points to the customer, all in ONE transaction (so a failure
    never leaves half a receipt). Returns the purchase id.
    """
    # Merge duplicate lines (e.g. same product scanned twice)
    quantities = {}
    for line in cart or []:
        pid = int(line["product_id"])
        qty = int(line.get("quantity", 1))
        if qty <= 0:
            raise DatabaseError("Quantities must be greater than 0.")
        quantities[pid] = quantities.get(pid, 0) + qty
    if not quantities:
        raise DatabaseError("The shopping list is empty.")

    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")  # lock so two checkouts can't oversell

        lines = []
        subtotal = 0.0
        for pid, qty in quantities.items():
            product = conn.execute("SELECT * FROM inventory WHERE id = ?", (pid,)).fetchone()
            if not product:
                raise DatabaseError(f"Product #{pid} is no longer available.")
            if product["in_stock"] < qty:
                raise DatabaseError(f"Only {product['in_stock']} '{product['name']}' left in stock.")
            line_total = round(product["price"] * qty, 2)
            subtotal += line_total
            lines.append((pid, product["name"], qty, product["price"], line_total))

        if customer_id is not None and not conn.execute(
            "SELECT 1 FROM customers WHERE id = ?", (customer_id,)
        ).fetchone():
            raise DatabaseError("Customer not found.")

        totals = calculate_totals(subtotal)
        if customer_id is None:
            totals["points_earned"] = 0  # guests don't earn points

        receipt_number = f"R-{datetime.now():%Y%m%d}-{secrets.token_hex(3).upper()}"
        cur = conn.execute(
            """INSERT INTO purchases (receipt_number, customer_id, subtotal, gst, qst, total,
                                      points_earned, payment_method)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (receipt_number, customer_id, totals["subtotal"], totals["gst"], totals["qst"],
             totals["total"], totals["points_earned"], payment_method),
        )
        purchase_id = cur.lastrowid

        conn.executemany(
            """INSERT INTO purchase_items (purchase_id, product_id, product_name, quantity, unit_price, line_total)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [(purchase_id, *line) for line in lines],
        )

        if customer_id is not None and totals["points_earned"]:
            conn.execute(
                "UPDATE customers SET points = points + ? WHERE id = ?",
                (totals["points_earned"], customer_id),
            )

        conn.commit()
        return purchase_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_purchase(purchase_id):
    """A full receipt: purchase info + items + customer (if any)."""
    conn = get_connection()
    purchase = conn.execute("SELECT * FROM purchases WHERE id = ?", (purchase_id,)).fetchone()
    if not purchase:
        conn.close()
        return None
    items = conn.execute(
        "SELECT * FROM purchase_items WHERE purchase_id = ? ORDER BY id", (purchase_id,)
    ).fetchall()
    customer = None
    if purchase["customer_id"]:
        customer = conn.execute("SELECT * FROM customers WHERE id = ?", (purchase["customer_id"],)).fetchone()
    conn.close()
    receipt = dict(purchase)
    receipt["items"] = _rows(items)
    receipt["customer"] = _public_customer(customer)
    return receipt


def mark_email_sent(purchase_id):
    conn = get_connection()
    conn.execute("UPDATE purchases SET email_sent = 1 WHERE id = ?", (purchase_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Notifications log
# ---------------------------------------------------------------------------
def save_notification(level, message_en, message_fr):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO notifications (level, message_en, message_fr) VALUES (?, ?, ?)",
        (level, message_en, message_fr),
    )
    conn.commit()
    conn.close()
    return cur.lastrowid


def get_notifications(limit=20):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return _rows(rows)
