"""Phase 2 (fridge monitoring) inside the Phase 4 application.

Two DHT11 sensors on ESP32 boards publish temperature/humidity to Mosquitto
(topics Frig1 / Frig2). This module subscribes to the broker, keeps the latest
readings, stores a history in the shared SQLite database, and runs the alert
flow: temperature above the limit -> email -> the user replies YES -> the fan
(L293D + PWM) turns on. NO leaves the fan off.

Everything lives in the same database and the same login session as the store.
"""

import json
import os
import re
import secrets
import smtplib
import threading
import time
import email
import email.header
import imaplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.utils import parseaddr

from flask import Blueprint, abort, current_app, jsonify, render_template, request, session

import db
from . import motor_control

REF_PATTERN = re.compile(r"\[ref:([A-Za-z0-9_-]+)\]")
FRIDGES = (1, 2)
MQTT_TOPICS = {"Frig1": 1, "Frig2": 2}  # topic -> fridge id
DEFAULT_THRESHOLD = 8.0

monitoring_bp = Blueprint("monitoring", __name__, url_prefix="/monitoring")


def _env(name, default=""):
    return os.environ.get(name, default)


class Monitor:
    """State and background work for one application."""

    def __init__(self, app):
        self.app = app
        self.lock = threading.Lock()
        self.latest = {f: {"temperature": None, "humidity": None, "updated_at": None} for f in FRIDGES}
        self.fan = {"status": "OFF", "duty_cycle": motor_control.DEFAULT_DUTY_CYCLE}
        self.feed = []          # newest first, shown on the dashboard
        self.last_saved = {}    # fridge -> monotonic time of the last stored reading
        self.mqtt_client = None
        self.mqtt_connected = False
        self.threads = []
        self.stop = threading.Event()
        self.active_admin = None  # (email, monotonic time) of the admin who last used the store

    # ---------------------------------------------------------------- settings
    @property
    def cooldown(self):
        return int(self.app.config.get("ALERT_COOLDOWN_SECONDS", _env("ALERT_COOLDOWN_SECONDS", "300")))

    @property
    def history_seconds(self):
        return int(self.app.config.get("FRIDGE_HISTORY_SECONDS", _env("FRIDGE_HISTORY_SECONDS", "30")))

    @property
    def stale_seconds(self):
        return max(1, int(self.app.config.get("FRIDGE_STALE_SECONDS", _env("FRIDGE_STALE_SECONDS", "30"))))

    @property
    def alert_ttl_seconds(self):
        return max(1, int(self.app.config.get("ALERT_TOKEN_TTL_SECONDS", _env("ALERT_TOKEN_TTL_SECONDS", "900"))))

    def note_admin_activity(self, email):
        """Called on every request from a logged-in admin."""
        if email:
            self.active_admin = (email.strip().lower(), time.monotonic())

    def alert_recipient(self):
        """The admin who is logged in and used the store in the last
        ALERT_ACTIVE_ADMIN_MINUTES (default 30); otherwise ALERT_RECIPIENT_EMAIL from .env."""
        minutes = float(_env("ALERT_ACTIVE_ADMIN_MINUTES", "30"))
        if self.active_admin and time.monotonic() - self.active_admin[1] <= minutes * 60:
            return self.active_admin[0]
        return _env("ALERT_RECIPIENT_EMAIL") or _env("SMTP_EMAIL")

    def smtp(self):
        return {
            "host": _env("SMTP_HOST", "smtp.gmail.com"), "port": int(_env("SMTP_PORT", "587")),
            "user": _env("SMTP_EMAIL"), "password": _env("SMTP_APP_PASSWORD"),
            "to": _env("ALERT_RECIPIENT_EMAIL") or _env("SMTP_EMAIL"),
            "imap": _env("IMAP_HOST", "imap.gmail.com"),
            "base": _env("PUBLIC_BASE_URL", "http://localhost:5003").rstrip("/"),
        }

    # ------------------------------------------------------------- notifications
    def add_notification(self, fridge_id, message, level="info", message_fr=None):
        """Show on the dashboard feed and keep it in the store's notification log."""
        with self.lock:
            self.feed.insert(0, {"id": secrets.token_hex(4), "fridge_id": fridge_id, "message": message,
                                 "level": level, "created_at": datetime.now().isoformat(timespec="seconds")})
            del self.feed[50:]
        try:
            with self.app.app_context():
                db.save_notification(level if level in ("info", "success", "warning", "error") else "info",
                                     message, message_fr or message)
        except Exception as error:  # never let logging break sensor handling
            print(f"[monitoring] Could not save notification: {error}")

    # ------------------------------------------------------------------ database
    def get_threshold(self, fridge_id):
        conn = db.get_connection()
        try:
            row = conn.execute("SELECT threshold_c FROM fridge_thresholds WHERE fridge_id = ?", (fridge_id,)).fetchone()
        finally:
            conn.close()
        return row["threshold_c"] if row else DEFAULT_THRESHOLD

    def set_threshold(self, fridge_id, value):
        conn = db.get_connection()
        try:
            conn.execute("""INSERT INTO fridge_thresholds (fridge_id, threshold_c) VALUES (?, ?)
                            ON CONFLICT(fridge_id) DO UPDATE SET threshold_c = excluded.threshold_c""", (fridge_id, value))
            conn.commit()
        finally:
            conn.close()

    def recent_alert(self, fridge_id):
        """Cooldown: don't email again for the same fridge too soon."""
        conn = db.get_connection()
        try:
            row = conn.execute("SELECT created_at FROM fridge_alerts WHERE fridge_id = ? ORDER BY id DESC LIMIT 1",
                               (fridge_id,)).fetchone()
        finally:
            conn.close()
        if not row:
            return False
        created = datetime.fromisoformat(row["created_at"]).replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - created).total_seconds() < self.cooldown

    def create_alert(self, fridge_id, temperature, recipient=None):
        token = secrets.token_urlsafe(16)
        conn = db.get_connection()
        try:
            conn.execute("INSERT INTO fridge_alerts (fridge_id, temperature, token, recipient) VALUES (?, ?, ?, ?)",
                         (fridge_id, temperature, token, recipient))
            conn.commit()
        finally:
            conn.close()
        return token

    def is_pending(self, token):
        """True while the alert can still be answered (not answered, not expired)."""
        alert = self.get_alert(token)
        return bool(alert) and alert["status"] == "pending"

    def recipient_of(self, token):
        """Email address an alert was sent to (older alerts: the .env address)."""
        conn = db.get_connection()
        try:
            row = conn.execute("SELECT recipient FROM fridge_alerts WHERE token = ?", (token,)).fetchone()
        finally:
            conn.close()
        recipient = row["recipient"] if row and row["recipient"] else self.smtp()["to"]
        return (recipient or "").lower()

    def _alert_row(self, conn, token):
        # SQLite timestamps are UTC. Keep expiry compatible with existing databases.
        row = conn.execute("""SELECT *, datetime(created_at, ?) AS expires_at,
                              (julianday(created_at) IS NULL
                               OR julianday(created_at) > julianday('now')
                               OR julianday(created_at) <= julianday('now', ?)) AS token_expired
                              FROM fridge_alerts WHERE token = ?""",
                           (f"+{self.alert_ttl_seconds} seconds", f"-{self.alert_ttl_seconds} seconds", token)).fetchone()
        if row is None:
            return None
        alert = dict(row)
        expired = alert.pop("token_expired")
        if alert["status"] == "pending" and expired:
            alert["status"] = "expired"
        return alert

    def get_alert(self, token):
        conn = db.get_connection()
        try:
            return self._alert_row(conn, token)
        finally:
            conn.close()

    def resolve_alert(self, token, status):
        """(row, just_resolved). Expired or already answered alerts cannot act."""
        if status not in ("confirmed", "declined"):
            raise ValueError("Unknown alert response.")
        conn = db.get_connection()
        try:
            # Serialize competing email replies/form submissions before checking expiry.
            conn.execute("BEGIN IMMEDIATE")
            row = self._alert_row(conn, token)
            if row is None or row["status"] != "pending":
                return row, False
            changed = conn.execute(
                "UPDATE fridge_alerts SET status = ?, resolved_at = CURRENT_TIMESTAMP WHERE token = ? AND status = 'pending'",
                (status, token)).rowcount
            row = self._alert_row(conn, token)
            conn.commit()
            return row, bool(changed)
        finally:
            conn.close()

    def store_reading(self, fridge_id, temperature, humidity):
        now = time.monotonic()
        if now - self.last_saved.get(fridge_id, -1e9) < self.history_seconds:
            return
        self.last_saved[fridge_id] = now
        conn = db.get_connection()
        try:
            conn.execute("INSERT INTO fridge_readings (fridge_id, temperature, humidity) VALUES (?, ?, ?)",
                         (fridge_id, temperature, humidity))
            conn.execute("DELETE FROM fridge_readings WHERE recorded_at < datetime('now', '-7 days')")
            conn.commit()
        finally:
            conn.close()

    # --------------------------------------------------------------------- email
    def send_alert_email(self, fridge_id, temperature, token, recipient=None):
        cfg = self.smtp()
        if recipient:
            cfg["to"] = recipient
        if not cfg["user"] or not cfg["password"] or not cfg["to"]:
            print("[email] SMTP_EMAIL / SMTP_APP_PASSWORD / ALERT_RECIPIENT_EMAIL not set in .env - skipping send.")
            return False
        yes = f"{cfg['base']}/monitoring/alert/confirm?token={token}&action=yes"
        no = f"{cfg['base']}/monitoring/alert/confirm?token={token}&action=no"
        body = (f"The current temperature is {temperature:.1f}C in Refrigerator {fridge_id} "
                f"(above the configured threshold). Would you like to turn on the fan?\n\n"
                f"Reply to this email with YES (in ALL CAPS) to turn on the fan, or NO (in ALL CAPS) to leave it off.\n"
                f"Write only YES or NO on the first line of your reply.\n\n"
                f"Approval expires {self.alert_ttl_seconds / 60:g} minutes after this alert was created.\n"
                f"Backup links open a confirmation page; opening a link does not operate the fan.\n"
                f"YES {yes}\nNO {no}\n")
        msg = MIMEText(body)
        msg["Subject"] = f"Smart Store Alert: Refrigerator {fridge_id} temperature is {temperature:.1f}C [ref:{token}]"
        msg["From"] = cfg["user"]
        msg["To"] = cfg["to"]
        try:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as server:
                server.starttls()
                server.login(cfg["user"], cfg["password"])
                server.send_message(msg)
            print(f"[email] Alert sent to {cfg['to']} for fridge {fridge_id} ({temperature:.1f}C)")
            return True
        except Exception as error:
            print(f"[email] Failed to send alert: {error}")
            return False

    # ------------------------------------------------------------------ readings
    def handle_reading(self, fridge_id, temperature, humidity):
        """One DHT11 reading: remember it, store it, and alert if it is too warm."""
        with self.lock:
            self.latest[fridge_id] = {"temperature": temperature, "humidity": humidity,
                                      "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        with self.app.app_context():
            self.store_reading(fridge_id, temperature, humidity)
            threshold = self.get_threshold(fridge_id)
            if temperature > threshold and not self.recent_alert(fridge_id):
                recipient = self.alert_recipient()
                token = self.create_alert(fridge_id, temperature, recipient)
                sent = self.send_alert_email(fridge_id, temperature, token, recipient)
                tail = "Email sent - waiting for a response." if sent else "The alert email could not be sent (check .env SMTP settings)."
                self.add_notification(
                    fridge_id,
                    f"Temperature alert: Refrigerator {fridge_id} is {temperature:.1f}C (threshold {threshold:.1f}C). {tail}",
                    "warning",
                    f"Alerte de température : le réfrigérateur {fridge_id} est à {temperature:.1f}C (seuil {threshold:.1f}C).")

    # ----------------------------------------------------------------------- fan
    def start_fan(self):
        duty = self.fan["duty_cycle"] or motor_control.DEFAULT_DUTY_CYCLE
        self.fan["duty_cycle"] = duty
        motor_control.fan_on(duty)
        self.fan["status"] = "ON"
        return duty

    def handle_alert_response(self, token, action, source):
        """YES (email reply or backup link) -> fan on. NO -> nothing happens."""
        if action not in ("yes", "no"):
            raise ValueError("Choose YES or NO.")
        with self.app.app_context():
            row, just_resolved = self.resolve_alert(token, "confirmed" if action == "yes" else "declined")
            if row is not None:
                row["just_resolved"] = just_resolved
            if row is None or not just_resolved:
                return row
            fridge_id, temperature = row["fridge_id"], row["temperature"]
            if action == "yes":
                duty = self.start_fan()
                self.add_notification(
                    fridge_id, f"User replied YES ({source}) - fan turned ON at {duty}% (Refrigerator {fridge_id} was {temperature:.1f}C).",
                    "success", f"Réponse OUI ({source}) - ventilateur allumé à {duty} % (réfrigérateur {fridge_id} : {temperature:.1f}C).")
            else:
                self.add_notification(
                    fridge_id, f"User replied NO ({source}) - no action taken for Refrigerator {fridge_id} ({temperature:.1f}C).",
                    "info", f"Réponse NON ({source}) - aucune action pour le réfrigérateur {fridge_id}.")
        return row

    # ------------------------------------------------------------------ mailbox
    @staticmethod
    def plain_text(message):
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == "text/plain" and not part.get_filename():
                    return (part.get_payload(decode=True) or b"").decode(part.get_content_charset() or "utf-8", errors="replace")
            for part in message.walk():
                if part.get_content_type() == "text/html":
                    html = (part.get_payload(decode=True) or b"").decode(part.get_content_charset() or "utf-8", errors="replace")
                    return re.sub(r"<[^>]+>", "\n", html)
            return ""
        return (message.get_payload(decode=True) or b"").decode(message.get_content_charset() or "utf-8", errors="replace")

    @staticmethod
    def parse_reply_answer(body):
        """Only what the user typed above the quoted email: 'yes', 'no' or None."""
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith(">") or re.match(r"^On .+wrote:?$", line) or line.startswith("-----"):
                break
            words = re.sub(r"[^A-Za-z]", " ", line).split()
            first = words[0].upper() if words else ""
            if first in ("YES", "Y", "OUI"):
                return "yes"
            if first in ("NO", "N", "NON"):
                return "no"
            return None
        return None

    def check_email_replies(self):
        cfg = self.smtp()
        mail = imaplib.IMAP4_SSL(cfg["imap"])
        try:
            mail.login(cfg["user"], cfg["password"])
            mail.select("INBOX")
            # Read or unread doesn't matter: if the store's Gmail is open somewhere,
            # Gmail marks replies as read before we see them. Look at every alert reply
            # from the last 2 days instead; only pending alerts are acted on, and an
            # alert can only be answered once (resolve_alert).
            since = (datetime.now() - timedelta(days=2)).strftime("%d-%b-%Y")
            status, data = mail.search(None, f'(SINCE {since} SUBJECT "ref:")')
            if status != "OK":
                return
            for num in data[0].split():
                status, msg_data = mail.fetch(num, "(BODY.PEEK[])")
                if status != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                    continue
                message = email.message_from_bytes(msg_data[0][1])
                subject = str(email.header.make_header(email.header.decode_header(message.get("Subject", ""))))
                match = REF_PATTERN.search(subject)
                if not match or not self.is_pending(match.group(1)):
                    continue
                if parseaddr(message.get("From", ""))[1].lower() != self.recipient_of(match.group(1)):
                    continue  # only the person the alert was sent to may answer
                answer = self.parse_reply_answer(self.plain_text(message))
                if answer is None:
                    continue
                print(f"[imap] Reply '{answer.upper()}' received for alert {match.group(1)[:6]}...")
                self.handle_alert_response(match.group(1), answer, source="email reply")
        finally:
            try:
                mail.logout()
            except Exception:
                pass

    def email_reply_loop(self):
        cfg = self.smtp()
        if not cfg["user"] or not cfg["password"]:
            print("[imap] SMTP_EMAIL / SMTP_APP_PASSWORD not set - not checking for replies.")
            return
        every = int(_env("IMAP_POLL_SECONDS", "10"))
        print(f"[imap] Checking {cfg['user']} for YES/NO replies every {every}s")
        while not self.stop.is_set():
            try:
                self.check_email_replies()
            except Exception as error:
                print(f"[imap] Could not check replies: {error}")
            self.stop.wait(every)

    # ---------------------------------------------------------------------- MQTT
    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code != 0:
            self.mqtt_connected = False
            print(f"[mqtt] Connection rejected (reason={reason_code}); retrying in the background.")
            return
        self.mqtt_connected = True
        print(f"[mqtt] Connected (reason={reason_code})")
        for topic in list(MQTT_TOPICS) + [_env("MSP01_MQTT_TOPIC", "MSP01")]:
            client.subscribe(topic)

    def on_disconnect(self, client, userdata, *args, **kwargs):
        self.mqtt_connected = False

    def on_connect_fail(self, client, userdata):
        self.mqtt_connected = False
        print("[mqtt] Broker unavailable; retrying in the background (up to 30s between attempts).")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            print(f"[mqtt] Bad payload on {msg.topic}: {msg.payload!r}")
            return
        if msg.topic == _env("MSP01_MQTT_TOPIC", "MSP01"):
            from sensors import record_reading
            with self.app.app_context():
                try:
                    record_reading(payload, source="mqtt")
                except ValueError as error:
                    print(f"[mqtt] Ignored MSP01 message: {error}")
            return
        fridge_id = MQTT_TOPICS.get(msg.topic)
        if fridge_id is None:
            return
        try:
            temperature = float(payload["temperature"])
            humidity = float(payload["humidity"])
        except (KeyError, TypeError, ValueError):
            print(f"[mqtt] Bad payload on {msg.topic}: {msg.payload!r}")
            return
        if not (-40 <= temperature <= 100 and 0 <= humidity <= 100):
            print(f"[mqtt] Ignored out-of-range reading on {msg.topic}: {msg.payload!r}")
            return
        self.handle_reading(fridge_id, temperature, humidity)

    def start_mqtt(self):
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            print("[mqtt] paho-mqtt is not installed - fridge readings are disabled (pip install -r requirements.txt).")
            return
        host, port = _env("MQTT_BROKER_HOST", "localhost"), int(_env("MQTT_BROKER_PORT", "1883"))
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="smart-store-phase4")
        client.on_connect, client.on_message, client.on_disconnect = self.on_connect, self.on_message, self.on_disconnect
        client.on_connect_fail = self.on_connect_fail
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        try:
            # The background loop retries even when the very first connection fails.
            client.connect_async(host, port, keepalive=60)
            self.mqtt_client = client
            client.loop_start()
        except Exception as error:
            client.disconnect()
            client.loop_stop()
            self.mqtt_client = None
            print(f"[mqtt] Could not start MQTT for {host}:{port} ({error}); check MQTT configuration.")

    def start(self):
        self.start_mqtt()
        thread = threading.Thread(target=self.email_reply_loop, daemon=True, name="email-replies")
        thread.start()
        self.threads.append(thread)

    def shutdown(self):
        self.stop.set()
        if self.mqtt_client is not None:
            self.mqtt_client.disconnect()
            self.mqtt_client.loop_stop()
        self.mqtt_connected = False
        motor_control.cleanup()


