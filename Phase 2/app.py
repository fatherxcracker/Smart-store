"""
Smart Store - Phase 2
IoT dashboard: two DHT11 sensors (via ESP32) publish temperature/humidity to
a Mosquitto MQTT broker. This Flask app subscribes to that broker, serves
the dashboard, stores per-fridge thresholds, and runs the temperature alert
flow: email -> user replies YES/NO -> fan control via motor_control.py.
The Pi checks the inbox (IMAP) for the reply; Yes/No links in the email
are kept as a backup in case replying isn't possible.
"""

import os
import re
import json
import time
import email
import email.header
import imaplib
import sqlite3
import secrets
import smtplib
import threading
from email.mime.text import MIMEText
from email.utils import parseaddr
from datetime import datetime

from flask import Flask, request, jsonify, Response, send_from_directory
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

import motor_control

load_dotenv()

# ---------------------------------------------------------------------------
# Config (from .env - see .env.example)
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "phase2.db")

MQTT_BROKER_HOST = os.environ.get("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.environ.get("MQTT_BROKER_PORT", "1883"))
MQTT_TOPICS = {"Frig1": 1, "Frig2": 2}  # topic -> fridge_id

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "")
SMTP_APP_PASSWORD = os.environ.get("SMTP_APP_PASSWORD", "")
ALERT_RECIPIENT_EMAIL = os.environ.get("ALERT_RECIPIENT_EMAIL", SMTP_EMAIL)

# Reading the user's YES/NO reply: the Pi logs into the SAME Gmail account it
# sends from (same App Password) and checks for unread replies every few seconds.
IMAP_HOST = os.environ.get("IMAP_HOST", "imap.gmail.com")
IMAP_POLL_SECONDS = int(os.environ.get("IMAP_POLL_SECONDS", "10"))

# Every alert email carries this tag in its subject, e.g. "[ref:abc123]".
# Replies keep the subject ("Re: ..."), so the tag tells us which alert
# (and which fridge) the YES/NO answer belongs to.
REF_PATTERN = re.compile(r"\[ref:([A-Za-z0-9_-]+)\]")

# The base URL the Yes/No links in the email point to. This must be an
# address your phone/email client can actually reach - usually the Pi's
# LAN IP, e.g. http://192.168.1.50:5001 (NOT localhost/127.0.0.1).
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:5001")

# Minimum time between two alert emails for the SAME fridge, so a fridge
# sitting above threshold doesn't spam an email every couple of seconds.
ALERT_COOLDOWN_SECONDS = int(os.environ.get("ALERT_COOLDOWN_SECONDS", "60"))

DEFAULT_THRESHOLDS = {1: 8.0, 2: 8.0}  # degrees C, overridden by the DB

# index.html / style.css / script.js all live directly in this folder
# (matching the dashboard as originally built). We serve ONLY those specific
# files below rather than exposing the whole folder as static - the folder
# also holds app.py, phase2.db and .env, which must never be downloadable.
app = Flask(__name__, static_folder=None)

# ---------------------------------------------------------------------------
# In-memory state (latest readings + notification feed).
# Thresholds and alert history are persisted in SQLite so they survive restarts.
# ---------------------------------------------------------------------------
state_lock = threading.Lock()
latest_readings = {
    1: {"temperature": None, "humidity": None, "updated_at": None},
    2: {"temperature": None, "humidity": None, "updated_at": None},
}

# Fan state now also remembers the selected PWM duty cycle.
fan_state = {
    "status": "OFF",
    "duty_cycle": motor_control.DEFAULT_DUTY_CYCLE
}

notifications = []  # list of {id, fridge_id, message, level, created_at} newest first


