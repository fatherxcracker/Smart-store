"""Phase 3 web application: inventory and product management."""

from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    abort,
)

# Load settings before the database module reads them.
load_dotenv()
import db


def create_app():
    app = Flask(__name__)
    db.init_db()

    # Inventory dashboard
    @app.get("/")
    @app.get("/inventory")
    def inventory():
        products = db.get_inventory()

        return render_template(
            "inventory.html",
            products=products,
        )

    # Add a product
    @app.route("/products/add", methods=["GET", "POST"])
    def add_product():
        error = None

        if request.method == "POST":
            try:
                db.add_product(
                    name=request.form.get("name", "").strip(),
                    category=request.form.get("category", "").strip(),
                    price=request.form.get("price", ""),
                    upc=request.form.get("upc", "").strip(),
                    epc=request.form.get("epc", "").strip(),
                    producer=request.form.get("producer", "").strip(),
                )

                return redirect(url_for("inventory"))

            except db.DatabaseError as exc:
                error = str(exc)

        return render_template(
            "add_product.html",
            error=error,
            values=request.form,
        )

    # Edit an existing product
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
                db.update_product(
                    product_id=product_id,
                    name=request.form.get("name", "").strip(),
                    category=request.form.get("category", "").strip(),
                    price=request.form.get("price", ""),
                    upc=request.form.get("upc", "").strip(),
                    epc=request.form.get("epc", "").strip(),
                    producer=request.form.get("producer", "").strip(),
                )

                return redirect(url_for("inventory"))

            except db.DatabaseError as exc:
                error = str(exc)

        return render_template(
            "edit_product.html",
            product=product,
            values=values,
            error=error,
        )

    # Delete a product while preserving its past receipts
    @app.post("/products/<int:product_id>/delete")
    def delete_product(product_id):
        product = db.get_product(product_id)

        if product is None:
            abort(404)

        db.delete_product(product_id)

        return redirect(url_for("inventory"))

    return app


if __name__ == "__main__":
    create_app().run(
        host="127.0.0.1",
        port=5002,
        debug=False,
    )