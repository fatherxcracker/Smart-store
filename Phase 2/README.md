# Smart Store — Phase 2

IoT fridge-monitoring dashboard.

- **Sensors:** 2x DHT11 (temperature + humidity), each wired to its own ESP32
- **Data transport:** MQTT (Mosquitto broker running on the Raspberry Pi), topics `Frig1` and `Frig2`
- **Backend:** Python (Flask) — subscribes to MQTT, stores thresholds, sends alert emails, controls the fan
- **Frontend:** HTML / CSS / JavaScript dashboard — 4 gauges (temp + humidity x 2 fridges), fan status, notifications feed
- **Alert flow:** over-threshold temperature → email "The current temperature is … Would you like to turn on the fan?" → user **replies YES** → the Pi reads the reply (IMAP) and drives the DC motor (simulated fan) through its GPIO. Replying NO (or anything else) takes no action.
- **Database:** SQLite (`phase2.db`, created automatically) — stores per-fridge thresholds and alert history

## 1. Project structure

```
Phase 2/
├── app.py                  # Flask backend: MQTT subscriber, alert email, fan control, dashboard API
├── motor_control.py        # DC motor (fan) GPIO control, with a mock mode for laptop testing
├── requirements.txt
├── .env.example             # copy to .env and fill in real values (never commit .env)
├── phase2.db                 # created automatically on first run
├── index.html              # the dashboard page Flask serves
├── style.css
├── script.js               # polls the backend: gauges, fan status, notifications
└── esp32/
    ├── Frig1/Frig1.ino        # ESP32 sketch for refrigerator 1
    └── Frig2/Frig2.ino        # ESP32 sketch for refrigerator 2
```

## 2. How it works

1. Each ESP32 reads its DHT11 sensor every 2 seconds and publishes `{"temperature": ..., "humidity": ...}` as JSON to its MQTT topic (`Frig1` or `Frig2`) on the Pi's Mosquitto broker.
2. `app.py` subscribes to both topics. Every time a reading comes in, it updates the dashboard's live gauges and checks it against that fridge's threshold.
3. If a reading is **above the threshold**, the backend emails you (see `.env`): *"The current temperature is X°C … Would you like to turn on the fan?"* and a notification appears on the dashboard. It won't send another email for the same fridge for `ALERT_COOLDOWN_SECONDS` (default 5 minutes), so a fridge sitting above threshold doesn't spam your inbox.
4. **Reply to the email with `YES`.** Every `IMAP_POLL_SECONDS` (default 10 s) the Pi logs into the same Gmail account over IMAP and reads unread replies. The subject of each alert carries a tag like `[ref:abc123…]`; replies keep the subject, so the Pi knows which alert/fridge the answer is for. Only the text **above** the quoted original is read, and only replies from `ALERT_RECIPIENT_EMAIL` are accepted.
   - `YES` (or `Y`, `Yes please`, …) → `motor_control.fan_on()` runs the motor, fan status goes to ON, and a notification is logged.
   - `NO` or anything else → no action (a NO is logged as a notification).
   - The email also contains backup YES/NO links in case replying isn't possible; they do the same thing.
5. The dashboard polls the fan status, readings and notifications every few seconds, so when a YES reply turns the motor on, the fan icon starts spinning and the status changes to ON without refreshing the page. There's also a manual power button and a PWM speed slider.

This mirrors the "Data capture → Data communication → Data presentation" flow from the spec: the ESP32 + DHT11 **capture** data, MQTT **communicates** it to the Pi, and the dashboard gauges + email + notifications **present** it and drive the alert/fan response.

## 3. Setting up the Mosquitto MQTT broker (on the Raspberry Pi)

```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
```

By default Mosquitto only listens on `localhost`, which blocks the ESP32s (on WiFi) from reaching it. Create a config to open it up to your network:

```bash
sudo nano /etc/mosquitto/conf.d/default.conf
```

Paste in:
```
listener 1883 0.0.0.0
allow_anonymous true
```