def add_notification(fridge_id, message, level="info"):
    with state_lock:
        notifications.insert(0, {
            "id": secrets.token_hex(4),
            "fridge_id": fridge_id,
            "message": message,
            "level": level,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })
        del notifications[50:]  # keep the feed bounded


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS thresholds (
            fridge_id INTEGER PRIMARY KEY,
            threshold_c REAL NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fridge_id INTEGER NOT NULL,
            temperature REAL NOT NULL,
            token TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP
        )
        """
    )
    for fridge_id, default_value in DEFAULT_THRESHOLDS.items():
        conn.execute(
            "INSERT OR IGNORE INTO thresholds (fridge_id, threshold_c) VALUES (?, ?)",
            (fridge_id, default_value),
        )
    conn.commit()
    conn.close()
    print(f"[database] Ready at {DATABASE_PATH}")


def get_threshold(fridge_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT threshold_c FROM thresholds WHERE fridge_id = ?", (fridge_id,)
    ).fetchone()
    conn.close()
    return row["threshold_c"] if row else DEFAULT_THRESHOLDS.get(fridge_id, 8.0)


def set_threshold(fridge_id, value):
    conn = get_connection()
    conn.execute(
        "INSERT INTO thresholds (fridge_id, threshold_c) VALUES (?, ?) "
        "ON CONFLICT(fridge_id) DO UPDATE SET threshold_c = excluded.threshold_c",
        (fridge_id, value),
    )
    conn.commit()
    conn.close()


def has_recent_pending_alert(fridge_id):
    """True if this fridge has an alert within the cooldown window (60s)."""
    conn = get_connection()
    row = conn.execute(
        """
        SELECT created_at FROM alerts
        WHERE fridge_id = ?
        ORDER BY created_at DESC LIMIT 1
        """,
        (fridge_id,),
    ).fetchone()
    conn.close()
    if not row:
        return False
    created = datetime.fromisoformat(row["created_at"])

    now = datetime.utcnow()
    return (now - created).total_seconds() < ALERT_COOLDOWN_SECONDS


def create_alert(fridge_id, temperature):
    token = secrets.token_urlsafe(16)
    conn = get_connection()
    conn.execute(
        "INSERT INTO alerts (fridge_id, temperature, token, status) VALUES (?, ?, ?, 'pending')",
        (fridge_id, temperature, token),
    )
    conn.commit()
    conn.close()
    return token


def resolve_alert(token, status):
    """Returns (row, just_resolved). just_resolved is False if this token was
    already handled by an earlier click, so the caller doesn't repeat the
    fan action / notification for the same click twice."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM alerts WHERE token = ?", (token,)).fetchone()
    if not row:
        conn.close()
        return None, False
    if row["status"] != "pending":
        conn.close()
        return row, False  # already handled (link clicked twice)
    conn.execute(
        "UPDATE alerts SET status = ?, resolved_at = CURRENT_TIMESTAMP WHERE token = ?",
        (status, token),
    )
    conn.commit()
    conn.close()
    return row, True


# ---------------------------------------------------------------------------
# Email alert
# ---------------------------------------------------------------------------
def send_alert_email(fridge_id, temperature, token):
    if not SMTP_EMAIL or not SMTP_APP_PASSWORD or not ALERT_RECIPIENT_EMAIL:
        print("[email] SMTP_EMAIL / SMTP_APP_PASSWORD / ALERT_RECIPIENT_EMAIL not set in .env - skipping send.")
        return False

    yes_link = f"{PUBLIC_BASE_URL}/api/alert/confirm?token={token}&action=yes"
    no_link = f"{PUBLIC_BASE_URL}/api/alert/confirm?token={token}&action=no"

    body = (
        f"The current temperature is {temperature:.1f}C in Refrigerator {fridge_id} "
        f"(above the configured threshold). Would you like to turn on the fan?\n\n"
        f"Reply to this email with YES to turn on the fan, or NO to leave it off.\n\n"
        f"(Backup if you can't reply: YES {yes_link}  |  NO {no_link})\n"
    )

    msg = MIMEText(body)
    msg["Subject"] = (
        f"Smart Store Alert: Refrigerator {fridge_id} temperature is "
        f"{temperature:.1f}C [ref:{token}]"
    )
    msg["From"] = SMTP_EMAIL
    msg["To"] = ALERT_RECIPIENT_EMAIL

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
            server.send_message(msg)
        print(f"[email] Alert sent for fridge {fridge_id} ({temperature:.1f}C)")
        return True
    except Exception as error:
        print(f"[email] Failed to send alert: {error}")
        return False


# ---------------------------------------------------------------------------
# MQTT
# ---------------------------------------------------------------------------
def on_mqtt_connect(client, userdata, flags, reason_code, properties=None):
    print(f"[mqtt] Connected to {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT} (reason={reason_code})")
    for topic in MQTT_TOPICS:
        client.subscribe(topic)
        print(f"[mqtt] Subscribed to '{topic}'")


