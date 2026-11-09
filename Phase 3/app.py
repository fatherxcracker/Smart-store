<<<<<<< HEAD
"""Smart Store Phase 3: smart self-checkout.

Pages
  /            customer accounts (register, login, points, purchase history)  - EN/FR
  /inventory   admin: products, stock receptions, inventory dashboard
  /cart        self-checkout: RFID + barcode scanning, payment, receipt

Run on the Raspberry Pi (the CF600 RFID reader is plugged into it):
    python app.py      ->  http://<pi-ip>:5002
=======
"""
phase3
This file is the main Flask application
It connects the website to the Python backend and database
The application has:
1. Customer registration and login
2. Customer accounts and loyalty points
3. Purchase history and receipts
4. Product management(add, edit, delete)
5. Inventory management
6. Shopping cart integration
Flask gets requests from the browser, processes them,communicates with the database, and returns a response
>>>>>>> 1c8b4b6 (Update Phase 3 customer account system and UI)
"""

# os lets read environment variables likee SECRET_KEY:
import os
# secrets generates random values for temporary Flask secret key:
import secrets
<<<<<<< HEAD
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
=======
# datetime works with dates and times like recording when inventory comes in:
from datetime import datetime

# Loads configuration variables from a .env file.
# This keeps sensitive settings outside the Python code.
from dotenv import load_dotenv

# Import Flask and the tools needed to build the website.
from flask import (
    Flask,           # Creates the Flask web application
    render_template, # Loads HTML pages from templates/
    request,         # Reads information sent by the browser
    redirect,        # Sends the user to another page
    url_for,         # Generates URLs using Flask route names
    abort,           # Stops a request with an HTTP error
    flash,           # Displays temporary success/error messages
    jsonify,         # Converts Python data into JSON responses
    session,         # Remembers which customer is logged in
)

# Read variables from .env before initializing the application.
load_dotenv()

# Import our database functions.
# db.py handles customers, products, inventory, and purchases.
import db

# Import functions for creating success/error notifications.
>>>>>>> 1c8b4b6 (Update Phase 3 customer account system and UI)
from notifications import notify, notify_error
from cart import cart_api
from checkout import checkout_api

<<<<<<< HEAD
def create_app():
    app = Flask(__name__)

=======
# Import the shopping cart API created in cart.py.
from cart import cart_api


# ============================================================
# 2. CREATE THE FLASK APPLICATION
# ============================================================

def create_app():
    """
    Creates and configures the Smart Store Flask application.

    This function is called an application factory.

    It creates the website, initializes the database,
    registers the shopping cart, and defines the routes.
    """

    # Create the Flask application.
    app = Flask(__name__)

    # SECRET_KEY is used to protect Flask session cookies.
    # Sessions let the application remember logged-in users.
    #
    # First, try FLASK_SECRET_KEY from the environment.
    # If unavailable, try SECRET_KEY.
    # Otherwise, generate a random key for local development.
    #
    # A permanent key should be configured for deployment.
>>>>>>> 1c8b4b6 (Update Phase 3 customer account system and UI)
    app.config["SECRET_KEY"] = (
        os.environ.get("FLASK_SECRET_KEY")
        or os.environ.get("SECRET_KEY")
        or secrets.token_hex(32)
    )

<<<<<<< HEAD
    db.init_db()

    @app.template_filter("local_time")
    def local_time(value):
        """The database stores UTC; show times in the Pi's local time."""
        if not value:
            return ""
        try:
            utc = datetime.fromisoformat(str(value)).replace(tzinfo=timezone.utc)
            return utc.astimezone().strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return value

    app.register_blueprint(cart_api)
    app.register_blueprint(checkout_api)
=======
    # Initialize the SQLite database.
    #
    # db.init_db() creates the required tables if needed.
    # It uses the database schema already defined by our team.
    db.init_db()

    # Connect the shopping cart routes to this Flask app.
    #
    # A Blueprint groups related routes in a separate file.
    # This allows cart.py to handle shopping cart functionality.
    app.register_blueprint(cart_api)
>>>>>>> 1c8b4b6 (Update Phase 3 customer account system and UI)

    # ---------------------------------------------------------
    # Pages
    # ---------------------------------------------------------