def init_monitoring(app, start_background=True):
    """Attach the fridge monitor to the app; background threads only when asked."""
    monitor = Monitor(app)
    app.extensions["monitor"] = monitor
    app.register_blueprint(monitoring_bp)
    if start_background:
        monitor.start()
    return monitor


def monitor():
    return current_app.extensions["monitor"]


def monitor_shutdown(app):
    """Stop MQTT/mailbox threads and release the GPIO pins."""
    running = app.extensions.get("monitor")
    if running is not None:
        running.shutdown()


# ---------------------------------------------------------------------- routes
def _current_user():
    return db.get_customer(session["customer_id"]) if session.get("customer_id") else None


@monitoring_bp.before_app_request
def remember_active_admin():
    """Temperature alerts go to the admin who is currently using the store."""
    monitor = current_app.extensions.get("monitor")
    if monitor is None or not session.get("customer_id"):
        return
    user = _current_user()
    if user and user.get("is_admin"):
        monitor.note_admin_activity(user.get("email"))


@monitoring_bp.before_request
def require_admin():
    if request.endpoint == "monitoring.alert_confirm":
        return  # protected by its secret one-time token (the link inside the email)
    user = _current_user()
    if not user:
        abort(401, "Log in on the account page to open the monitoring dashboard.")
    if not user.get("is_admin"):
        abort(403, "Administrator access required.")


