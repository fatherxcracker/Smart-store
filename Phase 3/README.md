# Smart Store — Phase 3: Smart Self-Checkout

A web-based smart store running on the Raspberry Pi: product and inventory management, a self-checkout that reads **all items at once with the CF600 RFID reader** (items are sold only by their RFID tag, never by barcode), simulated payment, loyalty points, receipts emailed automatically, and a bilingual (EN/FR) customer portal.

| Page | URL | Who uses it |
|---|---|---|
| Customer portal | `http://<pi-ip>:5002/` | Customers: create an account, log in, see points + purchase history (EN/FR) |
| Inventory dashboard | `http://<pi-ip>:5002/inventory` | Admin: add / edit / delete products, receive stock, reception history |
| Self-checkout | `http://<pi-ip>:5002/cart` | Customers: scan, review list, remove items, membership card, pay, receipt |
| User management | `http://<pi-ip>:5002/admin/users` | Admin: see every account, edit details, set points, reset passwords, manage admin roles, delete accounts |

The pages link to each other in their navigation bars; admins open **User management** with **Manage Users** on the Inventory page.

---

## 1. Hardware

| Device | Connected to | Used for |
|---|---|---|
| Chafon **CF600** UHF RFID reader, in **CDC mode** | Pi USB port | Checkout: reading every tag on the reader at once. Receiving stock: reading **one** tag at a time |
| USB **barcode scanner** | The computer showing the page | Only for **registering a product's UPC** on the add/edit product form (it types like a keyboard). Not used at checkout. |
| UHF RFID tags | One per physical item | **Every item in stock has its own tag.** Each unique EPC links one item to a product |

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

**The CF600 must be in CDC mode** (USB serial, also called "USB virtual COM port"). In CDC mode the app asks the reader for tags, so every scan is controlled: receiving stock reads exactly one tag per click and the same tag is never counted twice. In **keyboard (HID) mode** the reader types EPCs over and over into whatever field has the cursor; the app ignores those typed tags and shows a red warning *"The RFID reader is in keyboard (HID) mode"*.

The USB mode is a setting saved **inside the reader** (it stays after unplugging), so it only needs to be set once:

1. On a Windows PC, open the Chafon configuration tool (UHF reader demo software from the class SDK) with the reader plugged in.
2. In the device / communication parameters, set the USB (output) mode to **CDC** (USB virtual COM), not **HID / Keyboard**, and click **Set**.
3. Unplug the reader and plug it into the Pi.

Then on the Pi:

```bash
# 1. Load the USB-serial driver for the CF600 automatically at every boot
#    (some readers show up as /dev/ttyACM0 by themselves in CDC mode; this covers the others)
echo "usbserial" | sudo tee /etc/modules-load.d/cf600.conf
echo "options usbserial vendor=0x0483 product=0x5750" | sudo tee /etc/modprobe.d/cf600.conf

# 2. Allow your user to open the serial port without sudo
sudo usermod -aG dialout $USER

sudo reboot
```

After the reboot, check it:

```bash
ls /dev/ttyACM* /dev/ttyUSB*    # the reader's CDC serial port, e.g. /dev/ttyACM0 or /dev/ttyUSB0
cd ~/Smart-store/"Phase 3" && source venv/bin/activate
python rfid_reader.py           # prints "Reading from /dev/ttyACM0 (CDC mode)" then the EPCs (Ctrl+C to stop)
```

The app finds the port by itself (`RFID_PORT=auto`). If **no** port shows up, the reader is still in keyboard (HID) mode: set it to CDC (steps above). To force a port, set `RFID_PORT=/dev/ttyACM0` (or `COM5` on Windows) in `.env`.

### No reader (testing on a laptop)

Set `RFID_SIMULATE=1` in `.env`. Reading the reader then returns the tags listed in `RFID_SIMULATED_TAGS`. Receive those EPCs as stock first (Receive stock) so the checkout knows them. Set it back to `0` on the Pi.

---

## 3. Run

```bash
cd ~/Smart-store/"Phase 3"
source venv/bin/activate
python app.py
```

Open `http://<pi-ip>:5002` (find the IP with `hostname -I`), or `http://localhost:5002` on the Pi.

The database `smartstore.db` is created automatically the first time, with 5 sample products and **0 in stock**: stock only exists once each item's RFID tag is received (section 4). To start the demo from a clean database, stop the app and delete `smartstore.db`.

### Test accounts (new databases only)

The initial seed creates these demo accounts:

| Role | Email | Password |
|---|---|---|
| Administrator | `admin@smartstore.local` | `eUL1b-l0PhnHW9WDo8A6Dw` |
| Customer | `john@gmail.com` | `123456` |

