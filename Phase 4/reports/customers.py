"""Purchasing customers, not physical visitors or BLE motion events."""
from .common import rows


def generate(conn, period):
    receipts = rows(conn, "SELECT customer_id, created_at FROM purchases WHERE created_at >= ? AND created_at < ? ORDER BY created_at", period.bounds)
    previous = {r["customer_id"] for r in rows(conn, "SELECT DISTINCT customer_id FROM purchases WHERE created_at < ? AND customer_id IS NOT NULL", (period.bounds[0],))}
    buyers = {r["customer_id"] for r in receipts if r["customer_id"] is not None}
    days = {day: {"date": day, "buyers": set(), "orders": 0, "guest_orders": 0} for day in period.days}
    for receipt in receipts:
        entry = days[period.local_day(receipt["created_at"])]
        entry["orders"] += 1
        if receipt["customer_id"] is None:
            entry["guest_orders"] += 1
        else:
            entry["buyers"].add(receipt["customer_id"])
    for entry in days.values():
        entry["buyers"] = len(entry["buyers"])
    daily = list(days.values())
    maximum = max(day["buyers"] for day in daily)
    minimum = min(day["buyers"] for day in daily)
    return {"total_customers": len(buyers), "new_customers": len(buyers - previous),
            "returning_customers": len(buyers & previous),
            "guest_orders": sum(day["guest_orders"] for day in daily), "daily": daily,
            "busiest": [day for day in daily if day["buyers"] == maximum],
            "quietest": [day for day in daily if day["buyers"] == minimum]}