<<<<<<< HEAD
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
=======
    # ========================================================
    # 3. WEBSITE PAGES
    # ========================================================

    # @app.get means this route responds to HTTP GET requests.
    #
    # GET is used when the browser wants to retrieve information
    # or open a page.

    # Both "/" and "/account" open the customer account page.
    @app.get("/")
    @app.get("/account")
    def home():

        # Flask looks inside templates/ for account.html.
        # This page contains login, registration, and dashboard UI.
        return render_template("account.html")


    # Opens the inventory management page.
    @app.get("/inventory")
    def inventory():

        # db.get_inventory() retrieves products and stock levels.
        #
        # products= sends that information to inventory.html,
        # where it can be displayed in a table.
        return render_template(
            "inventory.html",
            products=db.get_inventory(),
        )


    # Opens the shopping cart page.
    @app.get("/cart")
    def shopping_cart():

        # The cart page displays products selected for checkout.
        return render_template("cart.html")


    # ========================================================
    # 4. PRODUCT MANAGEMENT
    # ========================================================

    # Product management allows administrators to:
    # - Add new products
    # - Edit existing products
    # - Delete products
    #
    # GET = display the form.
    # POST = submit information to the server.


    # --------------------------------------------------------
    # ADD A PRODUCT
    # --------------------------------------------------------

    @app.route("/products/add", methods=["GET", "POST"])
    def add_product():

        # Store an error message if something goes wrong.
        error = None

        # Check whether the user submitted the form.
        if request.method == "POST":

            try:
                # Read the product name from the HTML form.
                #
                # .get() retrieves a form field.
                # .strip() removes extra spaces.
                name = request.form.get("name", "").strip()

                # Call db.py to save the new product.
                #
                # Each product contains:
                # name, category, price, UPC, EPC, producer.
                #
                # UPC = barcode identifier.
                # EPC = RFID identifier.
                db.add_product(
                    name=name,
                    category=request.form.get("category", "").strip(),
                    price=request.form.get("price", ""),
                    upc=request.form.get("upc", "").strip(),
                    epc=request.form.get("epc", "").strip(),
                    producer=request.form.get("producer", "").strip(),
                )

                # flash() stores a temporary success notification.
                # The next HTML page can display this message.
                flash(
                    f'Product "{name}" added successfully.',
                    "success",
                )

                # Redirect the browser to the inventory page.
                return redirect(url_for("inventory"))

            # Catch errors raised by our database functions.
            # For example, duplicate UPC or invalid price.
            except db.DatabaseError as exc:
                error = str(exc)

        # For GET requests, display the empty product form.
        #
        # If POST failed, show the form again with the error
        # and the values the user previously entered.
        return render_template(
            "add_product.html",
            error=error,
            values=request.form,
        )


    # --------------------------------------------------------
    # EDIT A PRODUCT
    # --------------------------------------------------------

    # <int:product_id> is a dynamic URL parameter.
    #
    # Example: /products/3/edit
    # Flask converts 3 into an integer and passes it
    # to the function as product_id.
    @app.route(
        "/products/<int:product_id>/edit",
        methods=["GET", "POST"],
    )
    def edit_product(product_id):

        # Find the existing product in the database.
        product = db.get_product(product_id)

        # If the product doesn't exist, return HTTP 404.
        if product is None:
            abort(404)

        # Start with no error.
        error = None

        # Use the current product values to fill the edit form.
        values = product

        # If the user submits the edited product:
        if request.method == "POST":

            # Use the submitted values instead of the old values.
            values = request.form

            try:
                # Get the updated product name.
                name = request.form.get("name", "").strip()

                # Update the product in the database.
                db.update_product(
                    product_id=product_id,
                    name=name,
                    category=request.form.get("category", "").strip(),
                    price=request.form.get("price", ""),
                    upc=request.form.get("upc", "").strip(),
                    epc=request.form.get("epc", "").strip(),
                    producer=request.form.get("producer", "").strip(),
                )

                # Display a success notification.
                flash(
                    f'Product "{name}" updated successfully.',
                    "success",
                )

                # Return to the inventory page.
                return redirect(url_for("inventory"))

            # If validation fails, display the error.
            except db.DatabaseError as exc:
                error = str(exc)

        # Display the edit form.
        #
        # product = original product information
        # values = values currently shown in the form
        # error = validation error, if any
        return render_template(
            "edit_product.html",
            product=product,
            values=values,
            error=error,
        )


    # --------------------------------------------------------
    # DELETE A PRODUCT
    # --------------------------------------------------------

    # This route accepts POST requests only.
    # A product should not be deleted simply by opening a URL.
    @app.post("/products/<int:product_id>/delete")
    def delete_product(product_id):

        # Look up the product before deleting it.
        product = db.get_product(product_id)

        # Return 404 if the product does not exist.
        if product is None:
            abort(404)

        try:
            # Ask the database to delete the product.
            #
            # In db.py, deletion is a "soft delete".
            # This means the product is marked inactive.
            #
            # Old receipts can still reference that product.
            db.delete_product(product_id)

            # Display a success message.
            flash(
                f'Product "{product["name"]}" deleted successfully.',
                "success",
            )

        except db.DatabaseError as exc:

            # Display a failure notification.
            flash(str(exc), "error")

        # Return to the inventory dashboard.
        return redirect(url_for("inventory"))


    # ========================================================
    # 5. INVENTORY MANAGEMENT
    # ========================================================

    # Inventory management tracks how much stock arrives
    # and when it arrives.
    #
    # Receiving stock is different from creating a product.
    #
    # A product is defined once, but the store can receive
    # additional quantities of that product many times.


    # --------------------------------------------------------
    # RECEIVE NEW STOCK
    # --------------------------------------------------------

    @app.route("/inventory/receive", methods=["GET", "POST"])
    def receive_stock():

        # Retrieve the available products.
        # These are displayed in the product dropdown.
        products = db.get_inventory()

        # Store any validation error.
        error = None

        # Default values for the inventory reception form.
        values = {
            "product_id": "",
            "quantity": "",

            # Display the current date and time by default.
            # Example: 2026-11-09T12:30
            "received_at": datetime.now().strftime("%Y-%m-%dT%H:%M"),

            "note": "",
        }

        # Process the form after the user clicks Submit.
        if request.method == "POST":

            # Remember the submitted values.
            values = request.form

            try:
                # Read the selected product ID.
                #
                # Product IDs must be integers.
                try:
                    product_id = int(
                        request.form.get("product_id", "")
                    )

                except ValueError:
                    raise db.DatabaseError(
                        "Select a valid product."
                    )

                # Find the selected product.
                product = db.get_product(product_id)

                # Stop if the product doesn't exist.
                if product is None:
                    raise db.DatabaseError(
                        "Product not found."
                    )

                # Read the quantity received.
                #
                # int() converts the form value to an integer.
                try:
                    quantity = int(
                        request.form.get("quantity", "")
                    )

                except ValueError:
                    raise db.DatabaseError(
                        "Quantity must be a whole number."
                    )

                # Stock reception quantities must be positive.
                if quantity <= 0:
                    raise db.DatabaseError(
                        "Quantity must be greater than zero."
                    )

                # Read the reception date and time.
                received_at = request.form.get(
                    "received_at", ""
                ).strip()

                # Convert the HTML date/time string into
                # a Python datetime object.
                try:
                    received_date = datetime.strptime(
                        received_at,
                        "%Y-%m-%dT%H:%M",
                    )

                except ValueError:
                    raise db.DatabaseError(
                        "Enter a valid reception date and time."
                    )

                # Save the new stock reception in the database.
                #
                # This records:
                # - Which product was received
                # - How many units arrived
                # - Optional notes
                # - Reception date and time
                db.receive_stock(
                    product_id=product_id,
                    quantity=quantity,
                    note=request.form.get("note", "").strip() or None,
                    received_at=received_date.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                )

                # Show a success message.
                flash(
                    f'Received {quantity} units of "{product["name"]}".',
                    "success",
                )

                # Return to the inventory dashboard.
                return redirect(url_for("inventory"))

            # Display validation errors on the form.
            except db.DatabaseError as exc:
                error = str(exc)

        # Show the receive-stock form.
        return render_template(
            "receive_stock.html",
            products=products,
            values=values,
            error=error,
        )


    # --------------------------------------------------------
    # INVENTORY RECEPTION HISTORY
    # --------------------------------------------------------

    @app.get("/inventory/receptions")
    def reception_history():

        # Read an optional product_id from the URL.
        #
        # Example:
        # /inventory/receptions?product_id=2
        #
        # This filters the reception history to product 2.
        selected_id = request.args.get(
            "product_id", ""
        ).strip()

        # None means no product filter was selected.
        product_id = None

        if selected_id:
            try:
                # Convert the product ID into an integer.
                product_id = int(selected_id)

            except ValueError:
                # Return HTTP 400 if the ID is invalid.
                abort(400)

        # Display all receptions or filtered receptions.
        return render_template(
            "reception_history.html",
            receptions=db.get_receptions(product_id),
            products=db.get_inventory(),
            selected_id=selected_id,
        )


    # ========================================================
    # 6. CUSTOMER ACCOUNT SYSTEM - YOUR PART
    # ========================================================

    # This section manages customer accounts.
    #
    # It allows customers to:
    # - Register
    # - Log in
    # - View their membership number
    # - View loyalty points
    # - View purchase history
    # - View receipts
    # - Log out
    #
    # These routes return JSON instead of HTML.
    #
    # JavaScript in static/account.js calls these endpoints
    # using fetch().


    # --------------------------------------------------------
    # REGISTER A NEW CUSTOMER
    # --------------------------------------------------------

    @app.post("/api/account/register")
    def register():

        # Read the JSON sent from the registration form.
        #
        # silent=True prevents Flask from raising an error
        # automatically if the JSON is missing or invalid.
        #
        # or {} ensures data is a dictionary when parsing
        # returns None.
        data = request.get_json(silent=True) or {}

        try:
            # Create a new customer using db.py.
            #
            # The database function:
            # - Validates the customer information
            # - Hashes the password
            # - Generates a unique membership number
            # - Saves the account to SQLite
            customer = db.create_customer(
                name=data.get("name", ""),
                email=data.get("email", ""),
                password=data.get("password", ""),
                phone=data.get("phone", ""),
                language=data.get("language", "en"),
            )

            # Clear any previous login session.
            session.clear()

            # Remember the newly registered customer's ID.
            #
            # This automatically logs them in after registration.
            session["customer_id"] = customer["id"]

            # Return a JSON success response.
            #
            # notify("account_created") creates the message.
            #
            # membership_number is returned so the browser
            # can display the new customer's membership.
            #
            # HTTP 201 means a new resource was created.
            return jsonify({
                **notify(
                    "account_created",
                    data.get("language", "en"),
                    membership_number=customer["membership_number"],
                ),
                "membership_number": customer["membership_number"],
            }), 201

        # Catch errors such as duplicate emails,
        # missing information, or invalid passwords.
        except db.DatabaseError as error:

            # HTTP 400 means the request was invalid.
            return jsonify(
                notify_error(str(error))
            ), 400


    # --------------------------------------------------------
    # CUSTOMER LOGIN
    # --------------------------------------------------------

    @app.post("/api/account/login")
    def login():

        # Read the email and password from the login form.
        data = request.get_json(silent=True) or {}

        # Check the customer's credentials in the database.
        #
        # db.login_customer() checks the password hash.
        #
        # It returns customer information if successful.
        # It returns None if the credentials are incorrect.
        customer = db.login_customer(
            data.get("email", ""),
            data.get("password", ""),
        )

        # If login failed, return HTTP 401 Unauthorized.
        if not customer:
            return jsonify(
                notify("login_failed")
            ), 401

        # Remove any previous session information.
        session.clear()

        # Save the logged-in customer's ID in the session.
        #
        # Flask uses a signed session cookie so future
        # requests can identify the logged-in customer.
        session["customer_id"] = customer["id"]

        # Return a successful login notification.
        #
        # The message uses the customer's preferred language.
        return jsonify(
            notify(
                "login_success",
                customer["language"],
                name=customer["name"],
            )
        )