@monitoring_bp.after_request
def no_store(response):
    response.headers["Cache-Control"] = "private, no-store"
    if request.endpoint == "monitoring.alert_confirm":
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
    return response


@monitoring_bp.get("/")
def page():
    return render_template("monitoring.html", title="Fridges & fan", active="monitoring", no_refresh=True)


def readings_payload():
    m = monitor()
    out = {}
    with m.lock:
        snapshot = {f: dict(r) for f, r in m.latest.items()}
    now = datetime.now(timezone.utc)
    stale_after = m.stale_seconds
    for fridge_id, reading in snapshot.items():
        threshold = m.get_threshold(fridge_id)
        age = None
        if reading["updated_at"]:
            try:
                received = datetime.fromisoformat(reading["updated_at"])
                # Support an older in-memory timestamp without a UTC offset.
                if received.tzinfo is None:
                    received = received.astimezone()
                age = max(0, (now - received).total_seconds())
            except (ValueError, TypeError):
                pass
        has_reading = reading["temperature"] is not None
        online = has_reading and age is not None and age <= stale_after
        warm = reading["temperature"] is not None and reading["temperature"] > threshold
        status = "waiting" if not has_reading else "offline" if not online else "warning" if warm else "normal"
        out[fridge_id] = {**reading, "threshold": threshold, "status": status,
                          "online": online, "age_seconds": None if age is None else int(age),
                          "stale_after_seconds": stale_after}
    return out


