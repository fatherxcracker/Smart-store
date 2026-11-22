"""
Smart Store - Phase 3
Database layer (SQLite). Every other part of the project (admin pages,
self-checkout, customer accounts, receipts) calls these functions instead of
writing SQL directly, so the whole group works against the same schema.

    import db
    db.init_db()                      # creates smartstore.db + tables (safe to run every start)
    db.add_product(name=..., ...)     # products
    db.receive_stock(product_id, 2, epcs=["E2801170...01", "E2801170...02"])  # inventory: one EPC per unit
    db.create_customer(...)           # accounts
    db.create_purchase(cart, ...)     # checkout -> receipt
"""

import os
import secrets
import sqlite3
import math
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app, has_app_context

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "smartstore.db"))
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")
SEED_PATH = os.path.join(BASE_DIR, "database", "seed.sql")

# Quebec sales taxes
GST_RATE = 0.05
QST_RATE = 0.09975

# Earn 1 point per full dollar after discounts, before tax; redeem at $0.10 each.
POINTS_PER_DOLLAR = 1


# Fixed list of product categories (the add/edit product form only allows these).
# value stored in the database -> French label shown when the page is in French
CATEGORIES = {
    "Bakery": "Boulangerie",
    "Beverages": "Boissons",
    "Candy": "Bonbons",
    "Dairy": "Produits laitiers",
    "Deli": "Charcuterie",
    "Frozen Foods": "Surgelés",
    "Fruits & Vegetables": "Fruits et légumes",
    "Health & Beauty": "Santé et beauté",
    "Household": "Entretien ménager",
    "Meat & Seafood": "Viandes et poissons",
    "Pantry": "Épicerie",
    "Pet Supplies": "Animaux",
    "Snacks": "Collations",
    "Other": "Autre",
}

# Old free-text categories from earlier versions -> the matching fixed category
LEGACY_CATEGORIES = {
    "beverage": "Beverages", "drinks": "Beverages", "drink": "Beverages",
    "snack": "Snacks", "candies": "Candy", "milk": "Dairy",
    "frozen": "Frozen Foods", "produce": "Fruits & Vegetables",
    "fruits": "Fruits & Vegetables", "vegetables": "Fruits & Vegetables",
    "meat": "Meat & Seafood", "seafood": "Meat & Seafood",
    "personal care": "Health & Beauty", "health": "Health & Beauty",
    "pet": "Pet Supplies", "pets": "Pet Supplies",
}


def normalize_category(value):
    """Return the fixed category matching `value` (case-insensitive), or None."""
    text = (value or "").strip().lower()
    for category in CATEGORIES:
        if category.lower() == text or CATEGORIES[category].lower() == text:
            return category
    return LEGACY_CATEGORIES.get(text)


class DatabaseError(Exception):
    """Raised with a user-friendly message (e.g. 'UPC already exists')."""


# ---------------------------------------------------------------------------
# Connection / setup
# ---------------------------------------------------------------------------
def get_database_path():
    return current_app.config.get("DATABASE_PATH", DATABASE_PATH) if has_app_context() else DATABASE_PATH


def get_connection():
    conn = sqlite3.connect(get_database_path())
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
    for column, definition in (("points_redeemed", "INTEGER NOT NULL DEFAULT 0"), ("points_discount", "REAL NOT NULL DEFAULT 0")):
        if column not in purchase_columns:
            conn.execute(f"ALTER TABLE purchases ADD COLUMN {column} {definition}")
    if seed and conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        with open(SEED_PATH, encoding="utf-8") as f:
            conn.executescript(f.read())
    tag_columns = {row["name"] for row in conn.execute("PRAGMA table_info(product_tags)")}
    if "reception_id" not in tag_columns:
        conn.execute("ALTER TABLE product_tags ADD COLUMN reception_id INTEGER REFERENCES receptions(id)")
    # Preserve each legacy product EPC as an individual tag, once
    # (databases from before product_tags existed: that EPC was a real tagged item).
    conn.execute("""INSERT OR IGNORE INTO product_tags (epc, product_id)
                    SELECT UPPER(p.epc), p.id FROM products p
                    WHERE p.epc IS NOT NULL AND p.is_active = 1
                      AND NOT EXISTS (SELECT 1 FROM product_tags t WHERE t.product_id = p.id)
                      AND NOT EXISTS (SELECT 1 FROM purchase_items i WHERE i.product_id = p.id)""")
    # Move old free-text categories onto the fixed list
    for row in conn.execute("SELECT id, category FROM products").fetchall():
        fixed = normalize_category(row["category"])
        if fixed and fixed != row["category"]:
            conn.execute("UPDATE products SET category = ? WHERE id = ?", (fixed, row["id"]))
    conn.commit()
    conn.close()
    print(f"[database] Ready at {get_database_path()}")