>>>>>>> 1c8b4b6 (Update Phase 3 customer account system and UI)

        if request.method == "POST":
            try:
                name = request.form.get("name", "").strip()

<<<<<<< HEAD
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
=======
    # --------------------------------------------------------
    # GET LOGGED-IN CUSTOMER INFORMATION
    # --------------------------------------------------------

    @app.get("/api/account/me")
    def my_account():

        # Get the logged-in customer ID from the session.
        customer_id = session.get("customer_id")

        # If there is no customer ID, the user isn't logged in.
        if not customer_id:

            # HTTP 401 = authentication required.
            return jsonify(
                error="Please log in."
            ), 401

        # Retrieve the customer's account information.
        customer = db.get_customer(customer_id)

        # The account might have been deleted or become invalid.
        if not customer:

            # Clear the invalid session.
            session.clear()

            # HTTP 404 = account not found.
            return jsonify(
                error="Account not found."
            ), 404

        # Return the customer's information as JSON.
        #
        # The database function excludes password_hash.
        #
        # JavaScript uses this response to display:
        # name, email, membership number, and points.
        return jsonify(customer)
>>>>>>> 1c8b4b6 (Update Phase 3 customer account system and UI)

        return render_template(
            "add_product.html",
            error=error,
            values=request.form,
        )