@monitoring_bp.get("/api/readings")
def api_readings():
    return jsonify(readings_payload())


@monitoring_bp.get("/api/thresholds")
def api_thresholds():
    m = monitor()
    return jsonify({f: m.get_threshold(f) for f in FRIDGES})


@monitoring_bp.post("/api/thresholds/<int:fridge_id>")
def api_set_threshold(fridge_id):
    if fridge_id not in FRIDGES:
        return jsonify(success=False, message="Unknown fridge id."), 404
    data = request.get_json(silent=True) or {}
    try:
        value = float(data.get("threshold"))
    except (TypeError, ValueError):
        return jsonify(success=False, message="threshold must be a number."), 400
    if not -30 <= value <= 60:
        return jsonify(success=False, message="threshold must be between -30 and 60 °C."), 400
    m = monitor()
    m.set_threshold(fridge_id, value)
    m.add_notification(fridge_id, f"Refrigerator {fridge_id} threshold set to {value:.1f}C.", "info",
                       f"Seuil du réfrigérateur {fridge_id} réglé à {value:.1f}C.")
    return jsonify(success=True, fridge_id=fridge_id, threshold=value)


@monitoring_bp.get("/api/history/<int:fridge_id>")
def api_history(fridge_id):
    if fridge_id not in FRIDGES:
        return jsonify(success=False, message="Unknown fridge id."), 404
    try:
        hours = min(max(int(request.args.get("hours", "6")), 1), 168)
    except ValueError:
        hours = 6
    conn = db.get_connection()
    try:
        rows = conn.execute("""SELECT recorded_at, temperature, humidity FROM fridge_readings
                               WHERE fridge_id = ? AND recorded_at >= datetime('now', ?) ORDER BY recorded_at""",
                            (fridge_id, f"-{hours} hours")).fetchall()
    finally:
        conn.close()
    return jsonify([dict(r) for r in rows])


