"""Connect the shopping cart to payment simulation and receipts."""

from flask import Blueprint, current_app, jsonify, request, session

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

    if payment_method not in ("credit", "debit", "cash"):
        return jsonify(
            success=False,
            message="Choose Credit Card, Debit Card, or Cash.",
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

    checkout_key = session.get("checkout_key")
    if not checkout_key:
        return jsonify(success=False, message="Reload the cart before checking out."), 409

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
        if "language" not in data:
            language = customer["language"]

    # Only send IDs and quantities. Prices come from the database.
    # Recheck the chosen amount inside the purchase transaction; do not
    # silently reduce a confirmed discount when another checkout spends points.
    points_redeemed = session.get("points_to_redeem", 0) if session.get("points_owner") == session.get("customer_id") else 0
    if points_redeemed:
        owner = db.get_customer(session.get("customer_id")) if session.get("customer_id") else None
        if not owner or (customer_id is not None and customer_id != owner["id"]):
            return jsonify(success=False, message="You can only redeem points from your logged-in account."), 403
        customer_id = owner["id"]
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
            send_email=current_app.config.get("SEND_RECEIPT_EMAIL", True),
            epcs=list(session.get("rfid_cart_tags", {})),
            checkout_key=checkout_key,
            points_redeemed=points_redeemed,
        )
    except db.DatabaseError as error:
        # Validation failed: leave the cart and RFID history intact.
        return jsonify(
            notify_error(str(error), language, save=False)
        ), 400

    # Clear shopping state only after checkout completes.
    # Keep customer login information in the session.
    session.pop("shopping_cart", None)
    session.pop("rfid_cart_tags", None)
    session.pop("rfid_seen", None)
    session.pop("rfid_unknown", None)
    session.pop("checkout_key", None)
    session.pop("points_to_redeem", None)
    session.pop("points_owner", None)

    # Membership cards identify loyalty accounts; they do not authorize access
    # to private profile fields. Only the signed-in owner sees their details.
    receipt = result["receipt"]
    # Never fall back to HTML built from the full internal customer profile.
    receipt_html_by_language = {
        "en": "<p>Purchase saved. Receipt display is temporarily unavailable.</p>",
        "fr": "<p>Achat enregistré. L'affichage du reçu est temporairement indisponible.</p>",
    }
    if receipt:
        receipt = dict(receipt)
        customer = receipt.get("customer")
        if customer:
            fields = ("name", "membership_number", "points") if session.get("customer_id") == receipt["customer_id"] else ("membership_number",)
            receipt["customer"] = {key: customer[key] for key in fields}
        receipt.pop("checkout_key", None)
        receipt.pop("customer_id", None)
        for locale in receipt_html_by_language:
            try:
                receipt_html_by_language[locale] = receipts.build_receipt_html(receipt, locale)
            except Exception:
                # Keep the localized fallback without failing the saved purchase.
                pass

    # Email delivery notifications must not disclose the address at a kiosk.
    notes = []
    for note in result["notifications"]:
        if note.get("event") == "receipt_emailed":
            note = {"success": True, "level": "success", "message_en": "Receipt emailed.",
                    "message_fr": "Reçu envoyé par courriel."}
            note["message"] = note["message_" + language]
        notes.append(note)

    return jsonify({
        "success": True,
        "message": "Checkout completed successfully.",
        "cart": build_cart({}),
        "purchase_id": result["purchase_id"],
        "receipt": receipt,
        "receipt_html": receipt_html_by_language[language],
        "receipt_html_by_language": receipt_html_by_language,
        "notifications": notes,
    })
