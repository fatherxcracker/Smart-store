"""
Smart Store - Phase 1
Backend: Python (Flask) + SQLite
Frontend: HTML / CSS / JavaScript (static files, talks to the backend via fetch/AJAX)
Hardware: Raspberry Pi 5 - Blue LED (success), Red LED + Buzzer (failure)
"""

import os
import sqlite3

from flask import Flask, render_template, request, jsonify

# ---------------------------------------------------------------------------
# Paths / Config
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "database", "smartstore.db")

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Hardware setup (Raspberry Pi 5 GPIO)
# ---------------------------------------------------------------------------
# BCM pin numbers - change these to match how you wire your breadboard.
BLUE_LED_PIN = 17     # success indicator
RED_LED_PIN = 27      # failure indicator
BUZZER_PIN = 22        # failure indicator

# We try to use the real gpiozero library (works on the Raspberry Pi).
# If this code is run on a normal laptop (no GPIO hardware), we fall back
# to a "mock" version that just prints to the console instead of crashing.
# This lets the whole team develop/test the website on their own laptops,
# and it will automatically use the real hardware once it's run on the Pi.
try:
    from gpiozero import LED, Buzzer

    blue_led = LED(BLUE_LED_PIN)
    red_led = LED(RED_LED_PIN)
    buzzer = Buzzer(BUZZER_PIN)
    HARDWARE_MODE = "real"
    print("[hardware] gpiozero detected real Raspberry Pi GPIO pins.")
except Exception as gpio_error:  # not on a Pi, or no pin factory available
    print(f"[hardware] GPIO not available ({gpio_error}). Using mock hardware for local testing.")

    class MockDevice:
        """Stands in for an LED/Buzzer when there's no real Raspberry Pi attached."""

        def __init__(self, name):
            self.name = name
            self.is_on = False

        def on(self):
            self.is_on = True
            print(f"[mock-hardware] {self.name} -> ON")

        def off(self):
            self.is_on = False
            print(f"[mock-hardware] {self.name} -> OFF")

    blue_led = MockDevice("BLUE LED (success)")
    red_led = MockDevice("RED LED (failure)")
    buzzer = MockDevice("BUZZER (failure)")
    HARDWARE_MODE = "mock"


def signal_success():
    """Blue LED on briefly to confirm a successful insert."""
    blue_led.on()


def clear_success():
    blue_led.off()


def signal_failure():
    """Red LED + buzzer on to signal a failed insert."""
    red_led.on()
    buzzer.on()


def clear_failure():
    red_led.off()
    buzzer.off()


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(os.path.join(BASE_DIR, "database"), exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            address TEXT NOT NULL,
            telephone_number TEXT NOT NULL,
            email_address TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS system_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_email TEXT,
            status TEXT NOT NULL CHECK (status IN ('SUCCESS', 'FAILURE')),
            blue_led INTEGER DEFAULT 0,
            red_led INTEGER DEFAULT 0,
            buzzer INTEGER DEFAULT 0,
            message TEXT NOT NULL,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()
    print(f"[database] Ready at {DATABASE_PATH}")


def log_event(email, status, blue, red, buz, message):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO system_logs (customer_email, status, blue_led, red_led, buzzer, message)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (email, status, int(blue), int(red), int(buz), message),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Serves the single frontend page (HTML/CSS/JS handle the rest)."""
    return render_template("index.html")


@app.route("/api/customers", methods=["GET"])
def get_customers():
    """Returns all customers as JSON, used by the frontend to render the table."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT customer_id, full_name, address, telephone_number, email_address, created_at "
        "FROM customers ORDER BY customer_id DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route("/api/customers", methods=["POST"])
def add_customer():
    """
    Inserts a new customer.
    On success -> blue LED, JSON success response.
    On failure (e.g. duplicate email, missing field) -> red LED + buzzer, JSON error response.
    """
    data = request.get_json(silent=True) or request.form

    full_name = (data.get("full_name") or "").strip()
    address = (data.get("address") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip()

    # Basic server-side validation
    if not all([full_name, address, phone, email]):
        signal_failure()
        log_event(email or "unknown", "FAILURE", 0, 1, 1, "Missing required field.")
        return jsonify({
            "success": False,
            "message": "All fields are required.",
            "hardware": {"blue_led": False, "red_led": True, "buzzer": True},
        }), 400

    conn = None
    try:
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO customers (full_name, address, telephone_number, email_address)
            VALUES (?, ?, ?, ?)
            """,
            (full_name, address, phone, email),
        )
        conn.commit()

        signal_success()
        log_event(email, "SUCCESS", 1, 0, 0, "Customer added successfully. Blue LED activated.")

        return jsonify({
            "success": True,
            "message": "Customer added successfully!",
            "hardware": {"blue_led": True, "red_led": False, "buzzer": False},
        }), 201

    except sqlite3.IntegrityError:
        if conn is not None:
            conn.rollback()
            conn.close()
            conn = None
        signal_failure()
        log_event(email, "FAILURE", 0, 1, 1, "Duplicate email address.")
        return jsonify({
            "success": False,
            "message": "That email address is already registered.",
            "hardware": {"blue_led": False, "red_led": True, "buzzer": True},
        }), 409

    except Exception as error:
        if conn is not None:
            conn.rollback()
            conn.close()
            conn = None
        signal_failure()
        log_event(email, "FAILURE", 0, 1, 1, f"Unexpected error: {error}")
        return jsonify({
            "success": False,
            "message": "Something went wrong. Please try again.",
            "hardware": {"blue_led": False, "red_led": True, "buzzer": True},
        }), 500

    finally:
        if conn is not None:
            conn.close()


@app.route("/api/hardware/reset", methods=["POST"])
def reset_hardware():
    """Called by the frontend a couple seconds after showing a notification,
    so the LEDs/buzzer turn back off automatically."""
    clear_success()
    clear_failure()
    return jsonify({"success": True})


@app.route("/api/logs", methods=["GET"])
def get_logs():
    """Optional: view the system_logs table (useful for debugging/demoing)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM system_logs ORDER BY log_id DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


if __name__ == "__main__":
    init_db()
    print(f"[hardware] Running in '{HARDWARE_MODE}' mode.")
    # host="0.0.0.0" makes it reachable from other devices on your network
    # (e.g. viewing the Pi's site from your phone/laptop)
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