@monitoring_bp.get("/api/notifications")
def api_notifications():
    m = monitor()
    with m.lock:
        return jsonify(m.feed[:20])


@monitoring_bp.get("/api/fan/status")
def api_fan_status():
    return jsonify(monitor().fan)


@monitoring_bp.post("/api/fan/speed")
def api_fan_speed():
    m = monitor()
    data = request.get_json(silent=True) or {}
    try:
        duty = int(data.get("duty_cycle"))
    except (TypeError, ValueError):
        return jsonify(success=False, message="duty_cycle must be an integer from 0 to 100."), 400
    if not 0 <= duty <= 100:
        return jsonify(success=False, message="duty_cycle must be between 0 and 100."), 400
    m.fan["duty_cycle"] = duty
    if m.fan["status"] == "ON":
        motor_control.set_fan_speed(duty)
        if duty == 0:
            m.fan["status"] = "OFF"
        m.add_notification(None, f"Fan duty cycle set to {duty}%.", "info", f"Vitesse du ventilateur réglée à {duty} %.")
    return jsonify(success=True, **m.fan)


@monitoring_bp.post("/api/fan/toggle")
def api_fan_toggle():
    m = monitor()
    if m.fan["status"] == "OFF":
        duty = m.start_fan()
        m.add_notification(None, f"Fan turned ON manually at {duty}% duty cycle.", "info",
                           f"Ventilateur allumé manuellement à {duty} %.")
    else:
        motor_control.fan_off()
        m.fan["status"] = "OFF"
        m.add_notification(None, "Fan turned OFF manually from the dashboard.", "info",
                           "Ventilateur éteint manuellement depuis le tableau de bord.")
    return jsonify(m.fan)