def on_mqtt_message(client, userdata, msg):
    fridge_id = MQTT_TOPICS.get(msg.topic)
    if fridge_id is None:
        return
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        temperature = float(payload["temperature"])
        humidity = float(payload["humidity"])
    except (ValueError, KeyError, UnicodeDecodeError) as error:
        print(f"[mqtt] Bad payload on {msg.topic}: {msg.payload!r} ({error})")
        return

    with state_lock:
        latest_readings[fridge_id] = {
            "temperature": temperature,
            "humidity": humidity,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

    threshold = get_threshold(fridge_id)
    if temperature > threshold and not has_recent_pending_alert(fridge_id):
        token = create_alert(fridge_id, temperature)
        sent = send_alert_email(fridge_id, temperature, token)
        if sent:
            add_notification(
                fridge_id,
                f"Temperature alert: Refrigerator {fridge_id} is {temperature:.1f}C "
                f"(threshold {threshold:.1f}C). Email sent - waiting for a response.",
                level="warning",
            )
        else:
            add_notification(
                fridge_id,
                f"Temperature alert: Refrigerator {fridge_id} is {temperature:.1f}C, "
                f"but the alert email could not be sent (check .env SMTP settings).",
                level="warning",
            )


def start_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="smart-store-dashboard")
    client.on_connect = on_mqtt_connect
    client.on_message = on_mqtt_message
    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
        client.loop_start()
        return client
    except Exception as error:
        print(f"[mqtt] Could not connect to broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT} ({error})")
        print("[mqtt] The dashboard will still run, but readings won't update until the broker is reachable.")
        return None


# ---------------------------------------------------------------------------
# Routes - dashboard
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/style.css")
def style_css():
    return send_from_directory(BASE_DIR, "style.css")


@app.route("/script.js")
def script_js():
    return send_from_directory(BASE_DIR, "script.js")


@app.route("/api/readings")
def get_readings():
    with state_lock:
        out = {}
        for fridge_id, reading in latest_readings.items():
            threshold = get_threshold(fridge_id)
            status = "warning" if (reading["temperature"] is not None and reading["temperature"] > threshold) else "normal"
            out[fridge_id] = {**reading, "threshold": threshold, "status": status}
        return jsonify(out)


@app.route("/api/thresholds", methods=["GET"])
def get_thresholds():
    return jsonify({fid: get_threshold(fid) for fid in (1, 2)})


@app.route("/api/thresholds/<int:fridge_id>", methods=["POST"])
def post_threshold(fridge_id):
    if fridge_id not in (1, 2):
        return jsonify({"success": False, "message": "Unknown fridge id."}), 404
    data = request.get_json(silent=True) or {}
    try:
        value = float(data.get("threshold"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "threshold must be a number."}), 400
    set_threshold(fridge_id, value)
    add_notification(fridge_id, f"Refrigerator {fridge_id} threshold set to {value:.1f}C.", level="info")
    return jsonify({"success": True, "fridge_id": fridge_id, "threshold": value})


@app.route("/api/notifications")
def get_notifications():
    with state_lock:
        return jsonify(notifications[:20])


# ---------------------------------------------------------------------------
# Routes - fan control
# ---------------------------------------------------------------------------
@app.route("/api/fan/status")
def fan_status():
    return jsonify(fan_state)


@app.route("/api/fan/speed", methods=["POST"])
def fan_speed():
    data = request.get_json(silent=True) or {}

    try:
        duty_cycle = int(data.get("duty_cycle"))
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "duty_cycle must be an integer from 0 to 100."
        }), 400

    if not 0 <= duty_cycle <= 100:
        return jsonify({
            "success": False,
            "message": "duty_cycle must be between 0 and 100."
        }), 400

    fan_state["duty_cycle"] = duty_cycle

    if fan_state["status"] == "ON":
        motor_control.set_fan_speed(duty_cycle)

        if duty_cycle == 0:
            fan_state["status"] = "OFF"

        add_notification(
            None,
            f"Fan duty cycle set to {duty_cycle}%.",
            level="info"
        )

    return jsonify({"success": True, **fan_state})


@app.route("/api/fan/toggle", methods=["POST"])
def fan_toggle():
    if fan_state["status"] == "OFF":
        duty_cycle = fan_state["duty_cycle"]

        # If the saved value is zero, use the default when turning ON.
        if duty_cycle == 0:
            duty_cycle = motor_control.DEFAULT_DUTY_CYCLE
            fan_state["duty_cycle"] = duty_cycle

        motor_control.fan_on(duty_cycle)
        fan_state["status"] = "ON"

        add_notification(
            None,
            f"Fan turned ON manually at {duty_cycle}% duty cycle.",
            level="info"
        )
    else:
        motor_control.fan_off()
        fan_state["status"] = "OFF"

        add_notification(
            None,
            "Fan turned OFF manually from the dashboard.",
            level="info"
        )

    return jsonify(fan_state)


