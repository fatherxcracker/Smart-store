# Smart Store - Phase 4

Phase 3 accounts, inventory, RFID checkout and Phase 4 reports run in one Flask
application on port 5003. Phase 4 imports the existing store code and uses the
existing database, without maintaining duplicate store files.

## Implemented

- Administrator inventory report with category filters, stock levels, delivery dates and live refresh.
- Sales reports by day or date range: sold quantities, top/bottom N products,
  total paid, net sales, discounts, taxes and daily charts.
- Customer activity: distinct purchasing members, new/returning classifications,
  guest order counts, busiest/quietest days and daily charts/tables.
- Customer reports: dated receipt history, period spending, product search,
  purchase counts, historical unit prices and a product price-history chart.
- Existing login sessions and administrator checks protect all reports.
- Reports refresh every five seconds and support browser printing / Save as PDF.
- Mobile layouts and tables work without external chart libraries or CDN access.

## Run on Windows

From the repository root:

```powershell
cd "Phase 4"
```

First-time setup on another computer (a local environment has already been
created in this workspace):

```powershell
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Do not overwrite an existing `.env`. Start the integrated app:

```powershell
.\venv\Scripts\python.exe app.py
```

Open http://localhost:5003, sign in using an existing store account, and click
**Reports**. Administrators see all reporting tabs; customers see only their
personal purchase reports. The root page is the existing customer portal.
Do not open the Phase 3 port to log in for Phase 4: use port 5003 throughout.
Phase 3 does not need to run separately. Restart an already running Phase 4 server
after the integration update so it uses the existing Phase 3 code and database.
No app is started automatically by tests.

On the Pi, use `python3 -m venv venv`, install with
`venv/bin/python -m pip install -r requirements.txt`, and run
`venv/bin/python app.py`. Set `HOST=0.0.0.0` for LAN access.

## Database and configuration

- `PHASE3_DATABASE_PATH` defaults to `../Phase 3/smartstore.db`, resolved from
  this folder. Set an absolute path in `.env` to use another database.
- Startup runs Phase 3's normal database initialization and migrations. A missing
  database is created with Phase 3 demo data. Back up store data before deployment.
- Reports only read data. Checkout and account actions use the existing store
  functions and database, so reports reflect the same purchases and inventory.
- The unused local `database/smartstore.db` snapshot from the earlier standalone
  setup is preserved as a backup, ignored by Git, and not opened by this app.
- `REPORT_TIMEZONE` defaults to `America/Toronto`. Filter days include the entire
  local day, with UTC database boundaries accounting for daylight saving.
- Maximum report period is 366 days, including both endpoints.
- Receipt email settings load from Phase 3's `.env`; values in Phase 4's `.env`,
  when present, take precedence. A configured `FLASK_SECRET_KEY` keeps sessions
  stable across restarts.

## Report definitions

- Net sales = receipt subtotal minus redeemed points discounts, before tax.
  Total paid includes GST/QST. Product sales use historical item amounts before
  points discounts and tax. These are clearly labelled and are not interchangeable.
- Products with zero sales appear in rankings. Deleted products remain in
  historical sales reports if sold during the period. Product names/categories
  in admin rankings reflect the current product record; customer receipt lines
  retain the original purchased name and price.
- Customers are distinct linked accounts that purchased in the period, not
  physical visitors. New means no purchase before the period; returning means
  a prior purchase. A member appears in only one classification per period.
- Guest orders and orders from deleted accounts are reported separately, because
  they cannot be reliably assigned to distinct people. Zero-purchase days and
  ties are included in busiest/quietest day results.
- Personal total spending covers all receipts in the selected date period.
  Product/name filters narrow matching items and receipts, not that period total.
  Purchase count means distinct matching receipts; units are counted separately.
- Product price charts show the actual historical unit price before order-level
  points discounts and tax, rather than today's catalog price.

## Files

- `app.py`, `config.py`: integrated startup and settings.
- Phase 3 store modules, templates and static assets are imported in place.
  Small compatibility changes there allow configured database paths and report links.
- `reports/common.py`: read-only database snapshots and date handling.
- `reports/inventory.py`, `sales.py`, `customers.py`, `purchases.py`: report queries.
- `reports/__init__.py`: authenticated routes and page rendering.
- `templates/reports/`, `static/css/reports.css`, `static/js/reports.js`: report UI,
  charts, mobile layout and refresh logic.
- `test_reports.py`: temporary-database integration tests.
- `docs/Phase-4-.pdf`: assignment requirements.

## Tests

```powershell
.\venv\Scripts\python.exe -m unittest -v test_reports
```

Tests use temporary databases, not the real store. They do not send email or
access hardware. Run the original store regression tests from Phase 3 as well:

```powershell
cd "../Phase 3"
.\venv\Scripts\python.exe -m unittest -v test_checkout
.\venv\Scripts\python.exe test_database.py
```

## Still pending

- Minew MSP01 BLE receiver/decoder, sensor observation storage and live widgets.
  The sensor and Raspberry Pi are not currently available, so the module remains
  a placeholder; simulated or real sensor readings are not presented as working.
- Phase 2 fridge monitoring integration with the combined dashboard.
- French translations for the new reporting pages (the existing store portal
  remains bilingual), optional CSV export and configurable category stock alerts.
- Final end-to-end checks using physical RFID, BLE sensors and actual receipt email.
