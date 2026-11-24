# Smart Store - Phase 4 (complete system)

One Flask application on **port 5003** that contains everything built so far:

| Phase | What it contributes | Where it lives |
|---|---|---|
| 2 | Fridge monitoring: ESP32 + DHT11 -> Mosquitto -> temperature email -> reply **YES** -> fan (L293D + PWM) | `monitoring/`, `esp32/` |
| 3 | Accounts, loyalty points, inventory, RFID stock (one EPC per item), self-checkout, receipts, EN/FR notifications | `storefront.py`, `db.py`, `cart.py`, `checkout.py`, `receipts.py`, `notifications.py`, `rfid_reader.py` |
| 4 | Dashboard, admin + customer reports, CSV export, per-category stock alerts, Minew MSP01 BLE sensor | `reports/`, `sensors/`, `templates/`, `static/` |

The folder is **self-contained**: it does not import code from `Phase 2/` or `Phase 3/`.
One login, one SQLite database (`smartstore.db`), one set of notifications.

## What the Phase 4 task asks for, and where it is

| Requirement | Where |
|---|---|
| 2.1 Inventory report: available items per product, real-time, last restocked | **Reports > Inventory**. Refreshes every 5 s, so a purchase shows up without reloading. |
| 2.1 Stock-level alerts, customizable per category; colour levels | Same page, "Low-stock limit per category". Red = fewer than the limit, yellow = fewer than twice the limit, green = otherwise. The checkout sends a low-stock notification using the category's limit. |
| 2.2 Sales report: sold items per product in a range, most / least sold, total for a day or a range | **Reports > Sales** (a single day = same start and end date). Top/bottom N, daily line chart, taxes, discounts. |
| 2.3 Customer activity: customers per day / range, new vs returning, busiest / quietest day | **Reports > Customer activity** |
| 3.1 Receipt history per day or period (date and time, items, prices, total) | **My purchases** (customer) |
| 3.2 Total spent in a selected period | **My purchases**. The "Spending over time" chart is optional. |
| 3.3 Search purchase history, times bought, dates and prices, inflation diagram | **My purchases**: search box, product selector, "Inflation report: price history" chart |
| 4.1 GUI style, responsive | One design for the Phase 4 pages, mobile layouts, keyboard focus styles |
| 4.2 Notifications | Low-stock alerts, purchase confirmations, fridge alerts, error messages (EN/FR for the store). Everything is in **Manage inventory > Notifications** and on the dashboard. |
| Bilingual EN / FR | EN / FR switch on every Phase 4 page, shared with the store portal's language choice (also saved on the account for receipt emails) |
| 4.4 Extras | **CSV download** on every report, print / save as PDF, dashboard widgets |
| 5 Minew MSP01 sensor + dashboard widgets | **Reports > Dashboard** (live tiles) and **MSP01 sensor** page (charts, motion log) |
| 6 Final demonstration | Demo script below |

## Run it

### Raspberry Pi

```bash
cd ~/Smart-store/"Phase 4"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then edit .env (Gmail App Password, PUBLIC_BASE_URL, ...)
python app.py
```

Open `http://<pi-ip>:5003`. The first start creates `smartstore.db` with the sample products (0 in stock) and the demo accounts.

Mosquitto must be running for the fridges (`sudo systemctl status mosquitto`), and the ESP32 sketches in `esp32/` publish to topics `Frig1` and `Frig2` (wiring and Wi-Fi setup: `Phase 2/README.md`). The app still starts without the broker; the fridge tiles just say "Waiting for data".

### Windows (testing without hardware)

```powershell
cd "Phase 4"
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\venv\Scripts\python.exe app.py
```

Set `RFID_SIMULATE=1` and `MSP01_SIMULATE=1` in `.env` to demo without the reader or the sensor.

### Repeatable local demo

From `Phase 4`, run `python demo.py` and open `http://127.0.0.1:5007`. The command
uses a temporary database, leaves the regular store database alone, and starts
without real email or hardware services. Stop it with Ctrl+C and run it again
to restore the same starting stock and sample history.

