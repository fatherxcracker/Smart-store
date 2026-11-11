"""Shopping-cart API for Smart Store Phase 3."""

import secrets

from flask import Blueprint, jsonify, request, session

import db
import rfid_reader

cart_api = Blueprint("cart_api", __name__)


def get_cart():
    """Return product IDs and quantities for this browser session."""
    return dict(session.get("shopping_cart", {}))


def save_cart(cart):
    session["shopping_cart"] = cart
    session["checkout_key"] = secrets.token_hex(32)


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

        tagged_quantity = sum(1 for pid in session.get("rfid_cart_tags", {}).values() if pid == product["id"])
        eligible = (tagged_quantity <= quantity and
                    quantity - tagged_quantity <= db.get_untagged_stock(product["id"]))
        items.append({
            "product_id": product["id"],
            "name": product["name"],
            "quantity": quantity,
            "unit_price": product["price"],
            "line_total": line_total,
            "available": quantity <= product["in_stock"] and eligible,
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
    if get_cart() and not session.get("checkout_key"):
        session["checkout_key"] = secrets.token_hex(32)
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

    tagged_quantity = sum(1 for pid in session.get("rfid_cart_tags", {}).values() if pid == product["id"])
    if quantity - tagged_quantity > db.get_untagged_stock(product["id"]):
        return jsonify(success=False, message="No more untagged stock available. Scan the RFID tags for tagged items."), 400

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


def add_epcs_to_cart(epcs, manual=False):
    """Add each new EPC once, ignoring repeated RFID readings.
    Used by both the RFID reader scan and the JSON endpoint."""
    if not isinstance(epcs, list) or len(epcs) > 100:
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

    if not normalized:
        return cart_response("No RFID tags detected. Place the items on the reader.")

    # Remember tags across requests and page refreshes.
    # Unknown tags are remembered too, so a stray tag left on the reader
    # is reported once instead of on every auto-scan.
    if manual:
        # The customer pressed "Scan all items": add every tag on the reader
        # that isn't in the cart right now, including items removed earlier.
        seen = set(session.get("rfid_cart_tags", {}))
        unknown_seen = set()
    else:
        seen = set(session.get("rfid_seen", []))
        unknown_seen = set(session.get("rfid_unknown", []))
    new_epcs = normalized - seen - unknown_seen

    if not new_epcs:
        return cart_response(
            "These RFID tags have already been read. Cart unchanged."
        )

    products = db.find_by_epcs(sorted(new_epcs))
    sold = db.find_sold_tags(sorted(new_epcs - set(products)))
    unknown = sorted(new_epcs - set(products) - set(sold))
    known = sorted(new_epcs & set(products))

    # Only truly unknown tags are remembered; a sold tag that an employee
    # re-assigns must work on the next scan.
    if unknown:
        session["rfid_unknown"] = sorted(unknown_seen | set(unknown))[-40:]

    problems = []
    if sold:
        problems.append(
            "Already sold: "
            + ", ".join(f"{info['name']} (receipt {info['receipt_number']})" for info in sold.values())
            + ". Please ask an employee to re-tag the item."
        )
    if unknown:
        problems.append("Unknown RFID tag(s): " + ", ".join(unknown) + ". Please ask an employee.")

    if not known:
        return jsonify(success=False, message=" ".join(problems)), 404

    # Bound session size because Flask stores it in a signed cookie.
    if len(seen | set(known)) > 40:
        return jsonify(
            success=False,
            message="RFID limit reached. Reset the cart to start a new session.",
        ), 400

    cart = get_cart()

    # Validate the entire batch before saving any changes.
    for epc in known:
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
    session["rfid_seen"] = sorted(seen | set(known))
    active = session.get("rfid_cart_tags", {})
    active.update({epc: products[epc]["id"] for epc in known})
    session["rfid_cart_tags"] = active

    message = f"{len(known)} RFID item(s) added to your cart."
    if problems:
        message += " Ignored: " + " ".join(problems)
    return cart_response(message)


@cart_api.post("/api/cart/rfid")
def scan_rfid():
    """Add EPCs sent as JSON: {"epcs": ["E280...", ...]} (for testing)."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(
            success=False,
            message="Send RFID codes as JSON.",
        ), 400

    epcs = data.get("epcs")
    if not isinstance(epcs, list) or not epcs:
        return jsonify(
            success=False,
            message="Send between 1 and 100 EPC readings.",
        ), 400

    return add_epcs_to_cart(epcs)


@cart_api.post("/api/cart/rfid/scan")
def scan_rfid_reader():
    """Read every tag on the CF600 at once and add them to the cart."""
    try:
        epcs = rfid_reader.read_tags()
    except rfid_reader.RFIDError as error:
        return jsonify(success=False, message=str(error)), 503

    data = request.get_json(silent=True) or {}
    return add_epcs_to_cart(epcs, manual=data.get("manual") is True)


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

    # Keep scan history, but remove these tags from the active cart.
    session["rfid_cart_tags"] = {epc: pid for epc, pid in session.get("rfid_cart_tags", {}).items() if pid != product_id}
    # Keep RFID history so repeated readings do not restore removed items.
    return cart_response("Item removed from your cart.")


@cart_api.delete("/api/cart")
def reset_cart():
    session.pop("checkout_key", None)
    session.pop("shopping_cart", None)
    session.pop("rfid_cart_tags", None)
    session.pop("rfid_seen", None)
    session.pop("rfid_unknown", None)

    return cart_response("Your cart has been reset.")
