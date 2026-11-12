# Smart Store — Phase 3: Smart Self-Checkout

A web-based smart store running on the Raspberry Pi: product and inventory management, a self-checkout that reads **all items at once with the CF600 RFID reader** (or one at a time with a barcode scanner), simulated payment, loyalty points, receipts emailed automatically, and a bilingual (EN/FR) customer portal.

| Page | URL | Who uses it |
|---|---|---|
| Customer portal | `http://<pi-ip>:5002/` | Customers: create an account, log in, see points + purchase history (EN/FR) |
| Inventory dashboard | `http://<pi-ip>:5002/inventory` | Admin: add / edit / delete products, receive stock, reception history |
| Self-checkout | `http://<pi-ip>:5002/cart` | Customers: scan, review list, remove items, membership card, pay, receipt |

All three pages link to each other in their navigation bars.

---

## 1. Hardware

| Device | Connected to | Used for |
|---|---|---|
| Chafon **CF600** UHF RFID reader | Pi USB port | Reading every tag on the reader at once (checkout) and reading one tag's EPC (product form) |
| USB **barcode scanner** | The computer showing the page | Reading UPCs. It acts like a keyboard: click a UPC/barcode field and scan. No driver or code needed. |
| UHF RFID tags | One per physical item | Each unique EPC links one item to a product type |

The Flask app must run **on the Pi**, because the RFID reader is plugged into it. The pages can be opened on the Pi itself or on any laptop/phone on the same network.

---

## 2. Setup on the Raspberry Pi (once)

```bash
cd ~/Smart-store/"Phase 3"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env          # fill in SMTP_EMAIL / SMTP_APP_PASSWORD (Gmail App Password, no spaces)
```

### RFID reader setup (once)

```bash
# 1. Load the USB-serial driver for the CF600 automatically at every boot
echo "usbserial" | sudo tee /etc/modules-load.d/cf600.conf
echo "options usbserial vendor=0x0483 product=0x5750" | sudo tee /etc/modprobe.d/cf600.conf

# 2. Allow your user to open the serial port without sudo
sudo usermod -aG dialout $USER

sudo reboot
```

After the reboot, check it:

```bash
ls /dev/ttyUSB*                 # should show /dev/ttyUSB0
cd ~/Smart-store/"Phase 3" && source venv/bin/activate
python rfid_reader.py           # hold tags on the reader -> their EPCs are printed (Ctrl+C to stop)
```

If the reader shows up as `/dev/ttyACM0` instead, set `RFID_PORT=/dev/ttyACM0` in `.env`.

### No reader (testing on a laptop)

