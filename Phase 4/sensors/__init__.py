"""Phase 4: Minew MSP01 BLE sensor (temperature, humidity, light, motion)."""

import hmac
import os

from flask import Blueprint, abort, jsonify, render_template, request, session

import db

sensors_bp = Blueprint("sensors", __name__, url_prefix="/sensors")

STALE_SECONDS = int(os.environ.get("SENSOR_STALE_SECONDS", "300"))
FIELDS = ("temperature", "humidity", "light", "motion", "battery")


def _number(payload, key, low, high):
    value = payload.get(key)
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"{key} must be a number.")
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be a number.")
    if not low <= value <= high:
        raise ValueError(f"{key} must be between {low} and {high}.")
    return value


def record_reading(payload, source="api", sensor="msp01"):
    """Validate and store one reading. Any subset of the fields is allowed."""
    if not isinstance(payload, dict):
        raise ValueError("Send the reading as a JSON object.")
    temperature = _number(payload, "temperature", -40, 100)
    humidity = _number(payload, "humidity", 0, 100)
    light = _number(payload, "light", 0, 200000)
    battery = _number(payload, "battery", 0, 100)
    motion = payload.get("motion")
    if motion is not None:
        if str(motion).lower() in ("1", "true", "yes", "on", "detected"):
            motion = 1
        elif str(motion).lower() in ("0", "false", "no", "off", "none"):
            motion = 0
        else:
            raise ValueError("motion must be true or false.")
    if all(v is None for v in (temperature, humidity, light, battery, motion)):
        raise ValueError("The reading has none of: temperature, humidity, light, motion, battery.")
    conn = db.get_connection()
    try:
        conn.execute(
            "INSERT INTO sensor_readings (sensor, temperature, humidity, light, motion, battery, source) VALUES (?,?,?,?,?,?,?)",
            (sensor, temperature, humidity, light, motion, None if battery is None else int(battery), source))
        conn.execute("DELETE FROM sensor_readings WHERE recorded_at < datetime('now', '-7 days')")
        conn.commit()
    finally:
        conn.close()


def latest(sensor="msp01"):
    """Newest value of each field, how old it is, and motion activity."""
    conn = db.get_connection()
    try:
        out = {}
        for field in FIELDS:
            row = conn.execute(
                f"""SELECT {field} AS value, recorded_at, source,
                           CAST(strftime('%s','now') - strftime('%s', recorded_at) AS INTEGER) AS age
                    FROM sensor_readings WHERE sensor = ? AND {field} IS NOT NULL ORDER BY id DESC LIMIT 1""",
                (sensor,)).fetchone()
            out[field] = None if not row else {"value": row["value"], "recorded_at": row["recorded_at"],
                                               "age_seconds": max(row["age"], 0), "source": row["source"]}
        motion = conn.execute(
            """SELECT recorded_at, CAST(strftime('%s','now') - strftime('%s', recorded_at) AS INTEGER) AS age
               FROM sensor_readings WHERE sensor = ? AND motion = 1 ORDER BY id DESC LIMIT 1""", (sensor,)).fetchone()
        hour = conn.execute("SELECT COUNT(*) FROM sensor_readings WHERE sensor=? AND motion=1 AND recorded_at >= datetime('now','-1 hour')",
                            (sensor,)).fetchone()[0]
        today = conn.execute("SELECT COUNT(*) FROM sensor_readings WHERE sensor=? AND motion=1 AND recorded_at >= datetime('now','-24 hours')",
                             (sensor,)).fetchone()[0]
    finally:
        conn.close()
    newest = min((v["age_seconds"] for v in out.values() if v), default=None)
    out["online"] = newest is not None and newest <= STALE_SECONDS
    out["seconds_since_update"] = newest
    out["last_motion_seconds"] = None if not motion else max(motion["age"], 0)
    out["motion_last_hour"] = hour
    out["motion_last_24h"] = today
    out["stale_after_seconds"] = STALE_SECONDS
    return out


def history(hours=6, sensor="msp01"):
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """SELECT recorded_at, temperature, humidity, light, motion FROM sensor_readings
               WHERE sensor = ? AND recorded_at >= datetime('now', ?) ORDER BY id""",
            (sensor, f"-{int(hours)} hours")).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def _admin():
    user = db.get_customer(session["customer_id"]) if session.get("customer_id") else None
    return bool(user and user.get("is_admin"))


@sensors_bp.before_request
def guard():
    if request.endpoint == "sensors.ingest":
        return  # has its own token check
    if not session.get("customer_id"):
        abort(401, "Log in on the account page to see the sensor.")
    if not _admin():
        abort(403, "Administrator access required.")


@sensors_bp.after_request
def no_store(response):
    response.headers["Cache-Control"] = "private, no-store"
    return response


@sensors_bp.get("/")
def page():
    return render_template("sensors.html", title="Minew MSP01 sensor", active="sensors", no_refresh=True)


@sensors_bp.get("/api/latest")
def api_latest():
    return jsonify(latest())


@sensors_bp.get("/api/history")
def api_history():
    try:
        hours = min(max(int(request.args.get("hours", "6")), 1), 168)
    except ValueError:
        hours = 6
    return jsonify(history(hours))


@sensors_bp.post("/api/ingest")
def ingest():
    token = os.environ.get("SENSOR_INGEST_TOKEN", "")
    sent = request.headers.get("X-Sensor-Token", "")
    allowed = bool(token) and hmac.compare_digest(sent, token)
    if not allowed and not _admin():
        return jsonify(success=False, message="Send the X-Sensor-Token header (set SENSOR_INGEST_TOKEN in .env)."), 401
    try:
        record_reading(request.get_json(silent=True), source="api")
    except ValueError as error:
        return jsonify(success=False, message=str(error)), 400
    return jsonify(success=True), 201


def init_sensors(app, start_background=True):
    app.register_blueprint(sensors_bp)
    if not start_background:
        return
    from .minew_msp01 import start_ble_scanner, start_simulator
    if os.environ.get("MSP01_SIMULATE") == "1":
        start_simulator(app, record_reading)
    if os.environ.get("MSP01_BLE") == "1":
        start_ble_scanner(app, record_reading, os.environ.get("MINEW_DEVICE_ADDRESS", ""))
