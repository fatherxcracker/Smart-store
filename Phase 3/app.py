
"""
This is the main Flask application. It connects the website to the backend and database
Main features
- Customer accounts and login
- Membership numbers and loyalty points
- Purchase history and receipts
- Inventory and product management
- RFID scanning
- Shopping cart and checkout
"""

# Reads settings from the computer
import os
# Creates a random secret key when needed
import secrets
# Works with dates and time zones
from datetime import datetime, timezone
# Loads settings from the .env file
from dotenv import load_dotenv
# Flask tools used to create the website
from flask import (
    Flask, # Creates the Flask application
    render_template, # Opens HTML pages
    request, # Reads information sent by the browser
    redirect, # Sends the user to another page
    url_for, # Creates URLs for Flask routes
    abort, # Returns errors such as 404
    flash, # Shows temporary notifications
    jsonify, # Converts Python data into JSON
    session, # Remembers the logged-in customer
)

# Load settings from the .env file
load_dotenv()

# Database functions for customers and products
import db
# Functions for reading RFID tags
import rfid_reader
# Functions for success and error messages
from notifications import notify, notify_error
# Shopping cart routes
from cart import cart_api
# Checkout routes
from checkout import checkout_api

# Create flask app

def create_app():

    # Create the Flask application
    app = Flask(__name__)

    # Secret key protects session cookies
    # Sessions remember which customer is logged in
    app.config["SECRET_KEY"] = (
        os.environ.get("FLASK_SECRET_KEY")
        or os.environ.get("SECRET_KEY")
        or secrets.token_hex(32)
    )

    # Create database tables if needed
    db.init_db()

    @app.before_request
    def protect_inventory_management():
        protected = {"add_product", "edit_product", "delete_product", "receive_stock", "reception_history", "manage_product_tags"}
        if request.endpoint in protected:
            customer = db.get_customer(session.get("customer_id")) if session.get("customer_id") else None
            if not customer or not customer.get("is_admin"):
                abort(403, "Administrator access required.")

    # Converts stored UTC dates into local time
    @app.template_filter("local_time")
    def local_time(value):

        # Return empty text if no date exists
        if not value:
            return ""

        try:
            # Read the date from the database
            utc = datetime.fromisoformat(str(value)).replace(
                tzinfo=timezone.utc
            )

            # Display the date in local time
            return utc.astimezone().strftime("%Y-%m-%d %H:%M")

        except ValueError:
            # Return original value if conversion fails
            return value

    # Connect the shopping cart to Flask
    app.register_blueprint(cart_api)

    # Connect checkout to Flask
    app.register_blueprint(checkout_api)


    # Website pages

    # get opens a page or gets info.
    # Opens the customer account website
    @app.get("/")
    @app.get("/account")
    def home():

        # Load account.html
        return render_template("account.html")

    # Opens the inventory page
    @app.get("/inventory")
    def inventory():

        # Get products from the database
        customer = db.get_customer(session.get("customer_id")) if session.get("customer_id") else None
        return render_template("inventory.html", products=db.get_inventory(), is_admin=bool(customer and customer.get("is_admin")))

    # Opens the shopping cart page
    @app.get("/cart")
    def shopping_cart():

        return render_template("cart.html")


    # Product management

    # Handles adding, editing and deleting products
    # get show a form
    # post submits form information

    # Add product

    @app.route("/products/add", methods=["GET", "POST"])
    def add_product():

        # Start with no error
        error = None

        # Check if the form was submitted
        if request.method == "POST":

            try:
                # Read the product name
                # strip removes extra spaces
                name = request.form.get("name", "").strip()

                # Save the product in the database
                # UPC is the barcode identifier
                # EPC is the RFID identifier
                db.add_product(
                    name=name,
                    category=request.form.get("category", "").strip(),
                    price=request.form.get("price", ""),
                    upc=request.form.get("upc", "").strip(),
                    epc=None,
                    producer=request.form.get("producer", "").strip(),
                )

                # Show success notification
                flash(
                    notify("product_added", name=name)["message"],
                    "success",
                )

                # Return to inventory
                return redirect(url_for("inventory"))

            except db.DatabaseError as exc:

                # Show error if adding fails
                error = notify_error(str(exc))["message"]

        # Display the add product form
        return render_template(
            "add_product.html",
            error=error,
            values=request.form,
        )


    # Edit product

    # product_id identifies which product to edit
    @app.route(
        "/products/<int:product_id>/edit",
        methods=["GET", "POST"],
    )
    def edit_product(product_id):

        # Find the selected product
        product = db.get_product(product_id)

        # Return 404 if product does not exist
        if product is None:
            abort(404)

        error = None

        # Show product values
        values = product

        # Check if updated form was submitted
        if request.method == "POST":

            values = request.form

            try:
                # Read updated product name
                name = request.form.get("name", "").strip()

                # Update product in the database
                db.update_product(
                    product_id=product_id,
                    name=name,
                    category=request.form.get("category", "").strip(),
                    price=request.form.get("price", ""),
                    upc=request.form.get("upc", "").strip(),
                    epc=product.get("epc"),
                    producer=request.form.get("producer", "").strip(),
                )

                # Show success notification
                flash(
                    notify("product_updated", name=name)["message"],
                    "success",
                )

                return redirect(url_for("inventory"))

            except db.DatabaseError as exc:

                # Show error if update fails
                error = notify_error(str(exc))["message"]

        # Display the edit form
        return render_template(
            "edit_product.html",
            product=product,
            values=values,
            error=error,
        )


    # Delete product

    @app.post("/products/<int:product_id>/delete")
    def delete_product(product_id):

        # Find the product
        product = db.get_product(product_id)

        # Return 404 if not found
        if product is None:
            abort(404)

        try:
            # Delete the product through the database
            db.delete_product(product_id)

            # Show success message
            flash(
                notify(
                    "product_deleted",
                    name=product["name"],
                )["message"],
                "success",
            )

        except db.DatabaseError as exc:

            # Show error if deletion fails
            flash(notify_error(str(exc))["message"], "error")

        return redirect(url_for("inventory"))


    @app.route("/products/<int:product_id>/tags", methods=["GET", "POST"])
    def manage_product_tags(product_id):
        product = db.get_product(product_id)
        if not product:
            abort(404)
        error = None
        if request.method == "POST":
            try:
                db.register_product_tag(product_id, request.form.get("epc", ""))
                flash("RFID tag assigned to this item.", "success")
                return redirect(url_for("manage_product_tags", product_id=product_id))
            except db.DatabaseError as exc:
                error = str(exc)
        return render_template("product_tags.html", product=product, tags=db.get_product_tags(product_id), error=error)

    # Inventory

    # takes care of getting stock and seeing stock history


    # Receive stock

    @app.route("/inventory/receive", methods=["GET", "POST"])
    def receive_stock():

        # Get products for the dropdown
        products = db.get_inventory()

        error = None

        # Default form values
        values = {
            "product_id": "",
            "quantity": "",
            "received_at": datetime.now().strftime("%Y-%m-%dT%H:%M"),
            "note": "",
        }

        if request.method == "POST":

            # Get submitted form values
            values = request.form

            try:
                # Convert product ID into an integer
                try:
                    product_id = int(
                        request.form.get("product_id", "")
                    )

                except ValueError:
                    raise db.DatabaseError("Select a valid product.")

                # Find selected product
                product = db.get_product(product_id)

                if product is None:
                    raise db.DatabaseError("Product not found.")

                # Convert quantity into an integer
                try:
                    quantity = int(
                        request.form.get("quantity", "")
                    )

                except ValueError:
                    raise db.DatabaseError(
                        "Quantity must be a whole number."
                    )

                # Quantity must be positive
                if quantity <= 0:
                    raise db.DatabaseError(
                        "Quantity must be greater than zero."
                    )

                # Read reception date
                received_at = request.form.get(
                    "received_at", ""
                ).strip()

                try:
                    # Convert date text into a datetime object
                    received_date = datetime.strptime(
                        received_at,
                        "%Y-%m-%dT%H:%M",
                    )

                except ValueError:
                    raise db.DatabaseError(
                        "Enter a valid reception date and time."
                    )

                # Save stock reception
                # Convert local time to UTC
                db.receive_stock(
                    product_id=product_id,
                    quantity=quantity,
                    note=request.form.get("note", "").strip() or None,
                    epcs=[line.strip() for line in request.form.get("epcs", "").splitlines() if line.strip()],
                    received_at=received_date.astimezone(
                        timezone.utc
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                )

                # Get updated stock quantity
                in_stock = db.get_product(product_id)["in_stock"]

                # Show success message
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

                # Show error if receiving stock fails
                error = notify_error(str(exc))["message"]

        # Display receive stock form
        return render_template(
            "receive_stock.html",
            products=products,
            values=values,
            error=error,
        )


    # Reception history

    @app.get("/inventory/receptions")
    def reception_history():

        # Read optional product ID from the URL
        selected_id = request.args.get("product_id", "").strip()

        # None means show all products
        product_id = None

        if selected_id:
            try:
                product_id = int(selected_id)

            except ValueError:
                # Invalid product ID returns HTTP 400
                abort(400)

        # Display reception history
        return render_template(
            "reception_history.html",
            receptions=db.get_receptions(product_id),
            products=db.get_inventory(),
            selected_id=selected_id,
        )


    # RFID reader

    # Reads RFID tags for inventory products

    @app.get("/api/rfid/read")
    def read_rfid_tag():

        try:
            # Scan RFID tags
            epcs = rfid_reader.read_tags()

        except rfid_reader.RFIDError as error:

            # Reader error returns HTTP 503
            return jsonify(
                success=False,
                message=str(error),
            ), 503

        # No tag found
        if not epcs:
            return jsonify(
                success=False,
                message="No RFID tag detected. Hold the tag on the reader and try again.",
            ), 404

        # More than one tag found
        if len(epcs) > 1:
            return jsonify(
                success=False,
                message=f"{len(epcs)} tags detected. Put only one tag on the reader.",
                epcs=epcs,
            ), 409

        # Check if tag already belongs to a product
        existing = db.find_by_epc(epcs[0])

        # Return scanned tag information
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


    # Notifications

    # Get the 20 latest notifications
    @app.get("/api/notifications")
    def notifications_log():

        return jsonify(db.get_notifications(20))

    # Customer account system

    # manages customer accounts
    # handles registration, login, membership information, loyalty points, purchase history, receipts and logout
    # JavaScript sends requests to these Flask routes
    # Flask communicates with db.py to get or save information

    # Register customer

    @app.post("/api/account/register")
    def register():

        # Read JSON from the registration form
        data = request.get_json(silent=True) or {}

        try:
            # Create customer in the database
            # db.py validates the information
            # It also generates a membership number
            customer = db.create_customer(
                name=data.get("name", ""),
                email=data.get("email", ""),
                password=data.get("password", ""),
                phone=data.get("phone", ""),
                language=data.get("language", "en"),
            )

            # Save customer ID in the session
            # This automatically logs in the new customer
            # The shopping cart stays in the session
            session["customer_id"] = customer["id"]

            # Return success message and membership number
            # HTTP 201 means a new account was created
            return jsonify({
                **notify(
                    "account_created",
                    data.get("language", "en"),
                    membership_number=customer["membership_number"],
                ),
                "membership_number": customer["membership_number"],
            }), 201

        except db.DatabaseError as error:

            # Return HTTP 400 if registration fails
            return jsonify(notify_error(str(error))), 400


    # Login customer

    @app.post("/api/account/login")
    def login():

        # Read email and password from JavaScript
        data = request.get_json(silent=True) or {}

        # Check login details in the database
        customer = db.login_customer(data.get("email", ""), data.get("password", ""),)

        # HTTP 401 means incorrect login information
        if not customer:
            return jsonify(notify("login_failed")), 401

        # Remember the logged-in customer
        # Keep existing shopping cart
        session["customer_id"] = customer["id"]

        # Return success message in the customer's language
        return jsonify(notify(
            "login_success",
            customer["language"],
            name=customer["name"],
        ))


    # Customer info.

    @app.get("/api/account/me")
    def my_account():

        # Get customer ID from the session
        customer_id = session.get("customer_id")

        # User must be logged in
        if not customer_id:
            return jsonify(error="Please log in."), 401

        # Get customer information from the database
        customer = db.get_customer(customer_id)

        # Remove invalid login if account does not exist
        if not customer:
            session.pop("customer_id", None)
            return jsonify(error="Account not found."), 404

        # Send customer information to JavaScript
        # This includes name, email, membership and points
        return jsonify(customer)


    # Purchase history

    @app.get("/api/account/history")
    def history():

        # Get logged-in customer ID
        customer_id = session.get("customer_id")

        # Prevent users who are not logged in
        if not customer_id:
            return jsonify(error="Please log in."), 401

        # Return this customer's previous purchases
        return jsonify(db.get_purchase_history(customer_id))


    # View receipt

    @app.get("/api/account/receipt/<int:purchase_id>")
    def view_receipt(purchase_id):

        # Get logged-in customer ID
        customer_id = session.get("customer_id")

        # User must be logged in
        if not customer_id:
            return jsonify(error="Please log in."), 401

        # Find the requested receipt
        receipt = db.get_purchase(purchase_id)

        # Make sure receipt exists and belongs to this customer
        # This prevents customers from viewing other people's receipts
        if not receipt or receipt["customer_id"] != customer_id:
            return jsonify(error="Receipt not found."), 404

        # Return receipt information as JSON
        return jsonify(receipt)


    # Logout customer

    @app.post("/api/account/logout")
    def logout():

        # Remove only the customer login from the session
        # Keep the shopping cart information
        session.pop("customer_id", None)

        # Return logout notification
        return jsonify(notify("logged_out"))


    # Finish app setup

    # Return the configured Flask application
    return app


# Start server

# Run this section only when app.py is started directly
if __name__ == "__main__":

    # HOST controls which devices can connect
    # 0.0.0.0 allows connections from the local network
    # 127.0.0.1 allows connections only from this computer
    # PORT controls the server port
    # debug=False disables Flask debug mode
    create_app().run(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "5002")),
        debug=False,
    )
