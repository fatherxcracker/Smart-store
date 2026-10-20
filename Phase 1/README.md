# Smart Store — Phase 1

IoT customer-registration system.

- **Frontend:** HTML / CSS / JavaScript (static files, `fetch()` calls to the backend)
- **Backend:** Python (Flask)
- **Database:** SQLite (`database/smartstore.db`, created automatically)
- **Hardware:** Raspberry Pi 5 — blue LED (success), red LED + buzzer (failure)

## 1. Project structure

```
smart-store/
├── app.py                  # Flask backend: routes, DB, GPIO control
├── requirements.txt
├── database/
│   └── smartstore.db       # created automatically on first run
├── templates/
│   └── index.html          # the page Flask serves
└── static/
    ├── css/style.css
    └── js/script.js        # talks to the backend via fetch()
```

## 2. How it works

1. The customer fills out the form (name, address, phone, email) in the browser.
2. `script.js` sends that data with `fetch()` to `POST /api/customers` — no page reload.
3. `app.py` inserts the row into SQLite.
   - **Success** → blue LED turns on, a blue notification appears, the customer table refreshes.
   - **Failure** (duplicate email, missing field, DB error) → red LED **and** buzzer turn on, a red notification appears.
4. Every attempt (success or failure) is written to a `system_logs` table too, so you have a record of what the hardware did and when — useful for your report/demo.
5. Two seconds later, the frontend calls `/api/hardware/reset`, which turns the LEDs/buzzer back off.

This mirrors the "Data capture → Data communication → Data presentation" flow: the form **captures** data, the fetch/Flask/SQLite round trip **communicates** it, and the notification + live customer table **present** it.

## 3. Running it on your laptop first (recommended)

You don't need the Raspberry Pi to build and test the website. The code detects whether real GPIO hardware is present — if not, it automatically switches to a "mock" mode that just prints `[mock-hardware] BLUE LED -> ON` to the terminal instead of crashing. This means your whole group can develop on their own laptops.

```bash
# 1. Create and activate a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py
```

Open **http://localhost:5000** in your browser. Submit the form — you'll see the notification appear and, in the terminal, lines like:

```
[mock-hardware] BLUE LED (success) -> ON
[mock-hardware] BLUE LED (success) -> OFF
```

That confirms the whole pipeline (frontend → Flask → SQLite → "hardware") works before you touch any wires.

## 4. Running it on the Raspberry Pi 5

### 4.1 Wire the breadboard

| Component | Raspberry Pi 5 GPIO (BCM) | Notes |
|---|---|---|
| Blue LED (long leg / anode) | GPIO 17 | through a ~220–330Ω resistor to GND |
| Red LED (long leg / anode) | GPIO 27 | through a ~220–330Ω resistor to GND |
| Buzzer (active buzzer, + leg) | GPIO 22 | − leg to GND |

General pattern for each LED: `GPIO pin → resistor → LED anode → LED cathode → GND`.
If your buzzer is a passive buzzer instead of active, gpiozero's `Buzzer` still works for simple on/off, just without a tone.

Pin numbers are set at the top of `app.py`:
```python
BLUE_LED_PIN = 17
RED_LED_PIN = 27
BUZZER_PIN = 22
```
Change these to match however you actually wire it.

### 4.2 Install dependencies on the Pi

The Raspberry Pi 5 needs the `lgpio` backend for gpiozero (the older `RPi.GPIO` library does not support the Pi 5's new chip):

```bash
sudo apt update
sudo apt install -y python3-lgpio
python3 -m venv venv --system-site-packages
source venv/bin/activate
pip install -r requirements.txt
```

### 4.3 Run it

```bash
python app.py
```

You should see `[hardware] gpiozero detected real Raspberry Pi GPIO pins.` in the terminal — that confirms it found the real hardware instead of the mock.

From another device on the same network (e.g. your phone), you can visit `http://<raspberry-pi-ip-address>:5000` to use the app from anywhere on your WiFi.

## 5. Database

`database/smartstore.db` is created automatically the first time you run `app.py` — you don't need to run any separate script. It contains two tables:

- **customers** — `customer_id, full_name, address, telephone_number, email_address, created_at`
- **system_logs** — `log_id, customer_email, status, blue_led, red_led, buzzer, message, logged_at` (one row per add attempt, success or failure)

You can inspect it any time with:
```bash
sqlite3 database/smartstore.db "SELECT * FROM customers;"
sqlite3 database/smartstore.db "SELECT * FROM system_logs ORDER BY log_id DESC LIMIT 10;"
```

## 6. API reference (for your report / testing)

| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Serves the frontend page |
| GET | `/api/customers` | Returns all customers as JSON |
| POST | `/api/customers` | Adds a customer (`full_name`, `address`, `phone`, `email`) |
| POST | `/api/hardware/reset` | Turns all LEDs/buzzer off |
| GET | `/api/logs` | Returns the last 50 system log entries as JSON |

## 7. Notes

- `Phase1.fzz` (your Fritzing circuit file) and the old PHP/MySQL version aren't used by this app — they're just kept for reference. Everything here runs on Flask + SQLite as your group wanted.
- Duplicate email addresses are rejected (the `email_address` column is `UNIQUE`) and correctly trigger the failure LED/buzzer — try adding the same email twice to demo the failure case.