- Sign in as John using the demo account below. At Self-checkout, click **Scan RFID**.
  One Coca-Cola and one Lay's appear. Use John's membership number `SS-00000002`
  and choose **Cash** for the simulated purchase.
- As admin, confirm each item's stock drops from one to zero and today's sales
  show one unit of each product. As John, find the same receipt in Purchase History.
- In **My purchase reports**, select **Demo Coffee**. The inflation chart starts
  with three historical prices, including two purchases on the same day. Open
  **View price history table** to see each timestamp and price.
- The MSP01 page receives fresh simulated readings every five seconds.

### Accounts (new database only)

| Role | Email | Password |
|---|---|---|
| Administrator | `admin@smartstore.local` | `eUL1b-l0PhnHW9WDo8A6Dw` |
| Customer | `john@gmail.com` | `123456` |

For testing only. Create real accounts and change these passwords before any real use (Manage inventory > User management).

### Moving your Phase 3 data

Phase 4 uses `Phase 4/smartstore.db`. To keep the accounts, products and RFID tags you already have, stop both apps and copy the file: `cp "../Phase 3/smartstore.db" smartstore.db`. The new tables are created automatically on start. Otherwise start fresh and receive your tags again (Manage inventory > Receive stock).

## Pages

Administrators get **one page that holds everything**: `/reports/` (the "Reports" link in the store header). A left menu switches the content with no page reload, in the same blue/black look as the store, with the EN/FR language switch at the top.

| Menu entry | What opens inside the dashboard |
|---|---|
| Store overview | sales today, low stock, both fridges, fan, MSP01 sensor, recent notifications |
| Inventory report / Sales / Customer activity | the reports (filters, charts, Download CSV, per-category low-stock limits) |
| Fridges & fan | live temperature and humidity, limits, fan control, alerts |
| MSP01 sensor | temperature, humidity, light, motion, status |
| Products & stock | add/edit products, receive stock, RFID tags, reception history |
| Users | accounts, points, roles |
| Notifications | the last 100 store events |

The store header places the Smart Store logo on the left and EN/FR and Self-checkout on the right. Guests can sign in from the header, and signed-in users can log out there. Administrators who sign in land on `/reports/`. Opening a report URL directly (for example `/reports/sales`) lands in the matching dashboard section.

The customer dashboard shows the membership card and loyalty points. Its header opens Purchase history, My purchase reports, My profile, and Self-checkout.

Every report accepts `?format=csv` (the "Download CSV" link). Sales and customer reports also have the daily table as CSV (`&table=daily` for sales).

## The fridge alert flow (Phase 2)

1. A DHT11 reading above the fridge's limit creates an alert and sends an email (subject ends with `[ref:...]`). At most one email per fridge every `ALERT_COOLDOWN_SECONDS`.
2. **Reply YES** to the email: the Pi reads the Gmail inbox (IMAP, every `IMAP_POLL_SECONDS`) and turns the fan on. **Reply NO**: nothing happens. Only the address in `ALERT_RECIPIENT_EMAIL` can answer, and each alert can be answered once.
3. The email also contains backup YES/NO links (`PUBLIC_BASE_URL`, must be reachable from your phone).
4. Temperature limits, the fan switch and the PWM speed slider are on **Fridges & fan**. All events also appear in the store's notification log.

## Minew MSP01 sensor (temperature, humidity, light, motion)

1. Configure the sensor with the **BeaconSET+** app so it advertises temperature, humidity, illuminance and motion. The reelyActive guide describes the steps: https://reelyactive.github.io/diy/minew-msp01-config/
2. Get its readings into the app in any one of these ways:
   - **Bluetooth on the Pi**: `MSP01_BLE=1` (optionally `MINEW_DEVICE_ADDRESS=AA:BB:...`). `sensors/minew_msp01.py` decodes Minew's service data. It decodes **battery, temperature and humidity** of the Minew info frame; **check it against your own sensor** (for example with the nRF Connect phone app) before relying on it. Light and motion are not decoded from raw frames yet.
   - **MQTT**: publish JSON such as `{"temperature":21.5,"humidity":44,"light":320,"motion":1,"battery":90}` to topic `MSP01`.
   - **HTTP**: `POST /sensors/api/ingest` with the same JSON and header `X-Sensor-Token: <SENSOR_INGEST_TOKEN>` (for a gateway or reelyActive pipeline).
