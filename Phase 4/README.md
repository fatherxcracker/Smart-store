# Smart Store - Phase 4

Reporting, BLE monitoring and final integration workspace.

## Current status

This is the initial folder structure and a runnable landing page. Reporting
queries, authentication integration, charts, BLE decoding and live widgets are
not implemented yet. The starter app does not read, write or migrate any database,
start hardware, send emails or launch earlier phases.

## Layout

```text
Phase 4/
  app.py                      Flask entry point, port 5003
  config.py                   Local settings and shared database paths
  requirements.txt            Starter dependencies
  .env.example                Configuration template
  reports/
    inventory.py              Admin inventory reporting workspace
    sales.py                  Admin sales reporting workspace
    customers.py              Admin customer activity reporting workspace
    purchases.py              Customer history/search/price reporting workspace
  sensors/
    minew_msp01.py            BLE receiver/decoder workspace
  database/
    schema.sql                Reserved for Phase 4 sensor storage
  templates/
    index.html                Starter page
  static/css/
    style.css                 Starter page styling
  docs/
    Phase-4-.pdf              Teacher's Phase 4 requirements
```

## Run on Windows

From the project root:

```powershell
cd "Phase 4"
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\venv\Scripts\python.exe app.py
```

Copy `.env.example` only on initial setup; keep an existing `.env` when restarting.
Open http://localhost:5003. No sensor is needed to view the starter page.

On the Raspberry Pi, use `python3 -m venv venv`, `venv/bin/python -m pip install
-r requirements.txt`, `cp .env.example .env` (first setup only), and
`venv/bin/python app.py`. Set `HOST=0.0.0.0` in `.env` for access from other devices.

## Existing files and integration

No existing repository files were exclusively Phase 4. Phase 3 user management,
inventory, receipts and checkout remain in Phase 3 because they are used there.
Phase 2 fridge monitoring remains in Phase 2. The requirements PDF was copied
from Downloads; the original was preserved.

The future reports should reuse the existing Phase 3 business database rather
than create another store database. `PHASE3_DATABASE_PATH` defaults to
`../Phase 3/smartstore.db`, resolved from this folder. Merely setting this path
does not connect either application or share their login sessions.

## Implementation order

1. Integrate Phase 3 authentication and shared database access.
2. Implement admin inventory, sales and customer activity reports with date filters.
3. Implement customer receipt filters, spending totals, product search and price charts.
4. Configure and receive Minew MSP01 BLE data; add live dashboard widgets.
5. Connect existing monitoring and checkout navigation into a complete demo.
6. Verify access controls, report totals, date boundaries and hardware updates.

See `docs/Phase-4-.pdf` for the required features and optional enhancements.
