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
| UHF RFID tags | One per product | The EPC links each tag to a product |

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

---

## 4. How each requirement is covered

### Product management (admin) — `/inventory`
- **Register / edit / delete** products with name, category, price, **UPC** (≤ 13), **EPC** (≤ 24) and producer.
- **UPC via barcode scanner:** click the UPC field and scan.
- **EPC via the RFID reader:** put one tag on the reader and click **Read tag from RFID reader**; the EPC is filled in. The app warns if 0 or several tags are on the reader, or if the tag already belongs to another product.
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
7. A **receipt** is shown on screen and **emailed automatically** to the member's email, in the member's language.

### Customer accounts — `/`
- **Create an account:** name, email, password, optional phone. A **membership number** (e.g. `SS-48213907`) is generated automatically.
- **Log in** to see the membership card, **total points** and **purchase history**; each past receipt can be opened.
- **Bilingual:** EN/FR switch (bonus). The choice also sets the language of the checkout notifications and receipt.

### Receipts and notifications
- The **receipt** has the product list (name, quantity, unit price, amount), subtotal, GST, QST, **total**, payment method, **points earned**, the member's total points and the **date and time**.
- **Notifications** appear after every action: product added/updated/deleted, stock received, item scanned/removed, payment approved, checkout completed, receipt emailed, account created, login, errors. Every notification is also saved in the `notifications` table (`/api/notifications` shows the last 20).

---

## 5. Database design

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
- **One EPC per product** (as in the spec). Each physical tag has its own EPC, so for the demo use one tagged item per product; scanning the same tag again doesn't add it twice.

---

## 6. Project files

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
| GET | `/api/rfid/read` | Read one tag's EPC (product form) |
| POST | `/api/account/register` · `/login` · `/logout` | Customer accounts |
| GET | `/api/account/me` · `/history` · `/receipt/<id>` | Profile, purchase history, one receipt |
| GET | `/api/notifications` | Last 20 notifications |

---

## 7. Settings (`.env`)

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

---

## 8. Demo script

1. **Before class:** delete `smartstore.db`, then `python app.py`. Use **Read tag from RFID reader** on each sample product's **Edit** page so the products have your real tags' EPCs (or register new products).
2. **Admin** (`/inventory`): add a product, scanning its barcode into UPC and reading its tag into EPC → notification. Edit its price → notification. **Receive stock** for it → stock goes up. Show **Reception history**. Delete a test product.
3. **Customer account** (`/`): create an account → membership number shown. Switch to **FR** and back.
4. **Self-checkout** (`/cart`): put 3 tagged items on the reader → **Scan all items** → all 3 appear at once. Scan one more with the barcode scanner. **Remove** one item. Enter the membership number → **Proceed to payment** → receipt on screen.
5. Show the **receipt email** in the inbox, then the customer portal: **points** went up and the receipt is in **Purchase history**.
6. Back on `/inventory`: **Sold** and **In stock** have changed.

### Troubleshooting

| Message | Fix |
|---|---|
| "No RFID tags detected" / `(no tags)` | Hold the tags flat on top of the reader. Run `python rfid_reader.py --raw`: if it shows **received 0 bytes**, the reader isn't answering (check `RFID_PORT`, unplug/replug, try `RFID_RESPONSE_WAIT=0.8` in `.env`); if bytes arrive but no EPCs, send the output to the team. |
| "RFID reader not found on /dev/ttyUSB0" | Reader unplugged, or the usbserial setup wasn't done. Check `ls /dev/ttyUSB*`. |
| "No permission to open /dev/ttyUSB0" | Run `sudo usermod -aG dialout $USER`, then log out and in. |
| "Unknown RFID tag(s)" | That tag isn't registered. Read it into a product with **Read tag from RFID reader**. |
| "The receipt could not be emailed" | Check `SMTP_EMAIL` / `SMTP_APP_PASSWORD` in `.env`; the purchase is still saved. |
| Page won't open from a laptop | Same network as the Pi? Use `http://<pi-ip>:5002` and `HOST=0.0.0.0`. |

### Tests

```bash
python test_database.py                          # 40 checks of the database, receipts, notifications
python test_database.py --email you@gmail.com    # also sends a real receipt email
```
