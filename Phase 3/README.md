# Smart Store — Phase 3: Smart Self-Checkout

This part covers the **database design**, **receipts** and **notifications**. Everything else (admin pages, RFID/barcode scanning, checkout screen, customer login pages) calls the functions in `db.py`, `receipts.py` and `notifications.py`, so the whole group works on the same database.

## Files

```
Phase 3/
├── database/
│   ├── schema.sql          # all tables, relationships and the inventory view
│   └── seed.sql            # 5 sample products + initial stock (for testing/demo)
├── docs/
│   ├── ER_diagram.png      # ER diagram for the submission
│   └── ER_diagram.mmd      # source of the diagram (Mermaid)
├── db.py                   # database functions (products, inventory, customers, purchases)
├── receipts.py             # builds receipts (text + HTML) and emails them
├── notifications.py        # bilingual (EN/FR) messages for every action
├── test_database.py        # 40 automatic checks + sample receipt
├── requirements.txt
├── .env.example            # copy to .env (Gmail App Password, same as Phase 2)
└── .gitignore
```

## Setup

```bash
cd "Phase 3"
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # then fill in SMTP_EMAIL / SMTP_APP_PASSWORD
python test_database.py             # should end with "All 40 checks passed."
python test_database.py --email you@gmail.com   # also sends a real receipt email
```

`smartstore.db` is created automatically the first time `db.init_db()` runs (call it once when the Flask app starts).

## Database design

| Table | Purpose | Key fields |
|---|---|---|
| **products** | Each product is defined once | name, category, price, **upc** (≤13, unique), **epc** (≤24, unique), producer, image_url, expiry_date |
| **receptions** | Every time stock is received | product_id → products, **quantity**, **received_at** |
| **customers** | Membership accounts | name, email (unique), phone, **membership_number** (auto, e.g. `SS-48213907`), password_hash, **points**, language |
| **purchases** | One row per checkout = one receipt | receipt_number, customer_id → customers (NULL = guest), subtotal, GST, QST, total, **points_earned**, payment_method, email_sent, created_at |
| **purchase_items** | Lines on a receipt | purchase_id → purchases, product_id → products, product_name, **quantity**, **unit_price**, line_total |
| **notifications** | Log of every message shown to users | level, message_en, message_fr, created_at |
| **inventory** *(view)* | Stock dashboard | total_received, total_sold, **in_stock** |

**Relationships (all one-to-many)**
- Product 1 ── * Receptions — one product is received many times
- Product 1 ── * Purchase items — one product appears on many receipts
- Customer 1 ── * Purchases — a customer's purchase history
- Purchase 1 ── * Purchase items — the lines of one receipt

**Design decisions**
- **Stock is calculated, not stored:** `in_stock = total received − total sold` (the `inventory` view). It can never get out of sync.
- **Prices are copied into `purchase_items` at checkout**, so editing a product's price never changes old receipts.
- **Deleting a product is a "soft delete"** (`is_active = 0`): it disappears from the store and inventory, but old receipts that contain it still work. Its UPC/EPC are freed for reuse.
- **Checkout is one transaction:** stock check, receipt, items and points are saved together, or not at all.
- **Passwords are hashed** (Werkzeug), never stored as plain text.
- **Taxes:** GST 5 % + QST 9.975 % (Quebec).
- **Loyalty strategy:** 1 point per full dollar of the subtotal. Guests don't earn points.

> **RFID note:** the spec gives each product one EPC. Every physical RFID tag has its own EPC, so two identical tagged items on the reader would show up as one. For the demo, use one tagged item per product (or the group can add a `product_tags` table later: one row per tag → product_id).

## How the rest of the group uses it

```python
import db, receipts
from notifications import notify, notify_error

db.init_db()   # once, at app start

# --- Admin: products -------------------------------------------------
try:
    pid = db.add_product(name, category, price, upc, epc, producer)
    return jsonify(notify("product_added", lang, name=name))
except db.DatabaseError as error:
    return jsonify(notify_error(str(error), lang)), 400

db.update_product(pid, name, category, price, upc, epc, producer)   # notify("product_updated", ...)
db.delete_product(pid)                                               # notify("product_deleted", ...)

# --- Admin: inventory ------------------------------------------------
db.receive_stock(pid, 24, note="Invoice 1001")      # notify("stock_received", lang, quantity=24, name=..., in_stock=...)
db.get_inventory()                                   # rows for the inventory dashboard
db.get_receptions(pid)                               # reception history (quantity + date)

# --- Scanning --------------------------------------------------------
db.find_by_upc("049000042566")                       # barcode scanner
db.find_by_epcs(list_of_epcs_from_cf600)             # RFID: all tags at once -> {epc: product}

# --- Customers -------------------------------------------------------
acct = db.create_customer(name, email, password, phone, language)   # -> {"id", "membership_number"}
cust = db.login_customer(email, password)            # None if wrong
db.find_customer_by_membership("SS-48213907")        # membership card at checkout
db.get_purchase_history(customer_id)                 # list of past receipts
db.get_purchase(purchase_id)                         # one full receipt (with items)

# --- Checkout (steps 4–6) --------------------------------------------
cart = [{"product_id": 1, "quantity": 2}, {"product_id": 3, "quantity": 1}]
result = receipts.complete_checkout(cart, customer_id=cust_id_or_None, payment_method="card", lang="en")
# result["receipt"]              -> saved receipt (items, totals, points, date)
# result["receipt_html"]         -> show this on the "thank you" screen
# result["notifications"]        -> show to the customer (payment approved, checkout completed, receipt emailed)
# result["store_notifications"]  -> low-stock warnings for the admin dashboard
```

Every `notify(...)` result looks like:
```json
{"success": true, "level": "success", "message": "Product \"Coca-Cola 500ml\" added successfully.",
 "message_en": "...", "message_fr": "..."}
```
The front end only needs to show `message` in a toast coloured by `level` (`success` / `info` / `warning` / `error`). All message keys are listed in `notifications.py`.

## Receipt contents

Receipt number, date and time, member (or guest), product list (name, quantity, unit price, amount), subtotal, GST, QST, **total**, payment method, **points earned** and the customer's total points. It's emailed automatically (HTML + plain text) in the customer's language if they have an account; `email_sent` is set to 1 once it's sent.

## Useful checks for the demo

```bash
sqlite3 smartstore.db "SELECT name, total_received, total_sold, in_stock FROM inventory;"
sqlite3 smartstore.db "SELECT receipt_number, total, points_earned, email_sent, created_at FROM purchases ORDER BY id DESC LIMIT 5;"
```
