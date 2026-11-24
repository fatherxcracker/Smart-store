# Smart Store — IoT Project

A semester-long IoT project, built in phases. Each phase lives in its own folder with its own code, dependencies, and setup instructions — you can set up and run any phase on its own without needing the others.

## Phases

| Phase | Folder | What it does |
|---|---|---|
| Phase 1 | [`Phase 1/`](./Phase%201/README.md) | Customer registration page (HTML/CSS/JS + Flask + SQLite) with a Raspberry Pi 5, blue/red LEDs and a buzzer signalling success/failure. |
| Phase 2 | [`Phase 2/`](./Phase%202/README.md) | IoT fridge-monitoring dashboard: two ESP32 + DHT11 sensors publish temperature/humidity over MQTT to a Raspberry Pi broker, a Flask dashboard displays live gauges, sends an email alert when a fridge overheats, and turns on a fan (DC motor) when you reply YES to the email. |
| Phase 3 | [`Phase 3/`](./Phase%203/README.md) | Smart self-checkout: product and inventory management, a checkout that reads all items at once with a CF600 RFID reader (or a barcode scanner), simulated payment, loyalty points, receipts emailed automatically, and a bilingual (EN/FR) customer portal. |
| Phase 4 | [`Phase 4/`](./Phase%204/README.md) | **The complete system** (Phases 2 + 3 + reports): dashboard, inventory / sales / customer reports, customer purchase history with price charts, CSV export, per-category stock alerts, EN/FR and the Minew MSP01 sensor. **[Setup and run instructions](./Phase%204/README.md#run-it)** |

Open each phase's own README for its full setup, wiring, and run instructions.

## Phase 4: the complete system

[`Phase 4/`](./Phase%204/README.md) is the final, self-contained application (port 5003): Phase 2 fridge monitoring
(email reply YES -> fan), the Phase 3 store (RFID stock, checkout, receipts, users) and the Phase 4 dashboard,
inventory / sales / customer reports, customer purchase reports with price history, CSV export, per-category
stock alerts, EN/FR and the Minew MSP01 sensor widgets. Demonstrate this one.

**How to set it up and run it:** see [Phase 4 README, "Run it"](./Phase%204/README.md#run-it) (Raspberry Pi and Windows steps, `.env` settings, test accounts).
The teacher's requirements are in `Phase 4/docs/Phase-4-.pdf`.

## Repo layout

```
Smart-store/
├── README.md              <- you are here
├── Phase 1/                <- self-contained: own venv, own requirements.txt
├── Phase 2/                <- self-contained: own venv, own requirements.txt
├── Phase 3/                <- self-contained: own venv, own requirements.txt
└── Phase 4/                <- the complete system (Phases 2 + 3 + reports + sensor), port 5003
```

Each phase folder is independent — different `requirements.txt`, different virtual environment, different Flask app running on a different port (Phase 1 on 5000, Phase 2 on 5001, Phase 3 on 5002, Phase 4 on 5003), so you can `cd` into any one and run it without the other phases needing to exist or run at the same time.