These publicly documented credentials are for testing only. Do not use them for a network-accessible or real store. The seed runs when the product database is empty; it does not add accounts to an existing populated database or change existing passwords. To grant an existing account administrator access, log in as an admin and use **Make administrator** on that user's page in **User management** (or run `python manage_admin.py email@example.com` from Phase 3; add `--revoke` to remove access).

---

## 4. Stock = RFID tags (receiving items)

**Every item in stock has its own RFID tag.** Stock is not a number you type: it is the number of tags received for a product that haven't been sold yet. The self-checkout only sells items by their tag, so a product with no tags can't be sold.

### Receive stock (one tag per item)

1. Start the app on the Pi with the CF600 connected (CDC mode) and log in as an administrator.
2. **Inventory → Receive stock**, choose the product.
3. Put **one** item on the reader and click **Read one RFID tag**. Its EPC is added to the list and **Quantity Received** goes up by 1. Repeat for every item.
   - More than one tag on the reader → *"2 tags detected. Put only one tag on the reader."* Nothing is added.
   - A tag already in this delivery, or already on an item in stock → refused, so it's never counted twice.
4. Click **Record Delivery**. The quantity received = the number of tags, and stock goes up by that number.

You can also type or paste EPCs (one per line); the quantity is still counted from the list, and duplicates are refused. A delivery without any EPC is refused.

**Manage tags** (click a product's UPC or **Manage tags** in Inventory) shows every tag of a product. **Add item to stock** there reads one tag and records it as a delivery of 1 item.

### Rules

- EPCs have up to **24 hexadecimal characters** (`0-9`, `A-F`); each identifies one physical item. A product's UPC identifies its type and can have many EPCs.
- **Stock = unsold tags.** Selling an item marks its tag sold (stock −1). Removing a tag from a product takes that item out of stock. Making a sold tag available again puts it back in stock.
- **Checkout is EPC only:** items are added by reading their tags (Scan all items / Auto-scan). There is no barcode checkout; a cart quantity that doesn't match scanned tags can't be paid.
- **A sold tag can't be scanned again.** The cart shows *"Already sold: … (receipt …)"*. To put that tag on a new item, receive it again (Receive stock or Manage tags).
- With `RFID_SIMULATE=1`, the reader returns the EPCs in `RFID_SIMULATED_TAGS`. Receive them as stock first.
- **Testing with the same tags over and over?** Set `RFID_REUSE_SOLD_TAGS=1` in `.env` and restart the app. Checkout then doesn't use up tags (so stock doesn't go down either). Set it back to `0` for the real demo.
- Databases from older versions: stock is now counted from tags, so products that were only received as a number (without tags) show 0 until their tags are received.

### Read EPCs from the terminal (optional)

Stop the app before running `python rfid_reader.py`, because only one program can use the reader at a time. Hold a tag on the reader, copy its EPC, then stop the script, restart the app and paste the EPC into Receive stock.

### Resetting tags (before a demo or after testing)

Log in with an **admin** account. Afterwards click **Reset cart** on `/cart`, so the checkout forgets the tags it already read.

| What you want | Where | Button |
|---|---|---|
| Make **every** sold tag in the store available again (after practice checkouts) | **Inventory** page | **Reset sold RFID tags** (asks to confirm) |
| Make all sold tags of **one product** available again | **Manage tags** of that product | **Make all sold tags available** |
| Make **one** sold tag available again | **Manage tags** → the tag's row | **Make available** |
| **Remove** a tag from a product (e.g. to put it on another product) | **Manage tags** → the tag's row | **Remove** (asks to confirm), then assign it in the other product's **Manage tags** |

Making sold tags available again puts those items back **in stock** (stock = unsold tags); old receipts and the **Sold** column don't change. Removing a tag takes its item out of stock. Every reset/remove shows a notification and is saved in the notifications log.

<details>
<summary>Same thing with SQL commands (optional)</summary>

Run these from the `Phase 3` folder. The app can stay running.

**Make every sold tag available again:**

```bash
sqlite3 smartstore.db "UPDATE product_tags SET sold_purchase_id = NULL;"
```

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

**After a fresh database**, receive your real tags with **Receive stock** (section 4). The sample products start with 0 in stock.

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
- **Register / edit / delete** products with name, **category**, price, **UPC** (≤ 13) and producer. A product is defined once; its items (EPCs) are added by receiving stock.
- **Category from a fixed list:** the category field is searchable (type "bev" → Beverages) and only accepts the store's categories: Bakery, Beverages, Candy, Dairy, Deli, Frozen Foods, Fruits & Vegetables, Health & Beauty, Household, Meat & Seafood, Pantry, Pet Supplies, Snacks, Other (shown in French when the page is in French). Anything else is refused, in the browser and on the server. The list is `CATEGORIES` in `db.py`.
- **UPC via barcode scanner:** click the UPC field and scan.
- **EPC via the RFID reader (CDC mode):** **Receive stock** reads one tag per item; the app refuses 0 or several tags on the reader and tags already in stock.
- Duplicate UPC/EPC and invalid values are rejected with a clear message.
- Deleting a product hides it from the store and inventory, but old receipts that contain it stay correct.