<<<<<<< HEAD
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
=======
    # --------------------------------------------------------
    # CUSTOMER PURCHASE HISTORY
    # --------------------------------------------------------

    @app.get("/api/account/history")
    def history():

        # Identify the logged-in customer.
        customer_id = session.get("customer_id")

        # Purchase history is private.
        # Customers must log in before viewing it.
        if not customer_id:
            return jsonify(
                error="Please log in."
            ), 401

        # Get only this customer's previous purchases.
        #
        # Each purchase includes information such as:
        # receipt number, total, points earned, and date.
        #
        # JavaScript displays the purchases in the
        # Purchase History page.
        return jsonify(
            db.get_purchase_history(customer_id)
        )
>>>>>>> 1c8b4b6 (Update Phase 3 customer account system and UI)

                db.update_product(
                    product_id=product_id,
                    name=name,
                    category=request.form.get("category", "").strip(),
                    price=request.form.get("price", ""),
                    upc=request.form.get("upc", "").strip(),
                    epc=request.form.get("epc", "").strip(),
                    producer=request.form.get("producer", "").strip(),
                )

<<<<<<< HEAD
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
=======
    # --------------------------------------------------------
    # VIEW AN INDIVIDUAL RECEIPT
    # --------------------------------------------------------

    # Example URL:
    # /api/account/receipt/5
    #
    # Flask converts the 5 into purchase_id=5.
    @app.get("/api/account/receipt/<int:purchase_id>")
    def view_receipt(purchase_id):

        # Get the currently logged-in customer.
        customer_id = session.get("customer_id")

        # The user must be logged in.
        if not customer_id:
            return jsonify(
                error="Please log in."
            ), 401

        # Retrieve the requested receipt from the database.
        receipt = db.get_purchase(purchase_id)

        # Check TWO things:
        #
        # 1. Does the receipt exist?
        # 2. Does it belong to the logged-in customer?
        #
        # This prevents customers from reading someone
        # else's purchase receipts by changing the URL.
        if not receipt or receipt["customer_id"] != customer_id:
            return jsonify(
                error="Receipt not found."
            ), 404

        # Return the complete receipt as JSON.
        #
        # This includes purchased items, quantities,
        # prices, totals, and loyalty points.
        return jsonify(receipt)
