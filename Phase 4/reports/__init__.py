"""Authenticated Phase 4 pages sharing the store application's session."""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, session, url_for
import db
from . import inventory, sales, customers, purchases, dashboard, exports
from .common import Period, snapshot

ROOT = Path(__file__).resolve().parent.parent
report_pages = Blueprint("reports", __name__, url_prefix="/reports",
                         template_folder=str(ROOT / "templates"),
                         static_folder=str(ROOT / "static"), static_url_path="/assets")


@report_pages.before_request
def authorize():
    if request.endpoint == "reports.static":
        return
    customer = db.get_customer(session.get("customer_id")) if session.get("customer_id") else None
    if not customer:
        if request.endpoint == "reports.index":
            return redirect(url_for("home"))
        abort(401, "Log in on the account page to view reports.")
    # Only "My purchases" is for customers; every other report page is administrator-only.
    if request.endpoint not in ("reports.index", "reports.purchase_report") and not customer.get("is_admin"):
        abort(403, "Administrator access required.")


@report_pages.after_request
def private_response(response):
    if request.endpoint != "reports.static":
        response.headers["Cache-Control"] = "private, no-store"
    return response


@report_pages.app_context_processor
def report_context():
    return {"report_customer": db.get_customer(session.get("customer_id")) if session.get("customer_id") else None}


@report_pages.app_template_filter("report_time")
def report_time(value):
    if not value:
        return ""
    return datetime.fromisoformat(str(value)).replace(tzinfo=timezone.utc).astimezone(
        ZoneInfo(current_app.config["REPORT_TIMEZONE"])).strftime("%Y-%m-%d %H:%M")


@report_pages.errorhandler(ValueError)
def invalid_filter(error):
    return render_template("reports/error.html", message=str(error)), 400


@report_pages.get("/")
def index():
    customer = db.get_customer(session["customer_id"])
    if customer.get("is_admin"):
        return render_template("reports/shell.html", title="Admin dashboard")
    return redirect(url_for("reports.purchase_report"))


@report_pages.get("/notifications")
def notifications_page():
    return render_template("reports/notifications.html", title="Notifications", active="notifications",
                           items=db.get_notifications(100), no_refresh=True)


@report_pages.get("/dashboard")
def dashboard_page():
    return render_template("reports/dashboard.html", title="Dashboard", active="dashboard", no_refresh=True)


@report_pages.get("/api/dashboard")
def dashboard_data():
    with snapshot() as conn:
        return jsonify(dashboard.generate(conn, current_app))


@report_pages.get("/inventory")
def inventory_report():
    category = request.args.get("category", "").strip()
    with snapshot() as conn:
        data = inventory.generate(conn, category)
    fmt = request.args.get("format")
    if fmt in exports.FORMATS:
        return exports.inventory_export(fmt, data, lambda v: report_time(v) if v else "Never")
    return render_template("reports/inventory.html", data=data, category=category, title="Inventory report", active="inventory",
                           saved=request.args.get("saved", ""), error=request.args.get("error", ""))


@report_pages.post("/inventory/limits")
def save_low_stock_limit():
    category = request.form.get("category", "")
    try:
        value = db.set_category_threshold(category, request.form.get("low_stock", ""))
    except db.DatabaseError as error:
        return redirect(url_for("reports.inventory_report", error=str(error)))
    return redirect(url_for("reports.inventory_report", saved=f"{category}: low stock is now below {value} units."))


def filtered_report(kind, title, active):
    period = Period()
    with snapshot() as conn:
        if kind == "sales":
            try:
                limit = int(request.args.get("limit", "5"))
            except ValueError:
                raise ValueError("Choose a valid ranking size.")
            if limit < 1 or limit > 50:
                raise ValueError("Choose between 1 and 50 ranked products.")
            data = sales.generate(conn, period, limit)
        elif kind == "customers":
            limit = None
            data = customers.generate(conn, period)
        else:
            limit = None
            raw_id = request.args.get("product_id", "")
            try:
                product_id = int(raw_id) if raw_id else None
            except ValueError:
                raise ValueError("Choose a valid product.")
            data = purchases.generate(conn, period, session["customer_id"], request.args.get("q", "").strip(), product_id)
    fmt = request.args.get("format")
    if fmt in exports.FORMATS:
        if kind == "sales":
            return exports.sales_export(fmt, data, period, request.args.get("table", "products"))
        if kind == "customers":
            return exports.customers_export(fmt, data, period)
        return exports.purchases_export(fmt, data, report_time, period)
    return render_template(f"reports/{kind}.html", data=data, period=period, limit=limit,
                           title=title, active=active, timezone=current_app.config["REPORT_TIMEZONE"])


@report_pages.get("/sales")
def sales_report():
    return filtered_report("sales", "Sales report", "sales")


@report_pages.get("/customers")
def customer_report():
    return filtered_report("customers", "Customer activity", "customers")


@report_pages.get("/purchases")
def purchase_report():
    return filtered_report("purchases", "My purchase reports", "purchases")
