"""Personal receipt reporting scoped to the authenticated customer."""
from .common import rows, currency
from datetime import datetime, timezone


def generate(conn, period, customer_id, query="", product_id=None):
    options = rows(conn, """SELECT i.product_id AS id, MAX(i.product_name) AS name
        FROM purchase_items i JOIN purchases p ON p.id = i.purchase_id
        WHERE p.customer_id = ? GROUP BY i.product_id ORDER BY name""", (customer_id,))
    receipts = rows(conn, """SELECT id, receipt_number, created_at, subtotal, points_discount,
        points_redeemed, gst, qst, total, points_earned, payment_method FROM purchases
        WHERE customer_id = ? AND created_at >= ? AND created_at < ? ORDER BY created_at DESC, id DESC""", (customer_id, *period.bounds))
    items = rows(conn, """SELECT i.*, p.created_at, p.receipt_number FROM purchase_items i
        JOIN purchases p ON p.id = i.purchase_id
        WHERE p.customer_id = ? AND p.created_at >= ? AND p.created_at < ?
        ORDER BY p.created_at, p.id, i.id""", (customer_id, *period.bounds))
    by_receipt = {}
    for item in items:
        by_receipt.setdefault(item["purchase_id"], []).append(item)
    matched = [i for i in items if (not query or query.casefold() in i["product_name"].casefold())
               and (product_id is None or i["product_id"] == product_id)]
    ids = {i["purchase_id"] for i in matched}
    for receipt in receipts:
        receipt["items"] = by_receipt.get(receipt["id"], [])
    spending = {day: 0.0 for day in period.days}
    for receipt in receipts:
        spending[period.local_day(receipt["created_at"])] += receipt["total"]
    return {"spending": [{"date": day, "total": currency(total)} for day, total in spending.items()],
            "receipts": [r for r in receipts if r["id"] in ids] if query or product_id else receipts,
            "total_spent": currency(sum(r["total"] for r in receipts)),
            "receipt_count": len(receipts), "products": options, "matches": matched,
            "purchase_times": len(ids), "units": sum(i["quantity"] for i in matched),
            "price_history": [{"date": datetime.fromisoformat(i["created_at"]).replace(tzinfo=timezone.utc).astimezone(period.zone).isoformat(),
                               "price": i["unit_price"]} for i in matched] if product_id else []}
