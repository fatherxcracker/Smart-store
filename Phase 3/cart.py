"""Shopping-cart API for Smart Store Phase 3."""

from flask import Blueprint, jsonify, request, session

import db

cart_api = Blueprint("cart_api", __name__)


def get_cart():
    """Return product IDs and quantities for this browser session."""
    return dict(session.get("shopping_cart", {}))


def save_cart(cart):
    session["shopping_cart"] = cart


def build_cart(cart):
    """Use database prices to calculate the shopping list and totals."""
    items = []
    subtotal = 0.0

    for product_id, quantity in cart.items():
        product = db.get_product(int(product_id))

        if product is None:
            items.append({
                "product_id": int(product_id),
                "name": f"Unavailable product #{product_id}",
                "quantity": quantity,
                "unit_price": 0,
                "line_total": 0,
                "available": False,
            })
            continue

        line_total = round(product["price"] * quantity, 2)
        subtotal += line_total

        items.append({
            "product_id": product["id"],
            "name": product["name"],
            "quantity": quantity,
            "unit_price": product["price"],
            "line_total": line_total,
            "available": quantity <= product["in_stock"],
        })

    totals = db.calculate_totals(subtotal)

    return {
        "items": items,
        "item_count": sum(item["quantity"] for item in items),
        "subtotal": totals["subtotal"],
        "gst": totals["gst"],
        "qst": totals["qst"],
        "total": totals["total"],
        "can_checkout": bool(items) and all(
            item["available"] for item in items
        ),
    }


def cart_response(message=""):
    return jsonify({
        "success": True,
        "message": message,
        "cart": build_cart(get_cart()),
    })


@cart_api.get("/api/cart")
def view_cart():
    return cart_response()


@cart_api.post("/api/cart/barcode")
def scan_barcode():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(
            success=False,
            message="Send a barcode as JSON.",
        ), 400

    upc = data.get("upc")

    if not isinstance(upc, str) or not upc.strip():
        return jsonify(
            success=False,
            message="Scan or enter a barcode.",
        ), 400

    product = db.find_by_upc(upc)

    if product is None:
        return jsonify(
            success=False,
            message="No product matches this barcode.",
        ), 404

    cart = get_cart()
    product_id = str(product["id"])
    quantity = cart.get(product_id, 0) + 1

    if quantity > product["in_stock"]:
        return jsonify(
            success=False,
            message=f"Only {product['in_stock']} units available.",
        ), 400

    # Keep the session cookie small enough for a classroom demo.
    if product_id not in cart and len(cart) >= 40:
        return jsonify(
            success=False,
            message="The cart can contain at most 40 different products.",
        ), 400

    cart[product_id] = quantity
    save_cart(cart)

    return cart_response(f"{product['name']} added to your cart.")


@cart_api.delete("/api/cart/items/<int:product_id>")
def remove_item(product_id):
    cart = get_cart()

    if str(product_id) not in cart:
        return jsonify(
            success=False,
            message="This product is not in your cart.",
        ), 404

    del cart[str(product_id)]
    save_cart(cart)

    return cart_response("Item removed from your cart.")


@cart_api.delete("/api/cart")
def reset_cart():
    session.pop("shopping_cart", None)
    return cart_response("Your cart has been reset.")