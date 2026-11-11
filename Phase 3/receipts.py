"""
Smart Store - Phase 3
Receipts: build the receipt (product list, quantities, prices, total,
points earned, date/time) and email it to the customer automatically.

Typical use at the end of checkout (in a Flask route):

    import receipts
    result = receipts.complete_checkout(cart, customer_id=customer_id, lang=lang)
    return jsonify(result)

`result` contains the purchase id, the full receipt, the receipt HTML to
show on screen, and the list of notifications to display.

Email uses the same Gmail App Password setup as Phase 2 (see .env.example).
"""

import os
import smtplib
import logging
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from dotenv import load_dotenv

import db
from notifications import notify

load_dotenv()

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "")
SMTP_APP_PASSWORD = os.environ.get("SMTP_APP_PASSWORD", "")
STORE_NAME = os.environ.get("STORE_NAME", "Smart Store")
LOW_STOCK_LIMIT = int(os.environ.get("LOW_STOCK_LIMIT", "5"))

LABELS = {
    "en": {
        "title": "Receipt", "receipt_no": "Receipt #", "date": "Date", "member": "Member",
        "guest": "Guest", "item": "Item", "qty": "Qty", "price": "Price", "amount": "Amount",
        "subtotal": "Subtotal", "gst": "GST (5%)", "qst": "QST (9.975%)", "total": "Total",
        "payment": "Payment", "points_earned": "Points earned", "points_total": "Total points",
        "thanks": "Thank you for shopping with us!",
        "subject": "Your {store} receipt {number}",
    },
    "fr": {
        "title": "Reçu", "receipt_no": "Reçu no", "date": "Date", "member": "Membre",
        "guest": "Invité", "item": "Article", "qty": "Qté", "price": "Prix", "amount": "Montant",
        "subtotal": "Sous-total", "gst": "TPS (5 %)", "qst": "TVQ (9,975 %)", "total": "Total",
        "payment": "Paiement", "points_earned": "Points gagnés", "points_total": "Total des points",
        "thanks": "Merci de votre visite !",
        "subject": "Votre reçu {store} {number}",
    },
}


def _money(value, lang):
    return f"{value:,.2f} $".replace(",", " ").replace(".", ",") if lang == "fr" else f"${value:,.2f}"


def _date(created_at):
    # created_at is stored in UTC by SQLite; show it in local time
    try:
        utc = datetime.fromisoformat(created_at)
        local = utc.replace(tzinfo=timezone.utc).astimezone()
        return local.strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return str(created_at)


def _lang_for(receipt, lang):
    if lang in ("en", "fr"):
        return lang
    customer = receipt.get("customer")
    return customer["language"] if customer else "en"


# ---------------------------------------------------------------------------
# Building the receipt
# ---------------------------------------------------------------------------
def build_receipt_text(receipt, lang=None):
    """Plain-text receipt (used in the email and for printing/logging)."""
    lang = _lang_for(receipt, lang)
    L = LABELS[lang]
    customer = receipt.get("customer")
    lines = [
        f"{STORE_NAME} - {L['title']}",
        f"{L['receipt_no']}: {receipt['receipt_number']}",
        f"{L['date']}: {_date(receipt['created_at'])}",
        f"{L['member']}: {customer.get('name', L['member']) + ' (' + customer['membership_number'] + ')' if customer else L['guest']}",
        "-" * 44,
        f"{L['item']:<22}{L['qty']:>4}{L['price']:>9}{L['amount']:>9}",
    ]
    for item in receipt["items"]:
        lines.append(
            f"{item['product_name'][:22]:<22}{item['quantity']:>4}"
            f"{_money(item['unit_price'], lang):>9}{_money(item['line_total'], lang):>9}"
        )
    lines += [
        "-" * 44,
        f"{L['subtotal']:<30}{_money(receipt['subtotal'], lang):>14}",
        f"{L['gst']:<30}{_money(receipt['gst'], lang):>14}",
        f"{L['qst']:<30}{_money(receipt['qst'], lang):>14}",
        f"{L['total']:<30}{_money(receipt['total'], lang):>14}",
        f"{L['payment']:<30}{receipt['payment_method'].upper():>14}",
    ]
    if customer:
        lines += [
            f"{L['points_earned']:<30}{receipt['points_earned']:>14}",
        ]
        if "points" in customer:
            lines.append(f"{L['points_total']:<30}{customer['points']:>14}")
    lines += ["", L["thanks"]]
    return "\n".join(lines)