### Inventory
- A product is defined once and **received many times**: **Receive stock** records the EPC of every item received, the quantity (= number of EPCs) and the date/time received (with an optional invoice note).
- **Inventory dashboard:** received, sold and **in stock** for every product (in stock = tagged items not sold yet), plus the last reception date.
- **Reception history**, filterable by product.

### Self-checkout — `/cart`
1. **Scan all products at once:** place the items on the CF600 and click **Scan all items**. Every tag is read in one scan. Tick **Auto-scan** and the list keeps updating by itself every few seconds. A tag that was already read isn't counted twice; unknown tags are ignored with a warning. Items are only added by their RFID tag (no barcode at checkout).
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

### User management (admin) — `/admin/users`
- **All accounts in one table:** name, email, membership number, points, number of purchases, total spent, date joined, and an **Admin** badge. **Search** by name, email, phone or membership number.
- **Add user:** create an account for a customer (with a temporary password), optionally as an administrator.
- **Manage** a user:
  - edit name, email, phone and receipt language
  - set the loyalty **points** balance (corrections)
  - **reset the password**
  - **make administrator / remove administrator access**
  - **delete the account** — their receipts are kept as guest receipts, so sales totals and stock stay correct
  - see their **purchase history** and open any receipt
- **Safety rules:** an admin can't remove their own admin access or delete their own account, and the store always keeps at least one administrator.
- Every action shows a notification (EN/FR) and confirmations appear before role changes and deletion. Only administrators can open these pages.

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
- **Stock is calculated, not stored:** in stock = the product's RFID tags that aren't sold, so it always matches the tagged items on the shelf.
- **Price and name are copied into `purchase_items`** at checkout, so editing a product never changes old receipts.
- **Checkout is one database transaction:** stock check, receipt, items and points are saved together, or not at all.
- **Passwords are hashed**, never stored in plain text.
- **Times are stored in UTC** and shown in local time on every page and receipt.
- **Taxes:** GST 5 % + QST 9.975 % (Quebec).
- **One EPC per physical item:** many tags can share one product and UPC. Receiving stock records each item's EPC (quantity = number of EPCs), and the delivery history shows the EPCs of each delivery. Checkout sells items only by EPC, so the app always knows which physical item was sold; sold tags can't be sold again.
- **Fixed categories:** products use one category from a fixed list (`CATEGORIES` in `db.py`); old free-text categories are mapped to the list on startup.

---

## 7. Project files

```
Phase 3/
├── app.py                 # Flask app: pages, product management, inventory, accounts, RFID read
├── cart.py                # shopping cart API (RFID scan, remove, reset) - EPC only
├── checkout.py            # checkout API: membership, simulated payment -> receipts
├── rfid_reader.py         # CF600 reader driver, CDC/serial mode (pyserial), port auto-detect + simulation mode
├── db.py                  # all database functions
├── receipts.py            # receipt text/HTML + email
├── notifications.py       # bilingual notifications (EN/FR) + log
├── database/schema.sql    # tables, relationships, inventory view
├── database/seed.sql      # 5 sample products (0 in stock until their tags are received) + demo accounts
├── templates/             # account, inventory, add/edit product, receive stock, reception history, product tags, cart,
│                          # users (user management list) + user_detail (one account)
├── static/                # CSS + JS for each page: category_picker.js (searchable categories),
│                          # receive_stock_rfid.js (one tag per item), rfid_keyboard.js (ignores HID-mode typing)
├── docs/ER_diagram.png    # ER diagram (+ .mmd source)
├── test_database.py       # 53 automatic checks of the database/receipt logic
├── test_checkout.py       # 26 checkout tests
├── ProjectTasksDescriptionPhase3.docx   # who did what (open during the demo)
├── ProjectTasksDescriptionPhase3.pdf    # PDF copy of the same document
├── requirements.txt
└── .env.example
```

### API (used by the pages)