(`allow_anonymous true` is fine for a class demo on your own network; don't do this on a public network.)

Then restart and enable it:
```bash
sudo systemctl restart mosquitto
sudo systemctl enable mosquitto
```

Find the Pi's IP address (you'll need it for both the ESP32 sketches and the `.env` file below):
```bash
hostname -I
```

You can sanity-check the broker is reachable from the Pi itself with:
```bash
mosquitto_sub -h localhost -t Frig1
# in another terminal:
mosquitto_pub -h localhost -t Frig1 -m '{"temperature": 5.0, "humidity": 50.0}'
```

## 4. Flashing the two ESP32 boards

1. In the Arduino IDE, install these libraries (Tools → Manage Libraries): **PubSubClient** (Nick O'Leary) and **DHT sensor library** (Adafruit) + its dependency **Adafruit Unified Sensor**. Also install ESP32 board support if you haven't (Boards Manager → "esp32").
2. Open `esp32/Frig1/Frig1.ino`. Edit these three lines near the top:
   ```cpp
   const char* ssid = "your wifi name";
   const char* password = "your wifi password";
   const char* mqtt_server = "192.168.x.x";   // the Pi's IP from `hostname -I`
   ```
3. Select the correct board/port, upload to the ESP32 you're wiring to Refrigerator 1's DHT11.
4. Repeat steps 2–3 for `esp32/Frig2/Frig2.ino` on the second ESP32. **Do not** change the `mqtt_topic`/`client_id` lines in either file — that's what keeps the two fridges distinct on the dashboard.
5. Open the Arduino Serial Monitor (115200 baud) on each board after flashing — you should see `WiFi connected!` and then a `Published to Frig1: {...}` / `Published to Frig2: {...}` line every 2 seconds. If you instead see `Failed to read DHT11!`, double check the sensor wiring (see your breadboard setup below).

## 5. Running the dashboard (on the Raspberry Pi)

```bash
cd "Phase 2"
python3 -m venv venv --system-site-packages
source venv/bin/activate
pip install -r requirements.txt
```

Copy the environment template and fill in real values:
```bash
cp .env.example .env
nano .env
```

You need:
- `MQTT_BROKER_HOST=localhost` (Mosquitto is running on this same Pi)
- A **Gmail App Password** for `SMTP_EMAIL` / `SMTP_APP_PASSWORD` — go to your Google Account → Security → turn on 2-Step Verification → App Passwords → create one for "Mail". Use the 16-character password it gives you, not your normal Gmail password.
- `ALERT_RECIPIENT_EMAIL` — whoever should receive the "fridge is too warm" email. Their **reply** is what turns the fan on, so it must come from this exact address. (It can be the same as `SMTP_EMAIL` if you're emailing yourself.)
- IMAP is used to read replies with the same App Password — nothing extra to set up on Gmail (`IMAP_HOST=imap.gmail.com` is the default).
- `PUBLIC_BASE_URL` — must be an address your phone/email client can actually open, e.g. `http://192.168.1.50:5001` (the Pi's LAN IP from `hostname -I`). **Not** `localhost` — the Yes/No links are opened from your email, not from the Pi itself.

Then run it:
```bash
python app.py
```

You should see `[hardware] PWM motor control initialized.` (not "Using mock motor driver"), `[mqtt] Connected to ...` and `[imap] Checking ... for YES/NO replies`. Open `http://<pi-ip>:5001` from any device on the same WiFi to see the dashboard.

### Testing without the Pi/hardware

Same as Phase 1 — if `gpiozero` can't find real GPIO pins (e.g. running on a laptop), `motor_control.py` automatically falls back to a mock motor driver (it prints `Fan duty cycle: 40%` / `Fan ON` instead of crashing). That means you can build/test the dashboard, MQTT flow, and threshold logic on a laptop with a local Mosquitto broker before ever touching the Pi.

## 6. Wiring

### Breadboard 1 — the two ESP32s + DHT11 sensors

This breadboard is **not** electrically connected to the Raspberry Pi at all — the ESP32s only need to reach the Pi over WiFi (MQTT), not a wire. Power each ESP32 from its own USB cable (a wall adapter, laptop USB port, or a USB power bank/hub) — "plugged in for power" is exactly right, there's no other connection needed to the Pi.

Per ESP32 + DHT11:
| DHT11 pin | ESP32 pin |
|---|---|
| VCC | 3V3 |
| DATA | GPIO4 |
| GND | GND |

Add a 10kΩ pull-up resistor between DATA and VCC if your DHT11 breakout board doesn't already have one built in (most 3-pin DHT11 modules do).

### Breadboard 2 — the Pi + motor driver + DC motor

This breadboard **is** wired to the Pi's GPIO, and the DC motor/driver draw their own power from a separate battery pack — that's the correct setup. A motor can pull more current than the Pi's GPIO/5V pins can safely supply, so the driver board's motor-power input should come from the battery pack, not the Pi.

| `motor_control.py` pin (BCM) | Motor driver pin | Notes |
|---|---|---|
| GPIO22 | EN1 (enable) | speed/on-off |
| GPIO27 | IN1 | direction |
| GPIO17 | IN2 | direction (opposite of IN1) |

**One thing to double check:** the motor driver's logic GND, the battery pack's GND, and the Pi's GND must all be tied together (a shared ground), even though the battery powers the motor separately from the Pi. Without a shared ground, the Pi's GPIO signals have no reference voltage and the driver won't respond reliably. If your driver board is something like an L298N, this is its GND pin next to the motor power terminals.

These GPIO pin numbers happen to match the ones Phase 1 used for its LEDs/buzzer — that's only a conflict if you tried to run both phases' code on the same Pi at the same time, which you said isn't happening for this demo, so there's nothing to change.

## 7. Database

`phase2.db` is created automatically on first run. Two tables:

- **thresholds** — `fridge_id, threshold_c` (defaults to 8.0°C for both fridges until you change them from the dashboard)
- **alerts** — `id, fridge_id, temperature, token, status (pending/confirmed/declined), created_at, resolved_at` — one row per alert email sent, so you have a record for your report/demo

```bash
sqlite3 phase2.db "SELECT * FROM thresholds;"
sqlite3 phase2.db "SELECT * FROM alerts ORDER BY id DESC LIMIT 10;"
```

## 8. API reference

| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Serves the dashboard page |
| GET | `/api/readings` | Latest temperature/humidity + status per fridge |
| GET | `/api/thresholds` | Current threshold per fridge |
| POST | `/api/thresholds/<fridge_id>` | Set a fridge's threshold (`{"threshold": 8.0}`) |
| GET | `/api/notifications` | Recent notification feed (newest first) |
| GET | `/api/fan/status` | Current fan ON/OFF status + duty cycle |
| POST | `/api/fan/toggle` | Manually toggle the fan from the dashboard |
| POST | `/api/fan/speed` | Set PWM duty cycle (`{"duty_cycle": 0-100}`) |
| GET | `/api/alert/confirm?token=...&action=yes\|no` | Backup YES/NO link target from the alert email |

## 9. Demo checklist

1. Start Mosquitto, then `python app.py` on the Pi; open `http://<pi-ip>:5001`.
2. Both ESP32s publishing → all four gauges show values.
3. Lower a fridge's threshold below the current temperature and press **Save** → alert email arrives and a notification appears.
4. Reply **YES** → within ~10 s the motor spins and the dashboard shows the fan ON.
5. Trigger the other fridge and reply **NO** → nothing happens except a "no action taken" notification.

## 10. Notes

- The speed slider sets the real PWM duty cycle on the L293D enable pin (GPIO22), so it changes the motor's actual speed.
- `.env` is gitignored — never commit real Gmail credentials. Only `.env.example` (with placeholder values) is committed.
- Flask runs with `debug=False` so the Werkzeug debug console isn't exposed on the network.
