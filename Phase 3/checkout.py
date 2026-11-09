"""Connect the shopping cart to payment simulation and receipts."""

from flask import Blueprint, jsonify, request, session

import db
import receipts
from cart import build_cart, get_cart
from notifications import notify_error

checkout_api = Blueprint("checkout_api", __name__)


@checkout_api.post("/api/checkout")
def complete_checkout():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(
            success=False,
            message="Send checkout details as JSON.",
        ), 400

    payment_method = data.get("payment_method", "card")

    if payment_method not in ("card", "cash", "tap"):
        return jsonify(
            success=False,
            message="Choose card, cash, or tap.",
        ), 400

    membership_number = data.get("membership_number", "")

    if not isinstance(membership_number, str):
        return jsonify(
            success=False,
            message="Membership number must be text.",
        ), 400

    membership_number = membership_number.strip()

    language = data.get("language", "en")

    if language not in ("en", "fr"):
        return jsonify(
            success=False,
            message="Choose English or French.",
        ), 400

    cart = get_cart()

    if not cart:
        return jsonify(
            success=False,
            message="Your cart is empty.",
        ), 400

    # A blank membership number means guest checkout.
    customer_id = None

    if membership_number:
        customer = db.find_customer_by_membership(membership_number)

        if customer is None:
            return jsonify(
                success=False,
                message="Membership not found. Check the number or leave it blank for guest checkout.",
            ), 404

        customer_id = customer["id"]
        language = customer["language"]

    # Only send IDs and quantities. Prices come from the database.
    purchase_items = [
        {
            "product_id": int(product_id),
            "quantity": quantity,
        }
        for product_id, quantity in cart.items()
    ]

    try:
        result = receipts.complete_checkout(
            purchase_items,
            customer_id=customer_id,
            payment_method=payment_method,
            lang=language,
        )
    except db.DatabaseError as error:
        # Validation failed: leave the cart and RFID history intact.
        return jsonify(
            notify_error(str(error), language, save=False)
        ), 400

    # Clear shopping state only after checkout completes.
    # Keep customer login information in the session.
    session.pop("shopping_cart", None)
    session.pop("rfid_seen", None)
    session.pop("rfid_unknown", None)

    return jsonify({
        "success": True,
        "message": "Checkout completed successfully.",
        "cart": build_cart({}),
        "purchase_id": result["purchase_id"],
        "receipt": result["receipt"],
        "receipt_html": result["receipt_html"],
        "notifications": result["notifications"],
    })