>>>>>>> 1c8b4b6 (Update Phase 3 customer account system and UI)


    # --------------------------------------------------------
    # CUSTOMER LOGOUT
    # --------------------------------------------------------

    @app.post("/api/account/logout")
    def logout():

        # Clear all session information.
        #
        # After this, the application no longer considers
        # the customer logged in.
        session.clear()

        # Return a logout notification to JavaScript.
        return jsonify(
            notify("logged_out")
        )


    # ========================================================
    # 7. FINISH CREATING THE APPLICATION
    # ========================================================

    # Return the configured Flask application.
    #
    # All routes have now been registered.
    return app


# ============================================================
# 8. START THE WEB SERVER
# ============================================================

# This section runs only when app.py is executed directly.
#
# Example:
# python app.py
#
# It does not run when another Python file imports app.py.
if __name__ == "__main__":
<<<<<<< HEAD
    # 0.0.0.0 = reachable from other devices on the same network (laptop/phone).
    # Use HOST=127.0.0.1 in .env to allow only the Pi's own browser.
    create_app().run(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "5002")),
        debug=False,
    )
=======

    # Create the Flask application and start the server.
    create_app().run(

        # Only accept connections from this computer.
        host="127.0.0.1",

        # Open the website at http://127.0.0.1:5002
        port=5002,

        # Debug mode is disabled.
        # This avoids exposing Flask's interactive debugger.
        debug=False,
    )
>>>>>>> 1c8b4b6 (Update Phase 3 customer account system and UI)
