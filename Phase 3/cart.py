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


@cart_api.post("/api/cart/rfid")
def scan_rfid():
    """Add each new EPC once, ignoring repeated RFID readings."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(
            success=False,
            message="Send RFID codes as JSON.",
        ), 400

    epcs = data.get("epcs")

    if not isinstance(epcs, list) or not 1 <= len(epcs) <= 100:
        return jsonify(
            success=False,
            message="Send between 1 and 100 EPC readings.",
        ), 400

    # Normalize EPCs and remove duplicates within this batch.
    normalized = set()

    for epc in epcs:
        if not isinstance(epc, str):
            return jsonify(
                success=False,
                message="Each EPC must be text.",
            ), 400

        epc = epc.strip().upper()

        if (
            not epc
            or len(epc) > 24
            or any(character not in "0123456789ABCDEF" for character in epc)
        ):
            return jsonify(
                success=False,
                message="An EPC must contain at most 24 hexadecimal characters.",
            ), 400

        normalized.add(epc)

    # Remember tags across requests and page refreshes.
    seen = set(session.get("rfid_seen", []))
    new_epcs = normalized - seen

    if not new_epcs:
        return cart_response(
            "These RFID tags have already been read. Cart unchanged."
        )

    # Bound session size because Flask stores it in a signed cookie.
    if len(seen | new_epcs) > 40:
        return jsonify(
            success=False,
            message="RFID limit reached. Reset the cart to start a new session.",
        ), 400

    products = db.find_by_epcs(sorted(new_epcs))
    unknown = sorted(new_epcs - set(products))

    if unknown:
        return jsonify(
            success=False,
            message="Unknown RFID tags: " + ", ".join(unknown),
        ), 404

    cart = get_cart()

    # Validate the entire batch before saving any changes.
    for epc in sorted(new_epcs):
        product = products[epc]
        product_id = str(product["id"])
        quantity = cart.get(product_id, 0) + 1

        if quantity > product["in_stock"]:
            return jsonify(
                success=False,
                message=f"Not enough stock for {product['name']}.",
            ), 400

        if product_id not in cart and len(cart) >= 40:
            return jsonify(
                success=False,
                message="The cart can contain at most 40 different products.",
            ), 400

        cart[product_id] = quantity

    save_cart(cart)
    session["rfid_seen"] = sorted(seen | new_epcs)

    return cart_response(
        f"{len(new_epcs)} RFID item(s) added to your cart."
    )


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

    # Keep RFID history so repeated readings do not restore removed items.
    return cart_response("Item removed from your cart.")


@cart_api.delete("/api/cart")
def reset_cart():
    session.pop("shopping_cart", None)
    session.pop("rfid_seen", None)

    return cart_response("Your cart has been reset.")