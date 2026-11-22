"""Current inventory, read from the store's calculated inventory view."""
from .common import rows


def generate(conn, category=""):
    categories = [r["category"] for r in rows(conn, "SELECT DISTINCT category FROM inventory ORDER BY category")]
    products = rows(conn, "SELECT * FROM inventory" + (" WHERE category = ?" if category else "") + " ORDER BY category, name", (category,) if category else ())
    for product in products:
        product["stock_level"] = "low" if product["in_stock"] < 5 else "moderate" if product["in_stock"] < 10 else "good"
    return {"products": products, "categories": categories,
            "units": sum(p["in_stock"] for p in products),
            "low_count": sum(p["stock_level"] == "low" for p in products)}