def handle_alert_response(token, action, source):
    """Apply a YES/NO answer to an alert. Used by both the email-reply reader
    and the backup links. Returns the alert row (or None if unknown)."""
    action = "yes" if action == "yes" else "no"
    row, just_resolved = resolve_alert(token, "confirmed" if action == "yes" else "declined")
    if row is None or not just_resolved:
        return row  # unknown token, or this alert was already answered

    fridge_id = row["fridge_id"]
    temperature = row["temperature"]

    if action == "yes":
        duty_cycle = fan_state["duty_cycle"]
        if duty_cycle == 0:
            duty_cycle = motor_control.DEFAULT_DUTY_CYCLE
            fan_state["duty_cycle"] = duty_cycle

        motor_control.fan_on(duty_cycle)
        fan_state["status"] = "ON"

        add_notification(
            fridge_id,
            f"User replied YES ({source}) - fan turned ON at {duty_cycle}% "
            f"(Refrigerator {fridge_id} was {temperature:.1f}C).",
            level="success",
        )
    else:
        add_notification(
            fridge_id,
            f"User replied NO ({source}) - no action taken for "
            f"Refrigerator {fridge_id} ({temperature:.1f}C).",
            level="info",
        )
    return row


@app.route("/api/alert/confirm")
def alert_confirm():
    token = request.args.get("token", "")
    action = "yes" if request.args.get("action", "") == "yes" else "no"

    row = handle_alert_response(token, action, source="email link")
    if row is None:
        return Response(
            "<h1>This alert link isn't valid or has expired.</h1>",
            mimetype="text/html"
        ), 404

    fridge_id = row["fridge_id"]
    if action == "yes":
        html = (
            f"<h1>Fan turned on</h1>"
            f"<p>The fan is now running for Refrigerator {fridge_id}. You can close this tab.</p>"
        )
    else:
        html = (
            f"<h1>No action taken</h1>"
            f"<p>The fan was left off for Refrigerator {fridge_id}. You can close this tab.</p>"
        )
    return Response(html, mimetype="text/html")


# ---------------------------------------------------------------------------
# Email replies (IMAP) - "If the user replies YES, activate the fan"
# ---------------------------------------------------------------------------
def get_plain_text(message):
    """Return the text/plain body of an email (handles multipart replies)."""
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                payload = part.get_payload(decode=True) or b""
                return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        # No plain-text part (HTML-only reply): strip tags from the HTML part.
        for part in message.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True) or b""
                html = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                return re.sub(r"<[^>]+>", "\n", html)
        return ""
    payload = message.get_payload(decode=True) or b""
    return payload.decode(message.get_content_charset() or "utf-8", errors="replace")


def parse_reply_answer(body):
    """Look only at what the user typed (above the quoted original email) and
    return "yes", "no", or None if the reply is unclear."""
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        # Stop at the quoted original message.
        if line.startswith(">") or re.match(r"^On .+wrote:?$", line) or line.startswith("-----"):
            break
        first_word = re.sub(r"[^A-Za-z]", "", line.split()[0]).upper()
        if first_word in ("YES", "Y", "OUI"):
            return "yes"
        if first_word in ("NO", "N", "NON"):
            return "no"
        return None  # first thing they wrote wasn't YES/NO
    return None


def check_email_replies():
    """One pass: read unread alert replies from the inbox and act on them."""
    mail = imaplib.IMAP4_SSL(IMAP_HOST)
    try:
        mail.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        mail.select("INBOX")
        status, data = mail.search(None, '(UNSEEN SUBJECT "ref:")')
        if status != "OK":
            return
        for num in data[0].split():
            status, msg_data = mail.fetch(num, "(RFC822)")  # also marks it as read
            if status != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                continue
            message = email.message_from_bytes(msg_data[0][1])

            subject = str(email.header.make_header(email.header.decode_header(message.get("Subject", ""))))
            match = REF_PATTERN.search(subject)
            if not match:
                continue

            # Only accept answers from the person the alert was sent to.
            sender = parseaddr(message.get("From", ""))[1].lower()
            if sender != ALERT_RECIPIENT_EMAIL.lower():
                continue

            answer = parse_reply_answer(get_plain_text(message))
            if answer is None:
                # e.g. our own alert email (when sending to yourself) or an unclear reply
                continue

            token = match.group(1)
            print(f"[imap] Reply '{answer.upper()}' received for alert {token[:6]}...")
            handle_alert_response(token, answer, source="email reply")
    finally:
        try:
            mail.logout()
        except Exception:
            pass


def email_reply_loop():
    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        print("[imap] SMTP_EMAIL / SMTP_APP_PASSWORD not set - not checking for replies.")
        return
    print(f"[imap] Checking {SMTP_EMAIL} for YES/NO replies every {IMAP_POLL_SECONDS}s")
    while True:
        try:
            check_email_replies()
        except Exception as error:
            print(f"[imap] Could not check replies: {error}")
        time.sleep(IMAP_POLL_SECONDS)


if __name__ == "__main__":
    init_db()
    mqtt_client = start_mqtt()
    threading.Thread(target=email_reply_loop, daemon=True).start()

    try:
        app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)
    finally:
        if mqtt_client is not None:
            mqtt_client.loop_stop()

        motor_control.cleanup()