def _rows(rows):
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Products (admin: register / edit / delete)
# ---------------------------------------------------------------------------
def _validate_product(name, category, price, upc, epc, producer, current_category=None):
    if not name or not category or not producer:
        raise DatabaseError("Name, category and producer are required.")
    fixed = normalize_category(category)
    # An old product may keep its existing category until it is changed
    if not fixed and not (current_category and category.strip() == current_category):
        raise DatabaseError("Choose a category from the list.")
    category = fixed or category.strip()
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
    return price, upc, epc, category


def add_product(name, category, price, upc, epc, producer, image_url=None, expiry_date=None):
    price, upc, epc, category = _validate_product(name, category, price, upc, epc, producer)
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO products (name, category, price, upc, epc, producer, image_url, expiry_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name.strip(), category, price, upc, epc, producer.strip(), image_url, expiry_date),
        )
        product_id = cur.lastrowid
        if epc:
            # The EPC belongs to a physical item: record it as 1 item received
            rec = conn.execute(
                "INSERT INTO receptions (product_id, quantity, note) VALUES (?, 1, 'Initial stock')",
                (product_id,),
            )
            _assign_tag(conn, product_id, epc, rec.lastrowid)
        conn.commit()
        return product_id
    except sqlite3.IntegrityError as error:
        raise DatabaseError(_duplicate_message(error))
    finally:
        conn.close()


def _assign_tag(conn, product_id, epc, reception_id=None):
    """Make `epc` an available (unsold) tag of `product_id`, linked to the
    delivery (reception) it arrived in.

    A tag that was sold before can be put on a new item again (re-armed).
    A tag that is already on an unsold item is refused: no duplicates."""
    row = conn.execute(
        "SELECT product_id, sold_purchase_id FROM product_tags WHERE epc = ?", (epc,)
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO product_tags (epc, product_id, reception_id) VALUES (?, ?, ?)",
            (epc, product_id, reception_id),
        )
    elif row["sold_purchase_id"] is not None:
        conn.execute(
            "UPDATE product_tags SET product_id = ?, sold_purchase_id = NULL, reception_id = ? WHERE epc = ?",
            (product_id, reception_id, epc),
        )
    elif row["product_id"] == product_id:
        raise DatabaseError(f"Tag {epc} is already on an item of this product.")
    else:
        raise DatabaseError(f"Tag {epc} is already assigned to another product.")