@monitoring_bp.route("/alert/confirm", methods=["GET", "POST"])
def alert_confirm():
    values = request.form if request.method == "POST" else request.args
    token, action = values.get("token", ""), values.get("action", "")
    if action not in ("yes", "no"):
        abort(400, "Choose YES or NO using the link in your alert email.")
    if request.method == "POST":
        expected = session.get("alert_confirmation_csrf", "")
        submitted = request.form.get("csrf_token", "")
        if not expected or not secrets.compare_digest(expected.encode("utf-8"), submitted.encode("utf-8")):
            abort(403, "Reopen the alert link and confirm your choice on that page.")
        row = monitor().handle_alert_response(token, action, source="email link")
    else:
        # Email scanners, previews and browser prefetches must never operate the fan.
        row = monitor().get_alert(token)
    if row is None:
        state, code = "invalid", 404
    elif row["status"] == "expired":
        state, code = "expired", 410
    elif row["status"] != "pending":
        state, code = ("recorded" if row.get("just_resolved") else "answered"), 200
    else:
        state, code = "confirm", 200
        session.setdefault("alert_confirmation_csrf", secrets.token_urlsafe(32))
    return render_template("alert_confirmation.html", alert=row, action=action, state=state,
                           csrf_token=session.get("alert_confirmation_csrf", "")), code
