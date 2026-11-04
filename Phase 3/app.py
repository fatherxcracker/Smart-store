
import os
import secrets
from flask import Flask, jsonify, render_template, request, session
import db
from notifications import notify, notify_error

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

db.init_db()


@app.route("/")
def home():
    return render_template("account.html")


@app.route("/api/account/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    try:
        customer = db.create_customer(
            name=data.get("name", ""),
            email=data.get("email", ""),
            password=data.get("password", ""),
            phone=data.get("phone", ""),
            language=data.get("language", "en")
        )

        session.clear()
        session["customer_id"] = customer["id"]

        return jsonify({
            **notify(
                "account_created",
                data.get("language", "en"),
                membership_number=customer["membership_number"]
            ),
            "membership_number": customer["membership_number"]
        }), 201

    except db.DatabaseError as error:
        return jsonify(notify_error(str(error))), 400


@app.route("/api/account/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    customer = db.login_customer(
        data.get("email", ""),
        data.get("password", "")
    )

    if not customer:
        return jsonify(notify("login_failed")), 401

    session.clear()
    session["customer_id"] = customer["id"]

    return jsonify(notify(
        "login_success",
        customer["language"],
        name=customer["name"]
    ))


@app.route("/api/account/me")
def my_account():
    customer_id = session.get("customer_id")

    if not customer_id:
        return jsonify(error="Please log in."), 401

    customer = db.get_customer(customer_id)

    if not customer:
        session.clear()
        return jsonify(error="Account not found."), 404

    return jsonify(customer)


@app.route("/api/account/history")
def history():
    customer_id = session.get("customer_id")

    if not customer_id:
        return jsonify(error="Please log in."), 401

    return jsonify(db.get_purchase_history(customer_id))


@app.route("/api/account/receipt/<int:purchase_id>")
def view_receipt(purchase_id):
    customer_id = session.get("customer_id")

    if not customer_id:
        return jsonify(error="Please log in."), 401

    receipt = db.get_purchase(purchase_id)

    if not receipt or receipt["customer_id"] != customer_id:
        return jsonify(error="Receipt not found."), 404

    return jsonify(receipt)


@app.route("/api/account/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify(notify("logged_out"))


if __name__ == "__main__":
    app.run(debug=True, port=5002)