def update_product(product_id, name, category, price, upc, epc, producer, image_url=None, expiry_date=None):
    existing = get_product(product_id)
    price, upc, epc, category = _validate_product(
        name, category, price, upc, epc, producer,
        current_category=existing["category"] if existing else None,
    )
    conn = get_connection()
    try:
        cur = conn.execute(
            """UPDATE products
               SET name = ?, category = ?, price = ?, upc = ?, epc = ?, producer = ?,
                   image_url = ?, expiry_date = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ? AND is_active = 1""",
            (name.strip(), category, price, upc, epc, producer.strip(),
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


def register_product_tag(product_id, epc, note="Tag added on Manage tags"):
    """Add one tagged item to stock (a delivery of 1). Every item in stock
    has its own RFID tag, so a new tag always means one more item."""
    return receive_stock(product_id, epcs=[epc], note=note)


def reset_sold_tags(product_id=None, epc=None):
    """Make sold RFID tags available again so they can be scanned and sold
    again (for practice/demo checkouts). Stock goes back up by one per tag
    (stock = unsold tags); old receipts and the Sold column don't change.

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
    """Unassign a tag from a product (e.g. to put it on another product).
    An unsold tag removed this way takes its item out of stock."""
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
def receive_stock(product_id, quantity=None, note=None, received_at=None, epcs=None):
    """Record a delivery: one RFID tag (EPC) per item received, atomically.

    The quantity received IS the number of EPCs. `quantity` is optional; when
    given it must match the number of EPCs. A tag that was sold before can be
    put on a new item; a tag already on an unsold item is refused."""
    tags = [(epc or "").strip().upper() for epc in (epcs or []) if (epc or "").strip()]
    if not tags:
        raise DatabaseError("Scan the RFID tag of every item received. No stock was received.")
    if quantity not in (None, ""):
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise DatabaseError("Quantity must be a whole number.")
        if quantity != len(tags):
            raise DatabaseError(
                f"Every item needs one RFID tag: you are receiving {quantity} item(s) "
                f"but entered {len(tags)} EPC(s). No stock was received."
            )
    if len(tags) != len(set(tags)):
        raise DatabaseError("Each EPC must be unique in this delivery.")
    if any(len(epc) > 24 or any(c not in "0123456789ABCDEF" for c in epc) for epc in tags):
        raise DatabaseError("Each EPC must contain 1 to 24 hexadecimal characters.")
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if not conn.execute("SELECT 1 FROM products WHERE id = ? AND is_active = 1", (product_id,)).fetchone():
            raise DatabaseError("Product not found.")
        if received_at:
            cur = conn.execute("INSERT INTO receptions (product_id, quantity, note, received_at) VALUES (?, ?, ?, ?)", (product_id, len(tags), note, received_at))
        else:
            cur = conn.execute("INSERT INTO receptions (product_id, quantity, note) VALUES (?, ?, ?)", (product_id, len(tags), note))
        reception_id = cur.lastrowid
        for epc in tags:
            _assign_tag(conn, product_id, epc, reception_id)
        conn.commit()
        return reception_id
    except DatabaseError as error:
        conn.rollback()
        message = str(error)
        if "No stock" not in message and message != "Product not found.":
            message += " No stock was received."
        raise DatabaseError(message)
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


# ---------------------------------------------------------------------------
# User management (admin)
# ---------------------------------------------------------------------------
def list_customers(search=None):
    """Every account with its purchase count, total spent and last purchase.
    search matches name, email, phone or membership number."""
    sql = """SELECT c.*,
                    COUNT(p.id)                 AS purchase_count,
                    COALESCE(SUM(p.total), 0)   AS total_spent,
                    MAX(p.created_at)           AS last_purchase_at
             FROM customers c
             LEFT JOIN purchases p ON p.customer_id = c.id"""
    args = []
    search = (search or "").strip()
    if search:
        like = f"%{search.lower()}%"
        sql += """ WHERE lower(c.name) LIKE ? OR lower(c.email) LIKE ?
                   OR lower(COALESCE(c.phone, '')) LIKE ? OR lower(c.membership_number) LIKE ?"""
        args = [like, like, like, like]
    sql += " GROUP BY c.id ORDER BY c.is_admin DESC, c.created_at DESC, c.id DESC"
    conn = get_connection()
    rows = conn.execute(sql, args).fetchall()
    conn.close()
    return [_public_customer(r) for r in rows]


def count_admins():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM customers WHERE is_admin = 1").fetchone()[0]
    conn.close()
    return count


def admin_update_customer(customer_id, name, email, phone=None, language="en"):
    """Edit an account's profile (admin)."""
    name = (name or "").strip()
    email = (email or "").strip().lower()
    phone = (phone or "").strip() or None
    if not name or not email:
        raise DatabaseError("Name and email are required.")
    if "@" not in email:
        raise DatabaseError("Enter a valid email address.")
    if language not in ("en", "fr"):
        language = "en"
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE customers SET name = ?, email = ?, phone = ?, language = ? WHERE id = ?",
            (name, email, phone, language, customer_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise DatabaseError("Customer not found.")
    except sqlite3.IntegrityError:
        raise DatabaseError("An account with this email already exists.")
    finally:
        conn.close()


def set_customer_points(customer_id, points):
    """Set a loyalty balance directly (admin correction)."""
    try:
        points = int(str(points).strip())
    except (TypeError, ValueError):
        raise DatabaseError("Points must be a whole number of 0 or more.")
    if points < 0:
        raise DatabaseError("Points must be a whole number of 0 or more.")
    conn = get_connection()
    cur = conn.execute("UPDATE customers SET points = ? WHERE id = ?", (points, customer_id))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise DatabaseError("Customer not found.")
    return points


def set_customer_password(customer_id, password):
    """Reset an account's password (admin)."""
    if not password or len(password) < 6:
        raise DatabaseError("Password must be at least 6 characters.")
    conn = get_connection()
    cur = conn.execute(
        "UPDATE customers SET password_hash = ? WHERE id = ?",
        (generate_password_hash(password), customer_id),
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise DatabaseError("Customer not found.")


def set_customer_admin(customer_id, is_admin, acting_admin_id=None):
    """Grant or remove administrator access. The store always keeps at least
    one administrator, and an admin can't remove their own access here."""
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT is_admin FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if not row:
            raise DatabaseError("Customer not found.")
        if not is_admin and row["is_admin"]:
            if acting_admin_id is not None and int(customer_id) == int(acting_admin_id):
                raise DatabaseError("You can't remove your own administrator access.")
            if conn.execute("SELECT COUNT(*) FROM customers WHERE is_admin = 1").fetchone()[0] <= 1:
                raise DatabaseError("The store must keep at least one administrator.")
        conn.execute("UPDATE customers SET is_admin = ? WHERE id = ?", (1 if is_admin else 0, customer_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_customer(customer_id, acting_admin_id=None):
    """Delete an account. Its receipts are kept (they become guest receipts)
    so sales totals and stock stay correct."""
    if acting_admin_id is not None and int(customer_id) == int(acting_admin_id):
        raise DatabaseError("You can't delete your own account here.")
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT is_admin FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if not row:
            raise DatabaseError("Customer not found.")
        if row["is_admin"] and conn.execute(
            "SELECT COUNT(*) FROM customers WHERE is_admin = 1"
        ).fetchone()[0] <= 1:
            raise DatabaseError("The store must keep at least one administrator.")
        # Keep the receipts, unlinked from the account (same as ON DELETE SET NULL)
        conn.execute("UPDATE purchases SET customer_id = NULL WHERE customer_id = ?", (customer_id,))
        conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


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
def calculate_totals(subtotal, points_redeemed=0):
    if type(points_redeemed) is not int or points_redeemed < 0:
        raise DatabaseError("Points must be a non-negative whole number.")
    original = Decimal(str(subtotal)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    discount = Decimal(points_redeemed) * Decimal("0.10")
    if discount > original:
        raise DatabaseError("Points cannot exceed the purchase subtotal.")
    taxable = original - discount
    gst = (taxable * Decimal(str(GST_RATE))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    qst = (taxable * Decimal(str(QST_RATE))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {"subtotal": float(original), "points_redeemed": points_redeemed,
            "points_discount": float(discount), "discounted_subtotal": float(taxable),
            "gst": float(gst), "qst": float(qst), "total": float(taxable + gst + qst),
            "points_earned": int(taxable) * POINTS_PER_DOLLAR}


def create_purchase(cart, customer_id=None, payment_method="card", epcs=None, checkout_key=None, return_status=False, points_redeemed=0):
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
            # Items are only sold by their RFID tag (EPC): one tag per unit.
            if tagged_counts.get(pid, 0) != qty:
                raise DatabaseError("Every item must be scanned with the RFID reader. Reset and rescan the cart.")
            line_total = round(product["price"] * qty, 2)
            subtotal += line_total
            lines.append((pid, product["name"], qty, product["price"], line_total))

        if customer_id is not None and not conn.execute(
            "SELECT 1 FROM customers WHERE id = ?", (customer_id,)
        ).fetchone():
            raise DatabaseError("Customer not found.")

        totals = calculate_totals(subtotal, points_redeemed)
        if points_redeemed:
            customer = conn.execute("SELECT points FROM customers WHERE id = ?", (customer_id,)).fetchone()
            if not customer or customer["points"] < points_redeemed:
                raise DatabaseError("Not enough loyalty points available.")
        if customer_id is None:
            totals["points_earned"] = 0  # guests don't earn points

        receipt_number = f"R-{datetime.now():%Y%m%d}-{secrets.token_hex(3).upper()}"
        cur = conn.execute(
            """INSERT INTO purchases (receipt_number, customer_id, subtotal, gst, qst, total,
                                      points_earned, payment_method, checkout_key, points_redeemed, points_discount)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (receipt_number, customer_id, totals["subtotal"], totals["gst"], totals["qst"],
             totals["total"], totals["points_earned"], payment_method, checkout_key, points_redeemed, totals["points_discount"]),
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

        if customer_id is not None:
            conn.execute(
                "UPDATE customers SET points = points - ? + ? WHERE id = ?",
                (points_redeemed, totals["points_earned"], customer_id),
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
