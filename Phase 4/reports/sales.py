"""Historical product sales and receipt totals without join multiplication."""
from .common import rows, currency


def generate(conn, period, limit=5):
    products = rows(conn, """SELECT p.id, p.name, p.category, p.is_active,
        COALESCE(s.units, 0) AS units, COALESCE(s.gross, 0) AS gross
        FROM products p LEFT JOIN (
            SELECT i.product_id, SUM(i.quantity) AS units, SUM(i.line_total) AS gross
            FROM purchase_items i JOIN purchases r ON r.id = i.purchase_id
            WHERE r.created_at >= ? AND r.created_at < ? GROUP BY i.product_id
        ) s ON s.product_id = p.id
        WHERE p.is_active = 1 OR s.product_id IS NOT NULL ORDER BY units DESC, p.name, p.id""", period.bounds)
    receipts = rows(conn, "SELECT id, subtotal, points_discount, gst, qst, total, created_at FROM purchases WHERE created_at >= ? AND created_at < ? ORDER BY created_at, id", period.bounds)
    daily = {day: {"date": day, "total": 0, "orders": 0} for day in period.days}
    for receipt in receipts:
        entry = daily[period.local_day(receipt["created_at"])]
        entry["total"] += receipt["total"]
        entry["orders"] += 1
    for entry in daily.values():
        entry["total"] = currency(entry["total"])
    totals = {key: currency(sum(r[key] for r in receipts)) for key in ("subtotal", "points_discount", "gst", "qst", "total")}
    totals["net_sales"] = currency(totals["subtotal"] - totals["points_discount"])
    return {"products": products, "top": products[:limit],
            "bottom": sorted(products, key=lambda p: (p["units"], p["name"], p["id"]))[:limit],
            "daily": list(daily.values()), "totals": totals, "orders": len(receipts),
            "units": sum(p["units"] for p in products)}
