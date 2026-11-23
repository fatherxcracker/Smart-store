"""Current inventory, read from the store's calculated inventory view.

Stock level colours use a low-stock limit that the administrator can set for
each category (default LOW_STOCK_LIMIT, 5): red below the limit, yellow below
twice the limit, green otherwise.
"""
import db
from .common import rows


def level(in_stock, limit):
    if in_stock < limit:
        return "low"
    return "moderate" if in_stock < limit * 2 else "good"


def generate(conn, category=""):
    categories = [r["category"] for r in rows(conn, "SELECT DISTINCT category FROM inventory ORDER BY category")]
    limits = {r["category"]: r["low_stock"] for r in rows(conn, "SELECT category, low_stock FROM category_thresholds")}
    products = rows(conn, "SELECT * FROM inventory" + (" WHERE category = ?" if category else "") + " ORDER BY category, name",
                    (category,) if category else ())
    for product in products:
        product["low_limit"] = limits.get(product["category"], db.DEFAULT_LOW_STOCK)
        product["stock_level"] = level(product["in_stock"], product["low_limit"])
    peak = max([p["in_stock"] for p in products] + [1])
    for product in products:
        product["bar"] = round(product["in_stock"] / peak * 100)
    shown = sorted({p["category"] for p in products})
    return {"products": products, "categories": categories,
            "limits": {c: limits.get(c, db.DEFAULT_LOW_STOCK) for c in categories},
            "default_limit": db.DEFAULT_LOW_STOCK,
            "units": sum(p["in_stock"] for p in products),
            "low_count": sum(p["stock_level"] == "low" for p in products),
            "moderate_count": sum(p["stock_level"] == "moderate" for p in products),
            "shown_categories": shown}
