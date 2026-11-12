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
import math
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
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(customers)")}
    if "is_admin" not in columns:
        conn.execute("ALTER TABLE customers ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
    purchase_columns = {row["name"] for row in conn.execute("PRAGMA table_info(purchases)")}
    if "checkout_key" not in purchase_columns:
        conn.execute("ALTER TABLE purchases ADD COLUMN checkout_key TEXT")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_purchases_checkout_key ON purchases(checkout_key)")
    if seed and conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        with open(SEED_PATH, encoding="utf-8") as f:
            conn.executescript(f.read())
    tag_columns = {row["name"] for row in conn.execute("PRAGMA table_info(product_tags)")}
    if "reception_id" not in tag_columns:
        conn.execute("ALTER TABLE product_tags ADD COLUMN reception_id INTEGER REFERENCES receptions(id)")
    # Preserve each legacy product EPC as an individual tag, once.
    conn.execute("INSERT OR IGNORE INTO product_tags (epc, product_id) SELECT UPPER(epc), id FROM products WHERE epc IS NOT NULL AND is_active = 1")
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
    if not math.isfinite(price):
        raise DatabaseError("Price must be a finite number.")
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
        if epc:
            _assign_tag(conn, cur.lastrowid, epc)
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError as error:
        raise DatabaseError(_duplicate_message(error))
    finally:
        conn.close()


def _assign_tag(conn, product_id, epc):
    """Make `epc` an available (unsold) tag of `product_id` in product_tags.

    A tag that was sold before is re-armed: the admin is physically putting
    that tag on an item again. An unsold tag of another product is refused."""
    row = conn.execute(
        "SELECT product_id, sold_purchase_id FROM product_tags WHERE epc = ?", (epc,)
    ).fetchone()
    if row is None:
        conn.execute("INSERT INTO product_tags (epc, product_id) VALUES (?, ?)", (epc, product_id))
    elif row["sold_purchase_id"] is not None:
        conn.execute(
            "UPDATE product_tags SET product_id = ?, sold_purchase_id = NULL, reception_id = NULL WHERE epc = ?",
            (product_id, epc),
        )
    elif row["product_id"] != product_id:
        raise DatabaseError("This EPC is already assigned to another product.")


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
    return find_by_epcs([epc]).get((epc or "").strip().upper())


def find_by_epcs(epcs):
    epcs = [e.strip().upper() for e in epcs if e and e.strip()]
    if not epcs:
        return {}
    conn = get_connection()
    try:
        placeholders = ",".join("?" for _ in epcs)
        rows = conn.execute(f"SELECT i.*, t.epc AS tag_epc FROM product_tags t JOIN inventory i ON i.id = t.product_id WHERE t.sold_purchase_id IS NULL AND t.epc IN ({placeholders})", epcs).fetchall()
        return {row["tag_epc"]: dict(row) for row in rows}
    finally:
        conn.close()


def find_sold_tags(epcs):
    """For tags that were already sold: {epc: {"name", "receipt_number"}}."""
    epcs = [e.strip().upper() for e in epcs if e and e.strip()]
    if not epcs:
        return {}
    conn = get_connection()
    try:
        placeholders = ",".join("?" for _ in epcs)
        rows = conn.execute(
            f"""SELECT t.epc, p.name, pu.receipt_number
                FROM product_tags t
                JOIN products p ON p.id = t.product_id
                JOIN purchases pu ON pu.id = t.sold_purchase_id
                WHERE t.epc IN ({placeholders})""",
            epcs,
        ).fetchall()
        return {row["epc"]: {"name": row["name"], "receipt_number": row["receipt_number"]} for row in rows}
    finally:
        conn.close()


def reuse_sold_tags():
    """Demo/testing mode (RFID_REUSE_SOLD_TAGS=1): checkout doesn't use up tags."""
    return os.environ.get("RFID_REUSE_SOLD_TAGS", "0").lower() in ("1", "true", "yes")


def get_product_tags(product_id):
    conn = get_connection()
    try:
        return _rows(conn.execute("SELECT t.epc, t.sold_purchase_id, r.received_at FROM product_tags t LEFT JOIN receptions r ON r.id = t.reception_id WHERE t.product_id = ? ORDER BY t.epc", (product_id,)).fetchall())
    finally:
        conn.close()


def get_untagged_stock(product_id):
    """Units eligible for barcode checkout, excluding unsold RFID tags."""
    conn = get_connection()
    try:
        row = conn.execute("""SELECT i.in_stock -
            (SELECT COUNT(*) FROM product_tags t WHERE t.product_id = i.id
             AND t.sold_purchase_id IS NULL) AS available
            FROM inventory i WHERE i.id = ?""", (product_id,)).fetchone()
        return max(0, row["available"]) if row else 0
    finally:
        conn.close()


def register_product_tag(product_id, epc):
    epc = (epc or "").strip().upper()
    if not epc or len(epc) > 24 or any(c not in "0123456789ABCDEF" for c in epc):
        raise DatabaseError("EPC must contain 1 to 24 hexadecimal characters.")
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        product = conn.execute("SELECT * FROM inventory WHERE id = ?", (product_id,)).fetchone()
        if not product:
            raise DatabaseError("Product not found.")
        current = conn.execute(
            "SELECT product_id, sold_purchase_id FROM product_tags WHERE epc = ?", (epc,)
        ).fetchone()
        if current and current["sold_purchase_id"] is None:
            if current["product_id"] == product_id:
                raise DatabaseError("This tag is already assigned to this product.")
            raise DatabaseError("This EPC is already assigned to another product.")
        tagged = conn.execute("SELECT COUNT(*) FROM product_tags WHERE product_id = ? AND sold_purchase_id IS NULL", (product_id,)).fetchone()[0]
        if tagged >= product["in_stock"]:
            raise DatabaseError("Receive more stock before assigning another tag.")
        # New tag, or a sold tag being put on an item again (re-armed).
        _assign_tag(conn, product_id, epc)
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        raise DatabaseError("This EPC is already registered.")
    finally:
        conn.close()


def reset_sold_tags(product_id=None, epc=None):
    """Make sold RFID tags available again so they can be scanned and sold
    again (for practice/demo checkouts). Old receipts and the Sold / In stock
    numbers don't change, because they come from the purchase records.

    reset_sold_tags()                    -> every sold tag in the store
    reset_sold_tags(product_id=3)        -> every sold tag of one product
    reset_sold_tags(product_id=3, epc=X) -> one tag
    Returns how many tags were reset."""
    sql = "UPDATE product_tags SET sold_purchase_id = NULL WHERE sold_purchase_id IS NOT NULL"
    args = []
    if product_id is not None:
        sql += " AND product_id = ?"
        args.append(product_id)
    if epc:
        sql += " AND epc = ?"
        args.append(epc.strip().upper())
    conn = get_connection()
    try:
        count = conn.execute(sql, args).rowcount
        conn.commit()
        return count
    finally:
        conn.close()


def remove_product_tag(product_id, epc):
    """Unassign a tag from a product (e.g. to put it on another product)."""
    epc = (epc or "").strip().upper()
    conn = get_connection()
    try:
        removed = conn.execute(
            "DELETE FROM product_tags WHERE epc = ? AND product_id = ?", (epc, product_id)
        ).rowcount
        if not removed:
            raise DatabaseError("Tag not found.")
        # init_db() copies products.epc into product_tags at every start,
        # so clear it there too or the tag would come back after a restart.
        conn.execute(
            "UPDATE products SET epc = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND epc = ?",
            (product_id, epc),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------
def receive_stock(product_id, quantity, note=None, received_at=None, epcs=None):
    """Record a delivery and optional individual tags atomically."""
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        raise DatabaseError("Quantity must be a whole number.")
    if quantity <= 0:
        raise DatabaseError("Quantity must be greater than 0.")
    tags = [(epc or "").strip().upper() for epc in (epcs or [])]
    if len(tags) > quantity:
        raise DatabaseError("The number of EPCs cannot exceed the quantity received.")
    if len(tags) != len(set(tags)):
        raise DatabaseError("Each EPC must be unique in this delivery.")
    if any(not epc or len(epc) > 24 or any(c not in "0123456789ABCDEF" for c in epc) for epc in tags):
        raise DatabaseError("Each EPC must contain 1 to 24 hexadecimal characters.")
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if not conn.execute("SELECT 1 FROM products WHERE id = ? AND is_active = 1", (product_id,)).fetchone():
            raise DatabaseError("Product not found.")
        if received_at:
            cur = conn.execute("INSERT INTO receptions (product_id, quantity, note, received_at) VALUES (?, ?, ?, ?)", (product_id, quantity, note, received_at))
        else:
            cur = conn.execute("INSERT INTO receptions (product_id, quantity, note) VALUES (?, ?, ?)", (product_id, quantity, note))
        reception_id = cur.lastrowid
        conn.executemany("INSERT INTO product_tags (epc, product_id, reception_id) VALUES (?, ?, ?)", [(epc, product_id, reception_id) for epc in tags])
        conn.commit()
        return reception_id
    except sqlite3.IntegrityError:
        conn.rollback()
        raise DatabaseError("An EPC is already registered; no stock was received.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_inventory():
    """Everything the inventory dashboard needs: one row per product with
    total_received, total_sold and in_stock."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM inventory ORDER BY category, name").fetchall()
    conn.close()
    return _rows(rows)


def get_receptions(product_id=None):
    conn = get_connection()
    sql = """SELECT r.*, p.name AS product_name,
             (SELECT GROUP_CONCAT(epc, ", ") FROM product_tags WHERE reception_id = r.id) AS epcs
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


def create_purchase(cart, customer_id=None, payment_method="card", epcs=None, checkout_key=None, return_status=False):
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

        # A retry with the same signed cart identity returns the original sale.
        if checkout_key:
            existing = conn.execute("SELECT id FROM purchases WHERE checkout_key = ?", (checkout_key,)).fetchone()
            if existing:
                return (existing["id"], False) if return_status else existing["id"]

        epcs = list(epcs or [])
        if len(epcs) != len(set(epcs)):
            raise DatabaseError("Duplicate RFID tag in cart.")
        tagged_counts = {}
        for epc in epcs:
            tag = conn.execute("SELECT product_id FROM product_tags WHERE epc = ? AND sold_purchase_id IS NULL", (epc,)).fetchone()
            if not tag or tag["product_id"] not in quantities:
                raise DatabaseError("An RFID tag is no longer available. Reset and rescan the cart.")
            tagged_counts[tag["product_id"]] = tagged_counts.get(tag["product_id"], 0) + 1
        lines = []
        subtotal = 0.0
        for pid, qty in quantities.items():
            product = conn.execute("SELECT * FROM inventory WHERE id = ?", (pid,)).fetchone()
            if not product:
                raise DatabaseError(f"Product #{pid} is no longer available.")
            if product["in_stock"] < qty:
                raise DatabaseError(f"Only {product['in_stock']} '{product['name']}' left in stock.")
            tagged_sold = tagged_counts.get(pid, 0)
            if tagged_sold > qty:
                raise DatabaseError("RFID tags do not match cart quantities.")
            available_tagged = conn.execute("SELECT COUNT(*) FROM product_tags WHERE product_id = ? AND sold_purchase_id IS NULL", (pid,)).fetchone()[0]
            if qty - tagged_sold > product["in_stock"] - available_tagged:
                raise DatabaseError("Scan the RFID tags for tagged items; barcode sales require untagged stock.")
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
                                      points_earned, payment_method, checkout_key)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (receipt_number, customer_id, totals["subtotal"], totals["gst"], totals["qst"],
             totals["total"], totals["points_earned"], payment_method, checkout_key),
        )
        purchase_id = cur.lastrowid

        conn.executemany(
            """INSERT INTO purchase_items (purchase_id, product_id, product_name, quantity, unit_price, line_total)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [(purchase_id, *line) for line in lines],
        )

        if not reuse_sold_tags():
            for epc in epcs:
                conn.execute("UPDATE product_tags SET sold_purchase_id = ? WHERE epc = ?", (purchase_id, epc))

        if customer_id is not None and totals["points_earned"]:
            conn.execute(
                "UPDATE customers SET points = points + ? WHERE id = ?",
                (totals["points_earned"], customer_id),
            )

        conn.commit()
        return (purchase_id, True) if return_status else purchase_id
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
    receipt.pop("checkout_key", None)
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
