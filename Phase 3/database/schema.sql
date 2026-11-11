-- =====================================================================
-- Smart Store - Phase 3 database schema (SQLite)
-- Smart self-checkout: products, inventory receptions, customers,
-- purchases (receipts) and the items on each receipt.
--
-- Relationships (all one-to-many):
--   products   1 ──< receptions      (a product is received many times)
--   products   1 ──< purchase_items  (a product appears on many receipts)
--   customers  1 ──< purchases       (a customer has many receipts)
--   purchases  1 ──< purchase_items  (a receipt has many lines)
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- Products: each product is defined ONCE.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    category      TEXT    NOT NULL,
    price         REAL    NOT NULL CHECK (price >= 0),
    upc           TEXT    NOT NULL UNIQUE CHECK (length(upc) BETWEEN 1 AND 13),   -- barcode
    epc           TEXT    UNIQUE          CHECK (epc IS NULL OR length(epc) <= 24), -- RFID tag
    producer      TEXT    NOT NULL,
    image_url     TEXT,                      -- extra field for realism
    expiry_date   DATE,                      -- extra field for realism
    is_active     INTEGER NOT NULL DEFAULT 1, -- 0 = deleted (kept so old receipts still work)
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Receptions: every time stock of a product is received.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS receptions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id    INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    received_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    note          TEXT                       -- e.g. supplier invoice number
);

-- ---------------------------------------------------------------------
-- Customers: membership accounts with loyalty points.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    name               TEXT NOT NULL,
    email              TEXT NOT NULL UNIQUE,
    phone              TEXT,
    membership_number  TEXT NOT NULL UNIQUE,   -- auto-generated, e.g. SS-48213907
    password_hash      TEXT NOT NULL,          -- never store plain passwords
    points             INTEGER NOT NULL DEFAULT 0 CHECK (points >= 0),
    language           TEXT NOT NULL DEFAULT 'en' CHECK (language IN ('en', 'fr')),
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- One RFID tag identifies one physical item. A tag remains recorded after sale.
CREATE TABLE IF NOT EXISTS product_tags (
    epc TEXT PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    reception_id INTEGER REFERENCES receptions(id),
    sold_purchase_id INTEGER REFERENCES purchases(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Purchases: one row per completed checkout = one receipt.
-- customer_id is NULL for guests (no membership card).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS purchases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_number  TEXT    NOT NULL UNIQUE,   -- e.g. R-20261104-000012
    customer_id     INTEGER REFERENCES customers(id) ON DELETE SET NULL,
    subtotal        REAL    NOT NULL,
    gst             REAL    NOT NULL,          -- 5 %
    qst             REAL    NOT NULL,          -- 9.975 %
    total           REAL    NOT NULL,
    points_earned   INTEGER NOT NULL DEFAULT 0,
    payment_method  TEXT    NOT NULL DEFAULT 'card',  -- simulated: card / cash / tap
    email_sent      INTEGER NOT NULL DEFAULT 0,       -- 1 once the receipt email is sent
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Purchase items: the lines of a receipt.
-- unit_price is COPIED at checkout so old receipts never change
-- when a product's price is edited later.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS purchase_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_id   INTEGER NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
    product_id    INTEGER NOT NULL REFERENCES products(id),
    product_name  TEXT    NOT NULL,            -- copied too, for the same reason
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    unit_price    REAL    NOT NULL,
    line_total    REAL    NOT NULL
);

-- ---------------------------------------------------------------------
-- Notifications: a log of every user action shown on screen
-- ("Product added successfully", "Checkout completed", ...).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    level         TEXT NOT NULL DEFAULT 'info' CHECK (level IN ('info', 'success', 'warning', 'error')),
    message_en    TEXT NOT NULL,
    message_fr    TEXT NOT NULL,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for the lookups the scanners do constantly
CREATE INDEX IF NOT EXISTS idx_receptions_product ON receptions(product_id);
CREATE INDEX IF NOT EXISTS idx_items_purchase     ON purchase_items(purchase_id);
CREATE INDEX IF NOT EXISTS idx_items_product      ON purchase_items(product_id);
CREATE INDEX IF NOT EXISTS idx_purchases_customer ON purchases(customer_id);

-- ---------------------------------------------------------------------
-- Inventory view: stock is CALCULATED, never stored, so it can't drift.
--   in_stock = total received - total sold
-- ---------------------------------------------------------------------
DROP VIEW IF EXISTS inventory;
CREATE VIEW inventory AS
SELECT
    p.id, p.name, p.category, p.price, p.upc, p.epc, p.producer, p.image_url,
    COALESCE(r.total_received, 0)                              AS total_received,
    COALESCE(s.total_sold, 0)                                  AS total_sold,
    COALESCE(r.total_received, 0) - COALESCE(s.total_sold, 0)  AS in_stock,
    r.last_received_at
FROM products p
LEFT JOIN (SELECT product_id, SUM(quantity) AS total_received, MAX(received_at) AS last_received_at
           FROM receptions GROUP BY product_id) r ON r.product_id = p.id
LEFT JOIN (SELECT product_id, SUM(quantity) AS total_sold
           FROM purchase_items GROUP BY product_id) s ON s.product_id = p.id
WHERE p.is_active = 1;