Set `RFID_SIMULATE=1` in `.env`. "Scan all items" then pretends the tags listed in `RFID_SIMULATED_TAGS` are on the reader (by default Coca-Cola, Lay's and Kit Kat from the sample data). Set it back to `0` on the Pi.

---

## 3. Run

```bash
cd ~/Smart-store/"Phase 3"
source venv/bin/activate
python app.py
```

Open `http://<pi-ip>:5002` (find the IP with `hostname -I`), or `http://localhost:5002` on the Pi.

The database `smartstore.db` is created automatically the first time, with 5 sample products and 24 of each in stock. To start the demo from a clean database, stop the app and delete `smartstore.db`.

### Test accounts (new databases only)

The initial seed creates these demo accounts:

| Role | Email | Password |
|---|---|---|
| Administrator | `admin@smartstore.local` | `eUL1b-l0PhnHW9WDo8A6Dw` |
| Customer | `john@gmail.com` | `123456` |

These publicly documented credentials are for testing only. Do not use them for a network-accessible or real store. The seed runs when the product database is empty; it does not add accounts to an existing populated database or change existing passwords. To grant an existing account administrator access, run `python manage_admin.py email@example.com` from Phase 3. Add `--revoke` to remove access.

---

## 4. Linking an RFID tag (EPC) to a product

The self-checkout only recognises a tag if its **EPC** is saved on a product. The sample products use made-up EPCs (`E28011700000020A1B2C3D01`…), so **you must link your real tags before the checkout will find them**.

### Option A: read tags in the website

1. Start the app on the Pi with the CF600 connected and log in as an administrator.
2. Open **Inventory** and click the product UPC or **Manage tags**. Receive stock first if necessary.
3. Place one item on the reader, click **Read tag from RFID reader**, then **Assign tag**. Repeat for each physical item. Alternatively, enter or read one EPC per line when recording a delivery.
4. Open checkout and scan the tagged items. Two different EPCs assigned to the same product add two units.

If no tag is detected, move it closer; if several are detected, remove the extra tags. A duplicate EPC cannot be assigned again.

### Option B: read EPCs from the terminal

Stop the app before running `python rfid_reader.py`, because only one program can use the reader at a time. Hold a tag on the reader, copy its EPC, then stop the script and restart the app. Paste the EPC into **Manage tags** or the receive-stock form.

### Rules

- EPCs have up to **24 hexadecimal characters** (`0-9`, `A-F`); each identifies one physical item. A product UPC identifies its type and can have many EPCs.
- Existing product EPCs are migrated to individual tag records on startup. Existing accounts, stock and purchases are preserved.
- With `RFID_SIMULATE=1`, checkout uses the EPCs in `RFID_SIMULATED_TAGS`. Use tags that exist in the database.
- Tagged items must be checked out using RFID, so their individual tags can be marked sold. Barcode checkout is available for untagged stock.
- **A sold tag can't be scanned again.** The cart shows *"Already sold: … (receipt …)"*. To put that tag on a new item, assign it again in **Manage tags**; it becomes available.
- **Testing with the same tags over and over?** Set `RFID_REUSE_SOLD_TAGS=1` in `.env` and restart the app. Checkout then doesn't use up tags. Set it back to `0` for the real demo.

### Resetting tags (before a demo or after testing)

Log in with an **admin** account. Afterwards click **Reset cart** on `/cart`, so the checkout forgets the tags it already read.

| What you want | Where | Button |
|---|---|---|
| Make **every** sold tag in the store available again (after practice checkouts) | **Inventory** page | **Reset sold RFID tags** (asks to confirm) |
| Make all sold tags of **one product** available again | **Manage tags** of that product | **Make all sold tags available** |
| Make **one** sold tag available again | **Manage tags** → the tag's row | **Make available** |
| **Remove** a tag from a product (e.g. to put it on another product) | **Manage tags** → the tag's row | **Remove** (asks to confirm), then assign it in the other product's **Manage tags** |

Old receipts and the Sold / In stock numbers don't change, because they come from the purchase records. Every reset/remove shows a notification and is saved in the notifications log.

<details>
<summary>Same thing with SQL commands (optional)</summary>

Run these from the `Phase 3` folder. The app can stay running.

**Make every sold tag available again:**

```bash
sqlite3 smartstore.db "UPDATE product_tags SET sold_purchase_id = NULL;"
```

Old receipts and the Sold / In stock numbers don't change, because they come from the purchase records.

**Reset only one tag:**

```bash
sqlite3 smartstore.db "UPDATE product_tags SET sold_purchase_id = NULL WHERE epc = 'A00000000000000000004994';"
```

**See every tag and whether it's sold:**

```bash
sqlite3 -header smartstore.db "SELECT t.epc, p.name, CASE WHEN t.sold_purchase_id IS NULL THEN 'Available' ELSE 'Sold' END AS status FROM product_tags t JOIN products p ON p.id = t.product_id ORDER BY p.id;"
```

**Remove a tag** (to move it to another product, then assign it in that product's **Manage tags**):

```bash
sqlite3 smartstore.db "DELETE FROM product_tags WHERE epc = 'A00000000000000000004994';"
```

</details>

**Assign your real tags after a fresh database.** The sample data only has made-up EPCs (`E2801170…`), so real tags show as "Unknown" until they're assigned. Use **Manage tags** in the website, or add them all at once. Replace the EPCs with your own; read them with `python rfid_reader.py` while the app is stopped:

```bash
sqlite3 smartstore.db "
INSERT OR REPLACE INTO product_tags (epc, product_id) SELECT 'A00000000000000000004994', id FROM products WHERE name = 'Coca-Cola 500ml';
INSERT OR REPLACE INTO product_tags (epc, product_id) SELECT 'A00000000000000000004996', id FROM products WHERE name = 'Natrel Milk 2% 2L';
INSERT OR REPLACE INTO product_tags (epc, product_id) SELECT 'A00000000000000000004991', id FROM products WHERE name = 'Kit Kat 45g';
INSERT OR REPLACE INTO product_tags (epc, product_id) SELECT 'A00000000000000000004988', id FROM products WHERE name = 'Dasani Water 591ml';
"
```

**Start over with a fresh database** (erases all accounts, purchases, stock and tags). Stop the app first, keep a backup outside the project folder so it's never committed, then start the app to rebuild the sample data:

```bash
mkdir -p ~/smartstore-backups
cp smartstore.db ~/smartstore-backups/smartstore-$(date +%Y%m%d-%H%M%S).db
rm smartstore.db
python app.py
```

---

## 5. How each requirement is covered

### Product management (admin) — `/inventory`
- **Register / edit / delete** products with name, category, price, **UPC** (≤ 13) and producer; assign individual EPCs separately after receiving stock.
- **UPC via barcode scanner:** click the UPC field and scan.
- **EPC via the RFID reader:** receive stock, open **Manage tags** for the product, then read and assign each physical item’s tag. The app warns if 0 or several tags are on the reader.
- Duplicate UPC/EPC and invalid values are rejected with a clear message.
- Deleting a product hides it from the store and inventory, but old receipts that contain it stay correct.

### Inventory
- A product is defined once and **received many times**: **Receive stock** records the quantity and the date/time received (with an optional invoice note).
- **Inventory dashboard:** received, sold and **in stock** for every product (stock = total received − total sold), plus the last reception date.
- **Reception history**, filterable by product.

### Self-checkout — `/cart`
1. **Scan all products at once:** place the items on the CF600 and click **Scan all items**. Every tag is read in one scan. Tick **Auto-scan** and the list keeps updating by itself every few seconds. A tag that was already read isn't counted twice; unknown tags are ignored with a warning.
   Products can also be added with the **barcode scanner** (one scan = one item).
2. The **shopping list** updates immediately: items, quantity, price, subtotal, GST, QST and total.
3. **Remove** any unwanted item, or **Reset cart**.
4. Enter the **membership number** (from the customer's membership card), or leave it blank to check out as a guest.
5. **Proceed to payment:** simulated payment (card / tap / cash) after a confirmation.
6. **Points** are added to the member's account: **1 point per full dollar** of the subtotal (guests earn none).
7. A **receipt** is shown on screen and **emailed automatically** to the member's email. The email is in the language saved on the member's account (the EN/FR choice in the customer portal), whatever language the checkout screen is in.

### Customer accounts — `/`
- **Create an account:** name, email, password, optional phone. A **membership number** (e.g. `SS-48213907`) is generated automatically.
- **Log in** to see the membership card, **total points** and **purchase history**; each past receipt can be opened.
- **Bilingual:** EN/FR switch (bonus). The choice is saved on the account (also when it was picked before logging in), and receipt emails are sent in that language.

### Receipts and notifications
- The **receipt** has the product list (name, quantity, unit price, amount), subtotal, GST, QST, **total**, payment method, **points earned**, the member's total points and the **date and time**.
- **Notifications** appear after every action: product added/updated/deleted, stock received, item scanned/removed, payment approved, checkout completed, receipt emailed, account created, login, errors. Every notification is also saved in the `notifications` table (`/api/notifications` shows the last 20).

---

## 6. Database design

See `docs/ER_diagram.png`.

| Table | Purpose | Key fields |
|---|---|---|
| **products** | Each product is defined once | name, category, price, **upc** (≤13, unique), **epc** (≤24, unique), producer, image_url, expiry_date, is_active |
| **receptions** | Every time stock is received | product_id → products, **quantity**, **received_at**, note |
| **customers** | Membership accounts | name, email (unique), phone, **membership_number** (auto), password_hash, **points**, language |
| **purchases** | One row per checkout = one receipt | receipt_number, customer_id → customers (NULL = guest), subtotal, gst, qst, total, **points_earned**, payment_method, email_sent, created_at |
| **purchase_items** | Lines on a receipt | purchase_id → purchases, product_id → products, product_name, **quantity**, **unit_price**, line_total |
| **notifications** | Log of every message shown | level, message_en, message_fr, created_at |
| **inventory** *(view)* | Inventory dashboard | total_received, total_sold, **in_stock**, last_received_at |

**Relationships (all one-to-many):** Product → Receptions · Product → Purchase items · Customer → Purchases · Purchase → Purchase items.

**Design decisions**
- **Stock is calculated, not stored**, so it can never get out of sync.
- **Price and name are copied into `purchase_items`** at checkout, so editing a product never changes old receipts.
- **Checkout is one database transaction:** stock check, receipt, items and points are saved together, or not at all.
- **Passwords are hashed**, never stored in plain text.
- **Times are stored in UTC** and shown in local time on every page and receipt.
- **Taxes:** GST 5 % + QST 9.975 % (Quebec).
- **One EPC per physical item:** multiple tags can share one product and UPC. Administrators can enter or scan EPCs while receiving stock, or click the UPC / **Manage tags** in inventory to assign them later. The delivery history shows EPCs recorded with each delivery. Sold tags cannot be sold again. Barcode checkout is available for untagged stock; tagged stock must be scanned by RFID so the app knows which physical item was sold.

---

## 7. Project files

```
Phase 3/
├── app.py                 # Flask app: pages, product management, inventory, accounts, RFID read
├── cart.py                # shopping cart API (barcode, RFID scan, remove, reset)
├── checkout.py            # checkout API: membership, simulated payment -> receipts
├── rfid_reader.py         # CF600 reader driver (pyserial) + simulation mode
├── db.py                  # all database functions
├── receipts.py            # receipt text/HTML + email
├── notifications.py       # bilingual notifications (EN/FR) + log
├── database/schema.sql    # tables, relationships, inventory view
├── database/seed.sql      # 5 sample products + initial stock
├── templates/             # account, inventory, add/edit product, receive stock, reception history, cart
├── static/                # CSS + JS for each page (rfid_tag.js = "Read tag" button)
├── docs/ER_diagram.png    # ER diagram (+ .mmd source)
├── test_database.py       # 40 automatic checks of the database/receipt logic
├── ProjectTasksDescriptionPhase3.docx
├── requirements.txt
└── .env.example
```

### API (used by the pages)

| Method | URL | Purpose |
|---|---|---|
| GET | `/api/cart` | Current shopping list and totals |
| POST | `/api/cart/rfid/scan` | Read all tags on the CF600 and add them |
| POST | `/api/cart/rfid` | Add EPCs sent as JSON `{"epcs": [...]}` (testing) |
| POST | `/api/cart/barcode` | Add one item by UPC `{"upc": "..."}` |
| DELETE | `/api/cart/items/<id>` | Remove an item |
| DELETE | `/api/cart` | Reset the cart |
| POST | `/api/checkout` | Pay `{"membership_number", "payment_method", "language"}` → receipt |
| POST | `/inventory/tags/reset` | Admin: make every sold RFID tag available again |
| POST | `/products/<id>/tags/reset` | Admin: make one sold tag (`epc`) or all sold tags of a product available again |
| POST | `/products/<id>/tags/remove` | Admin: remove a tag (`epc`) from a product |
| GET | `/api/rfid/read` | Read one tag's EPC (product form) |
| POST | `/api/account/register` · `/login` · `/logout` | Customer accounts |
| GET | `/api/account/me` · `/history` · `/receipt/<id>` | Profile, purchase history, one receipt |
| GET | `/api/notifications` | Last 20 notifications |

---

## 8. Settings (`.env`)

| Setting | Default | Meaning |
|---|---|---|
| `SMTP_EMAIL`, `SMTP_APP_PASSWORD` | — | Gmail account + 16-letter App Password (no spaces) for receipt emails |
| `STORE_NAME` | Smart Store | Name on receipts |
| `LOW_STOCK_LIMIT` | 5 | Low-stock warning level |
| `HOST`, `PORT` | 0.0.0.0, 5002 | `0.0.0.0` lets laptops/phones on the network open the site |
| `FLASK_SECRET_KEY` | random | Keeps logins and carts after a restart |
| `RFID_PORT` | /dev/ttyUSB0 | CF600 serial port |
| `RFID_SCAN_SECONDS` | 2 | How long one scan reads for |
| `RFID_SIMULATE` | 0 | `1` = no reader, use `RFID_SIMULATED_TAGS` |
| `RFID_REUSE_SOLD_TAGS` | 0 | `1` = testing: checkout doesn't mark tags sold, so the same tags can be bought again |

---

## 9. Demo script

1. **Before class:** start `python app.py`. Receive stock and assign each item's real EPC through **Manage tags** or the receive-stock form. Existing product EPCs are migrated automatically.
2. **Admin** (`/inventory`): add a product with its UPC, receive stock, assign individual EPCs, and show reception history. Edit a price or delete a test product.
3. **Customer account** (`/`): create an account → membership number shown. Switch to **FR** and back.
4. **Self-checkout** (`/cart`): put 3 tagged items on the reader → **Scan all items** → all 3 appear at once. Scan one more with the barcode scanner. **Remove** one item. Enter the membership number → **Proceed to payment** → receipt on screen.
5. Show the **receipt email** in the inbox, then the customer portal: **points** went up and the receipt is in **Purchase history**.
6. Back on `/inventory`: **Sold** and **In stock** have changed.

### Troubleshooting

| Message | Fix |
|---|---|
| "No RFID tags detected" / `(no tags)` | Hold the tags flat on top of the reader. The reader only sees tags within a few cm, so lay the tag flat in the middle of the reader. Stop the app and run `python rfid_reader.py --raw`. If you see `cf 01 00 01 01 12` frames but no EPCs, the reader is working and the tag is out of range. If **nothing at all** comes back, check `RFID_PORT` and unplug/replug the reader. |
| "RFID reader not found on /dev/ttyUSB0" | Reader unplugged, or the usbserial setup wasn't done. Check `ls /dev/ttyUSB*`. |
| "No permission to open /dev/ttyUSB0" | Run `sudo usermod -aG dialout $USER`, then log out and in. |
| "Unknown RFID tag(s)" | That tag isn't registered. Assign it through **Manage tags** (see section 4). |
| "Already sold: …" | That tag was sold in an earlier checkout. Assign it again in **Manage tags**, or set `RFID_REUSE_SOLD_TAGS=1` while testing. |
| "The receipt could not be emailed" | Check `SMTP_EMAIL` / `SMTP_APP_PASSWORD` in `.env`; the purchase is still saved. |
| Page won't open from a laptop | Same network as the Pi? Use `http://<pi-ip>:5002` and `HOST=0.0.0.0`. |

### Tests

Checkout retries use a unique cart identity saved with the purchase, so retrying
the same cart returns the original sale without deducting stock or awarding
points again. Existing databases gain this field automatically on startup.
If receipt, notification, or email processing fails after a sale is saved, the
checkout returns success with a warning. Failed email delivery is not retried
automatically.

At checkout, a membership number alone shows only that number and points earned
on this purchase. The signed-in account owner can also see their name and points
balance. Email receipts retain the full receipt details. The store-wide
notification log requires administrator access. EN/FR switches save the language
preference for signed-in customers; an explicit checkout language takes priority.

```bash
python test_database.py                          # 40 checks of the database, receipts, notifications
python -m unittest -v test_checkout               # checkout retries, privacy, failures, stock, language, migration
python test_database.py --email you@gmail.com    # also sends a real receipt email
```