def build_receipt_html(receipt, lang=None):
    """HTML receipt (used in the email and shown on the checkout screen)."""
    lang = _lang_for(receipt, lang)
    L = LABELS[lang]
    customer = receipt.get("customer")
    member = (f"{escape(customer.get('name', L['member']))} ({escape(customer['membership_number'])})"
              if customer else L["guest"])

    rows = "".join(
        f"<tr><td style='padding:6px 0'>{escape(i['product_name'])}</td>"
        f"<td style='text-align:center'>{i['quantity']}</td>"
        f"<td style='text-align:right'>{_money(i['unit_price'], lang)}</td>"
        f"<td style='text-align:right'>{_money(i['line_total'], lang)}</td></tr>"
        for i in receipt["items"]
    )

    def total_row(label, value, bold=False):
        weight = "font-weight:bold;font-size:17px;" if bold else ""
        return (f"<tr><td colspan='3' style='padding:4px 0;{weight}'>{label}</td>"
                f"<td style='text-align:right;{weight}'>{value}</td></tr>")

    points_html = ""
    if customer:
        points_html = (
            f"<div style='margin-top:16px;padding:12px;background:#ecfdf5;border-radius:8px;color:#065f46'>"
            f"<b>{L['points_earned']}: +{receipt['points_earned']}</b><br>"
            + (f"{L['points_total']}: {customer['points']}" if "points" in customer else "")
            + "</div>"
        )

    return f"""<div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;color:#1e293b">
  <h2 style="margin:0;color:#0f766e">{escape(STORE_NAME)}</h2>
  <p style="margin:4px 0 16px;color:#64748b">{L['title']} {escape(receipt['receipt_number'])}</p>
  <p style="margin:2px 0">{L['date']}: {_date(receipt['created_at'])}</p>
  <p style="margin:2px 0 12px">{L['member']}: {member}</p>
  <table style="width:100%;border-collapse:collapse;font-size:14px">
    <tr style="border-bottom:1px solid #cbd5e1;text-align:left">
      <th style="padding:6px 0">{L['item']}</th><th>{L['qty']}</th>
      <th style="text-align:right">{L['price']}</th><th style="text-align:right">{L['amount']}</th>
    </tr>
    {rows}
    <tr><td colspan="4" style="border-top:1px solid #cbd5e1"></td></tr>
    {total_row(L['subtotal'], _money(receipt['subtotal'], lang))}
    {total_row(L['gst'], _money(receipt['gst'], lang))}
    {total_row(L['qst'], _money(receipt['qst'], lang))}
    {total_row(L['total'], _money(receipt['total'], lang), bold=True)}
    {total_row(L['payment'], escape(receipt['payment_method'].upper()))}
  </table>
  {points_html}
  <p style="margin-top:20px;color:#64748b">{L['thanks']}</p>
</div>"""


# ---------------------------------------------------------------------------
# Emailing the receipt
# ---------------------------------------------------------------------------
def send_receipt_email(purchase_id, lang=None):
    """Email the receipt to the customer if they have an email.
    Returns a notification dict, or None for guests (no email to send to)."""
    receipt = db.get_purchase(purchase_id)
    if not receipt or not receipt.get("customer") or not receipt["customer"].get("email"):
        return None

    lang = _lang_for(receipt, lang)
    to_email = receipt["customer"]["email"]

    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        print("[receipt] SMTP_EMAIL / SMTP_APP_PASSWORD not set in .env - receipt not emailed.")
        return notify("receipt_email_failed", lang)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = LABELS[lang]["subject"].format(store=STORE_NAME, number=receipt["receipt_number"])
    msg["From"] = f"{STORE_NAME} <{SMTP_EMAIL}>"
    msg["To"] = to_email
    msg.attach(MIMEText(build_receipt_text(receipt, lang), "plain", "utf-8"))
    msg.attach(MIMEText(build_receipt_html(receipt, lang), "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
            server.send_message(msg)
    except Exception as error:
        print(f"[receipt] Failed to email receipt {receipt['receipt_number']}: {error}")
        return notify("receipt_email_failed", lang)

    db.mark_email_sent(purchase_id)
    print(f"[receipt] Receipt {receipt['receipt_number']} emailed to {to_email}")
    return {**notify("receipt_emailed", lang, email=to_email), "event": "receipt_emailed"}


# ---------------------------------------------------------------------------
# One call for the whole end of checkout (steps 4-6 of the workflow)
# ---------------------------------------------------------------------------
def complete_checkout(cart, customer_id=None, payment_method="card", lang="en", send_email=True, epcs=None, checkout_key=None):
    """Payment simulation -> save purchase -> add points -> receipt -> email.

    cart = [{"product_id": 1, "quantity": 2}, ...]
    Raises db.DatabaseError (e.g. not enough stock) - wrap it with
    notifications.notify_error(str(error), lang) in the route.
    """
    purchase_id, created = db.create_purchase(
        cart, customer_id=customer_id, payment_method=payment_method, epcs=epcs,
        checkout_key=checkout_key, return_status=True,
    )
    # From here on the sale is committed. Notification/email/render failures
    # must never tell the customer that payment failed or invite another sale.
    receipt = None
    notes = []
    store_notes = []
    receipt_html = "<p>Purchase saved. Receipt display is temporarily unavailable.</p>"
    try:
        receipt = db.get_purchase(purchase_id)
        receipt_html = build_receipt_html(receipt, lang)
        if created:
            notes.append(notify("payment_approved", lang, total=receipt["total"]))
            if receipt["customer"]:
                notes.append(notify("checkout_completed", lang,
                                    receipt_number=receipt["receipt_number"], points=receipt["points_earned"]))
            else:
                notes.append(notify("checkout_completed_guest", lang, receipt_number=receipt["receipt_number"]))
            if send_email:
                email_note = send_receipt_email(purchase_id, lang)
                if email_note:
                    notes.append(email_note)
                    receipt = db.get_purchase(purchase_id)
            for item in receipt["items"]:
                product = db.get_product(item["product_id"])
                if product and product["in_stock"] <= LOW_STOCK_LIMIT:
                    store_notes.append(notify("low_stock", lang, name=product["name"], in_stock=product["in_stock"]))
    except Exception:
        logging.exception("Purchase %s saved; checkout follow-up failed", purchase_id)
        notes.append({
            "success": True, "level": "warning",
            "message": ("Purchase saved. Receipt or email services are temporarily unavailable. Do not pay again."
                        if lang == "en" else "Achat enregistré. Le reçu ou le courriel est temporairement indisponible. Ne payez pas à nouveau."),
        })

    return {
        "success": True,
        "purchase_id": purchase_id,
        "receipt": receipt,
        "receipt_html": receipt_html,
        "notifications": notes,          # show these to the customer
        "store_notifications": store_notes,  # show these on the admin dashboard
    }