3. No sensor at hand: `MSP01_SIMULATE=1` produces believable values so the widgets can be demonstrated. The page then shows the source of each reading as `simulator` in the database (`sensor_readings.source`).

A sensor with no reading for `SENSOR_STALE_SECONDS` is shown as **Offline (stale)**, never as a live value.

## Demo script (about 10 minutes)

1. **Inventory management**: log in as admin > Manage inventory > Receive stock: read a tag with the CF600 (one tag at a time). The inventory report shows +1.
2. **Purchasing workflow**: open `/cart` in another window, scan the items, pay. Watch **Reports > Inventory** drop by one without reloading, and a low-stock notice appear when the category limit is crossed. Change the Dairy limit to 10 to show the colours change.
3. **Data synchronization**: the Dashboard shows today's sales and customers from that purchase within 5 seconds.
4. **Admin reports**: Sales (top/bottom, daily chart, CSV), Customer activity (new vs returning, busiest day).
5. **Customer reports**: log in as a customer > My purchases: receipts, spending chart, search an item, pick it and show the inflation chart (change a product price in between to show a different price).
6. **Fridges and sensor**: warm a DHT11 with your hand, show the email, reply YES, watch the fan start. Show the MSP01 tiles and the motion log.
7. **Polish**: resize the window, download a CSV, show French in the store portal.

## Database

Phase 3 tables (customers, products, product_tags, receptions, purchases, purchase_items, notifications, the `inventory` view) plus:

| Table | Purpose |
|---|---|
| `category_thresholds` | low-stock limit per category |
| `fridge_thresholds`, `fridge_alerts`, `fridge_readings` | Phase 2 limits, alert emails and their answers, history for the charts (kept 7 days) |
| `sensor_readings` | MSP01 readings (kept 7 days) |

See the [Phase 4 ER diagram](docs/ER_diagram.png) and its [Mermaid source](docs/ER_diagram.mmd). Stock is calculated from unsold product tags, and the monitoring tables store fridge and MSP01 readings.

## Report definitions

- Net sales = receipt subtotal minus redeemed points discounts, before tax. Total paid includes GST/QST. Product sales use the item amounts at purchase time, before points discounts and tax. They are labelled and are not interchangeable.
- Products with zero sales appear in rankings. Deleted products remain in historical reports if sold in the period.
- Customers are distinct linked accounts that purchased in the period (not physical visitors). New = no purchase before the period; returning = a prior purchase. Guest orders are counted separately. Zero-purchase days and ties are included in busiest/quietest day results.
- Personal total spending covers all receipts in the selected period. Product/name filters narrow the matching items and receipts, not that total.
- Price charts show the unit price actually paid, not today's catalog price.
- Days include the whole local day in `REPORT_TIMEZONE` (default `America/Toronto`). Maximum period: 366 days.
- Stock = number of unsold RFID tags of the product (every item has its own EPC).

## Tests

```bash
python -m unittest -v test_reports test_phase4 test_checkout
python test_database.py                                         # 53 checks
```

They use temporary databases and never send email, open the MQTT broker, drive the GPIO pins or use Bluetooth.

## Known limits

- Not yet tested with the physical hardware in this combined app (CF600, DHT11 boards, fan, MSP01). The pieces come from Phases 2 and 3, which were tested separately.
- Raw Bluetooth decoding of the MSP01 is partial (see above).
- French on the Phase 4 pages comes from a phrase list in `static/i18n.js`; a new text added later shows in English until it is added there. Product names and server error pages (401/403) are not translated. CSV column names stay in English.
- `Phase 2/` and `Phase 3/` still run on their own (ports 5001 and 5002). Phase 4 is the version to demonstrate.
