
"""Smart Store Phase 3: smart self-checkout.

Pages
  /            customer accounts (register, login, points, purchase history)  - EN/FR
  /inventory   admin: products, stock receptions, inventory dashboard
  /cart        self-checkout: RFID + barcode scanning, payment, receipt

Run on the Raspberry Pi (the CF600 RFID reader is plugged into it):
    python app.py      ->  http://<pi-ip>:5002
"""

# Read configuration values such as the Flask secret key from the environment.
import os
# Generate a random secret key if one is not configured.
import secrets
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    abort,
    flash,
    jsonify,
    session,
)

load_dotenv()

import db
import rfid_reader
from notifications import notify, notify_error
from cart import cart_api
from checkout import checkout_api


def create_app():
    """Create the Flask app and register all Smart Store features."""
    app = Flask(__name__)

    # The secret key signs session cookies, including the customer login session.
    app.config["SECRET_KEY"] = (
        os.environ.get("FLASK_SECRET_KEY")
        or os.environ.get("SECRET_KEY")
        or secrets.token_hex(32)
    )

    # Create database tables if needed.
    db.init_db()

    # Display stored UTC dates in the computer's local time.
    @app.template_filter("local_time")
    def local_time(value):
        """The database stores UTC; show times in the computer's local time."""
        if not value:
            return ""
        try:
            utc = datetime.fromisoformat(str(value)).replace(tzinfo=timezone.utc)
            return utc.astimezone().strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return value

    # Register the shopping cart and checkout routes from separate modules.
    app.register_blueprint(cart_api)
    app.register_blueprint(checkout_api)

    # ---------------------------------------------------------
    # Pages
    # ---------------------------------------------------------

    @app.get("/")
    @app.get("/account")
    def home():
        return render_template("account.html")

    @app.get("/inventory")
    def inventory():
        return render_template(
            "inventory.html",
            products=db.get_inventory(),
        )

    @app.get("/cart")
    def shopping_cart():
        return render_template("cart.html")

    # ---------------------------------------------------------
    # Product management
    # ---------------------------------------------------------

    @app.route("/products/add", methods=["GET", "POST"])
    def add_product():
        error = None

        if request.method == "POST":
            try:
                name = request.form.get("name", "").strip()

                db.add_product(
                    name=name,
                    category=request.form.get("category", "").strip(),
                    price=request.form.get("price", ""),
                    upc=request.form.get("upc", "").strip(),
                    epc=request.form.get("epc", "").strip(),
                    producer=request.form.get("producer", "").strip(),
                )

                flash(notify("product_added", name=name)["message"], "success")
                return redirect(url_for("inventory"))

            except db.DatabaseError as exc:
                error = notify_error(str(exc))["message"]

        return render_template(
            "add_product.html",
            error=error,
            values=request.form,
        )

    @app.route(
        "/products/<int:product_id>/edit",
        methods=["GET", "POST"],
    )
    def edit_product(product_id):
        product = db.get_product(product_id)

        if product is None:
            abort(404)

        error = None
        values = product

        if request.method == "POST":
            values = request.form

            try:
                name = request.form.get("name", "").strip()

                db.update_product(
                    product_id=product_id,
                    name=name,
                    category=request.form.get("category", "").strip(),
                    price=request.form.get("price", ""),
                    upc=request.form.get("upc", "").strip(),
                    epc=request.form.get("epc", "").strip(),
                    producer=request.form.get("producer", "").strip(),
                )

                flash(notify("product_updated", name=name)["message"], "success")
                return redirect(url_for("inventory"))

            except db.DatabaseError as exc:
                error = notify_error(str(exc))["message"]

        return render_template(
            "edit_product.html",
            product=product,
            values=values,
            error=error,
        )

    @app.post("/products/<int:product_id>/delete")
    def delete_product(product_id):
        product = db.get_product(product_id)

        if product is None:
            abort(404)

        try:
            db.delete_product(product_id)

            flash(notify("product_deleted", name=product["name"])["message"], "success")

        except db.DatabaseError as exc:
            flash(notify_error(str(exc))["message"], "error")

        return redirect(url_for("inventory"))

    # ---------------------------------------------------------
    # Inventory
    # ---------------------------------------------------------

    @app.route("/inventory/receive", methods=["GET", "POST"])
    def receive_stock():
        products = db.get_inventory()
        error = None

        values = {
            "product_id": "",
            "quantity": "",
            "received_at": datetime.now().strftime("%Y-%m-%dT%H:%M"),
            "note": "",
        }

        if request.method == "POST":
            values = request.form

            try:
                try:
                    product_id = int(
                        request.form.get("product_id", "")
                    )
                except ValueError:
                    raise db.DatabaseError("Select a valid product.")

                product = db.get_product(product_id)

                if product is None:
                    raise db.DatabaseError("Product not found.")

                try:
                    quantity = int(
                        request.form.get("quantity", "")
                    )
                except ValueError:
                    raise db.DatabaseError(
                        "Quantity must be a whole number."
                    )

                if quantity <= 0:
                    raise db.DatabaseError(
                        "Quantity must be greater than zero."
                    )

                received_at = request.form.get(
                    "received_at", ""
                ).strip()

                try:
                    received_date = datetime.strptime(
                        received_at,
                        "%Y-%m-%dT%H:%M",
                    )
                except ValueError:
                    raise db.DatabaseError(
                        "Enter a valid reception date and time."
                    )

                db.receive_stock(
                    product_id=product_id,
                    quantity=quantity,
                    note=request.form.get("note", "").strip() or None,
                    # Form time is local; the database stores UTC.
                    received_at=received_date.astimezone(timezone.utc).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                )

                in_stock = db.get_product(product_id)["in_stock"]
                flash(
                    notify(
                        "stock_received",
                        quantity=quantity,
                        name=product["name"],
                        in_stock=in_stock,
                    )["message"],
                    "success",
                )
                return redirect(url_for("inventory"))

            except db.DatabaseError as exc:
                error = notify_error(str(exc))["message"]

        return render_template(
            "receive_stock.html",
            products=products,
            values=values,
            error=error,
        )

    @app.get("/inventory/receptions")
    def reception_history():
        selected_id = request.args.get("product_id", "").strip()
        product_id = None

        if selected_id:
            try:
                product_id = int(selected_id)
            except ValueError:
                abort(400)

        return render_template(
            "reception_history.html",
            receptions=db.get_receptions(product_id),
            products=db.get_inventory(),
            selected_id=selected_id,
        )

    # ---------------------------------------------------------
    # RFID reader (admin: read a tag's EPC into the product form)
    # ---------------------------------------------------------

    @app.get("/api/rfid/read")
    def read_rfid_tag():
        try:
            epcs = rfid_reader.read_tags()
        except rfid_reader.RFIDError as error:
            return jsonify(success=False, message=str(error)), 503

        if not epcs:
            return jsonify(
                success=False,
                message="No RFID tag detected. Hold the tag on the reader and try again.",
            ), 404

        if len(epcs) > 1:
            return jsonify(
                success=False,
                message=f"{len(epcs)} tags detected. Put only one tag on the reader.",
                epcs=epcs,
            ), 409

        existing = db.find_by_epc(epcs[0])
        return jsonify(
            success=True,
            epc=epcs[0],
            message=(
                f"Tag {epcs[0]} read."
                if existing is None
                else f'Tag {epcs[0]} read. It already belongs to "{existing["name"]}".'
            ),
            in_use_by=existing["name"] if existing else None,
        )

    @app.get("/api/notifications")
    def notifications_log():
        return jsonify(db.get_notifications(20))

    # ---------------------------------------------------------
    # Customer accounts
    # ---------------------------------------------------------

    @app.post("/api/account/register")
    def register():
        data = request.get_json(silent=True) or {}

        try:
            customer = db.create_customer(
                name=data.get("name", ""),
                email=data.get("email", ""),
                password=data.get("password", ""),
                phone=data.get("phone", ""),
                language=data.get("language", "en"),
            )

            # Keep the shopping cart; only switch the logged-in customer.
            session["customer_id"] = customer["id"]

            return jsonify({
                **notify(
                    "account_created",
                    data.get("language", "en"),
                    membership_number=customer["membership_number"],
                ),
                "membership_number": customer["membership_number"],
            }), 201

        except db.DatabaseError as error:
            return jsonify(notify_error(str(error))), 400

    @app.post("/api/account/login")
    def login():
        data = request.get_json(silent=True) or {}

        customer = db.login_customer(
            data.get("email", ""),
            data.get("password", ""),
        )

        if not customer:
            return jsonify(notify("login_failed")), 401

        # Keep the shopping cart; only switch the logged-in customer.
        session["customer_id"] = customer["id"]

        return jsonify(notify(
            "login_success",
            customer["language"],
            name=customer["name"],
        ))

    @app.get("/api/account/me")
    def my_account():
        customer_id = session.get("customer_id")

        if not customer_id:
            return jsonify(error="Please log in."), 401

        customer = db.get_customer(customer_id)

        if not customer:
            session.pop("customer_id", None)
            return jsonify(error="Account not found."), 404

        return jsonify(customer)

    @app.get("/api/account/history")
    def history():
        customer_id = session.get("customer_id")

        if not customer_id:
            return jsonify(error="Please log in."), 401

        return jsonify(db.get_purchase_history(customer_id))

    @app.get("/api/account/receipt/<int:purchase_id>")
    def view_receipt(purchase_id):
        customer_id = session.get("customer_id")

        if not customer_id:
            return jsonify(error="Please log in."), 401

        receipt = db.get_purchase(purchase_id)

        if not receipt or receipt["customer_id"] != customer_id:
            return jsonify(error="Receipt not found."), 404

        return jsonify(receipt)

    @app.post("/api/account/logout")
    def logout():
        session.pop("customer_id", None)
        return jsonify(notify("logged_out"))

    return app


if __name__ == "__main__":
    # 0.0.0.0 = reachable from other devices on the same network (laptop/phone).
    # Use HOST=127.0.0.1 in .env to allow only this computer's browser.
    create_app().run(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "5002")),
        debug=False,
    )