| Method | URL | Purpose |
|---|---|---|
| GET | `/api/cart` | Current shopping list and totals |
| POST | `/api/cart/rfid/scan` | Read all tags on the CF600 and add them |
| POST | `/api/cart/rfid` | Add EPCs sent as JSON `{"epcs": [...]}` (testing) |
| DELETE | `/api/cart/items/<id>` | Remove an item |
| DELETE | `/api/cart` | Reset the cart |
| POST | `/api/checkout` | Pay `{"membership_number", "payment_method", "language"}` → receipt |
| POST | `/inventory/tags/reset` | Admin: make every sold RFID tag available again |
| POST | `/products/<id>/tags/reset` | Admin: make one sold tag (`epc`) or all sold tags of a product available again |
| POST | `/products/<id>/tags/remove` | Admin: remove a tag (`epc`) from a product |
| GET | `/api/rfid/read` | Read exactly one tag's EPC (receive stock, Manage tags); refuses 0 or several tags |
| GET / POST | `/admin/users` | Admin: list / search all accounts · create an account |
| GET | `/admin/users/<id>` | Admin: one account (details, points, role, purchases) |
| POST | `/admin/users/<id>/update` · `/points` · `/password` · `/admin` · `/delete` | Admin: edit profile · set points · reset password · grant/remove admin · delete account |
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
| `RFID_PORT` | auto | CF600 CDC serial port: `auto` finds `/dev/ttyACM*`, `/dev/ttyUSB*` or `COMx`; or set one |
| `RFID_SCAN_SECONDS` | 2 | How long one scan reads for |
| `RFID_SIMULATE` | 0 | `1` = no reader, use `RFID_SIMULATED_TAGS` |
| `RFID_REUSE_SOLD_TAGS` | 0 | `1` = testing: checkout doesn't mark tags sold, so the same tags can be bought again |

---

## 9. Demo script

1. **Before class:** check the reader is in **CDC mode** (`python rfid_reader.py` shows the port), start `python app.py`, and **Receive stock** for each product by reading each item's tag.
2. **Admin** (`/inventory`): add a product (search the category list, scan its UPC), then **Receive stock** reading one tag per item: quantity counts up by itself, a duplicate tag is refused. Show the new stock and reception history. Edit a price or delete a test product.
3. **Customer account** (`/`): create an account → membership number shown. Switch to **FR** and back.
4. **Self-checkout** (`/cart`): put 3 tagged items on the reader → **Scan all items** → all 3 appear at once. **Remove** one item. Enter the membership number → **Proceed to payment** → receipt on screen.
5. Show the **receipt email** in the inbox, then the customer portal: **points** went up and the receipt is in **Purchase history**.
6. Back on `/inventory`: **Sold** and **In stock** have changed.
7. **Manage Users** (`/admin/users`): the new customer is listed with their points, purchases and total spent. Open them, show their receipt, adjust points, and make them an administrator (then remove it again).

### Troubleshooting

| Message | Fix |
|---|---|
| "No RFID tags detected" / `(no tags)` | Hold the tags flat on top of the reader. The reader only sees tags within a few cm, so lay the tag flat in the middle of the reader. Stop the app and run `python rfid_reader.py --raw`. If you see `cf 01 00 01 01 12` frames but no EPCs, the reader is working and the tag is out of range. If **nothing at all** comes back, check `RFID_PORT` and unplug/replug the reader. |
| "RFID reader not found … CDC mode" | Reader unplugged, or it's in keyboard (HID) mode, which has no serial port. Set it to **CDC** (section 2) and check `ls /dev/ttyACM* /dev/ttyUSB*`. |
| Red banner "The RFID reader is in keyboard (HID) mode" | The reader is typing tags instead of answering the app. The typed tags were ignored. Set it to **CDC** (section 2). |
| "No permission to open /dev/tty…" | Run `sudo usermod -aG dialout $USER`, then log out and in. |
| "2 tags detected. Put only one tag on the reader." | Receiving reads one item at a time: keep the other tagged items away from the reader. |
| "Tag … is already on an item in stock" | That tag was already received. Use another tag (each item needs its own). |
| "Unknown RFID tag(s)" | That tag was never received. Receive it with **Receive stock** (section 4). |
| "Already sold: …" | That tag was sold in an earlier checkout. Receive it again on a new item, use **Make available**, or set `RFID_REUSE_SOLD_TAGS=1` while testing. |
| "Choose a category from the list." | Pick a category from the suggestions (type a few letters to search). |
| "The receipt could not be emailed" | Check `SMTP_EMAIL` / `SMTP_APP_PASSWORD` in `.env`; the purchase is still saved. |
| Page won't open from a laptop | Same network as the Pi? Use `http://<pi-ip>:5002` and `HOST=0.0.0.0`. |

### Spending loyalty points

Sign in to the account that owns the points. At checkout, enter a whole number
under **Use loyalty points** and click **Apply points** before confirming payment.
Each point reduces the order subtotal by $0.10; taxes are calculated on the
remaining subtotal. You cannot redeem more than your current balance or reduce
the subtotal below zero. New points are earned at 1 point per full dollar of the
remaining subtotal before tax. For example, a $10 subtotal with 20 points redeemed
becomes $8 before tax and earns 8 new points.

Redemption and earnings are saved together with the purchase. Retrying a checkout
does not spend points twice. Receipts show points used and the discount. Existing
receipts default to zero redeemed points when the database migrates on startup.

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
