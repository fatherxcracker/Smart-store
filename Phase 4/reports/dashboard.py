"""Admin dashboard widgets: today's store numbers, stock alerts, fridges and the BLE sensor."""
from datetime import timedelta

import db
import sensors
from . import customers, inventory, sales
from .common import Period, today_local


def generate(conn, app):
    today = today_local()
    day = sales.generate(conn, Period(today, today), 5)
    week = sales.generate(conn, Period(today - timedelta(days=6), today), 5)
    buyers = customers.generate(conn, Period(today, today))
    stock = inventory.generate(conn)
    low = [p for p in stock["products"] if p["stock_level"] == "low"]
    fridges = None
    monitor = app.extensions.get("monitor")
    if monitor is not None:
        from monitoring import readings_payload
        fridges = {"readings": readings_payload(), "fan": dict(monitor.fan), "mqtt": monitor.mqtt_connected}
    notes = db.get_notifications(8)
    return {
        "today": {"date": today.isoformat(), "total": day["totals"]["total"], "orders": day["orders"],
                  "units": day["units"], "customers": buyers["total_customers"]},
        "week": {"daily": week["daily"], "total": week["totals"]["total"], "top": week["top"][:3]},
        "stock": {"units": stock["units"], "low_count": stock["low_count"], "moderate_count": stock["moderate_count"],
                  "low": [{"name": p["name"], "category": p["category"], "in_stock": p["in_stock"], "limit": p["low_limit"]}
                          for p in low[:8]]},
        "fridges": fridges,
        "sensor": sensors.latest(),
        "notifications": [{"level": n["level"], "message": n["message_en"], "created_at": n["created_at"]} for n in notes],
    }
