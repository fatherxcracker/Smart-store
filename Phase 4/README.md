# Smart Store - Phase 4

Copies of the store accounts, inventory and RFID checkout run with Phase 4
reports in one application on port 5003. All code, templates, assets and business
data used by Phase 4 live inside this folder. Earlier phases are unchanged.

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

Open http://localhost:5003, sign in using an account in the copied database, and click
**Reports**. Administrators see all reporting tabs; customers see only their
personal purchase reports. The root page is the existing customer portal.
Do not open the Phase 3 port to log in for Phase 4: use port 5003 throughout.
Phase 3 does not need to run separately. Restart an already running Phase 4 server
after this isolation update so it switches from the earlier shared configuration
to its own code and database. No app is started automatically by tests.

On the Pi, use `python3 -m venv venv`, install with
`venv/bin/python -m pip install -r requirements.txt`, and run
`venv/bin/python app.py`. Set `HOST=0.0.0.0` for LAN access.

## Database and configuration

- The default database is `Phase 4/database/smartstore.db`. A one-time, consistent
  snapshot was copied from Phase 3's database using a read-only source connection.
  It preserves the accounts and purchases present when copied. No `.env` secrets
  were copied. The database is local and ignored by Git.
- This is an independent copy: purchases, points, passwords, products and stock
  changes are not synchronized with earlier phases.
- `PHASE4_DATABASE_PATH` optionally selects another Phase 4 database, relative to
  this folder or absolute. Paths inside Phases 1-3 are rejected. The old
  `PHASE3_DATABASE_PATH` setting is no longer used; remove it from any local `.env`.
- Startup runs the copied store initialization against Phase 4's database only.
  If absent, a new database is created with the copied demo seed. On another
  computer, copy the desired database into `database/smartstore.db` before first
  startup if you want to preserve existing data.
- Reports only read data. The copied checkout, inventory and account functions
  update Phase 4's database, never a previous phase's database.
- `REPORT_TIMEZONE` defaults to `America/Toronto`. Filter days include the entire
  local day, with UTC database boundaries accounting for daylight saving.
- Maximum report period is 366 days, including both endpoints.
- Set receipt email credentials in Phase 4's own `.env`. Earlier phases' `.env`
  files are not loaded. A configured `FLASK_SECRET_KEY` keeps sessions stable
  across restarts.

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
- `store/`: Phase 4's independent copies of the store Python modules, templates,
  static assets, schema, seed and regression tests. Source: Phase 3, with
  Phase 4-specific database configuration and reporting navigation applied only
  to these copies. Future updates must be made here, not in earlier phases.
- `database/smartstore.db`: Phase 4's local business database (Git-ignored).
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
access hardware. The copied store regression tests can also be run without
opening the original phase:

```powershell
cd store
..\venv\Scripts\python.exe -m unittest -v test_checkout
..\venv\Scripts\python.exe test_database.py
```

## Still pending

- Minew MSP01 BLE receiver/decoder, sensor observation storage and live widgets.
  The sensor and Raspberry Pi are not currently available, so the module remains
  a placeholder; simulated or real sensor readings are not presented as working.
- Phase 2 fridge monitoring integration with the combined dashboard.
- French translations for the new reporting pages (the existing store portal
  remains bilingual), optional CSV export and configurable category stock alerts.
- Final end-to-end checks using physical RFID, BLE sensors and actual receipt email.
