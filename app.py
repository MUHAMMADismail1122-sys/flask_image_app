from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import json, os, uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey_change_this"

USERS_FILE = "users.json"
PRODUCTS_FILE = "products.json"
UPLOAD_FOLDER = os.path.join("static", "images")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ------------------ Helper Functions ------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def load_products():
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, "r") as f:
            try:
                products = json.load(f)
                # ✅ Make sure price is float
                for p in products:
                    p["price"] = float(p["price"])
                return products
            except:
                return []
    return []

def save_products(products):
    with open(PRODUCTS_FILE, "w") as f:
        json.dump(products, f, indent=4)

PROMOTIONS_FILE = "promotions.json"

def load_promotions():
    if os.path.exists(PROMOTIONS_FILE):
        with open(PROMOTIONS_FILE, "r") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []

def save_promotions(promotions):
    with open(PROMOTIONS_FILE, "w") as f:
        json.dump(promotions, f, indent=4)

# ------------------ User Routes ------------------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        confirm = request.form.get("confirm").strip()

        users = load_users()
        if username in users:
            flash("Username already exists.", "error")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))
        if not username or not password:
            flash("Please fill all fields.", "error")
            return redirect(url_for("register"))

        users[username] = {"password": password}
        save_users(users)
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        users = load_users()

        if username not in users or users[username]["password"] != password:
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))

        session["username"] = username
        flash("Login successful.", "success")
        return redirect(url_for("products"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


# ------------------ Product Routes ------------------
@app.route("/products")
def products():
    products = load_products()
    return render_template("products.html", products=products)

@app.route("/add_product", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        products = load_products()
        product_id = str(uuid.uuid4())
        name = request.form["name"]
        price = request.form["price"]
        description = request.form.get("description", "")
        image = None

        file = request.files.get("image")
        if file and file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            image = f"images/{filename}"

        new_product = {
            "id": product_id,
            "name": name,
            "price": float(price),
            "description": description,
            "image": image or "",
        }

        products.append(new_product)
        save_products(products)
        return redirect(url_for("products"))

    return render_template("add_product.html")

@app.route("/edit_product/<product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    products = load_products()
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        return "Product not found", 404

    if request.method == "POST":
        product["name"] = request.form["name"]
        product["price"] = float(request.form["price"])
        product["description"] = request.form.get("description", "")

        file = request.files.get("image")
        if file and file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            product["image"] = f"images/{filename}"

        save_products(products)
        return redirect(url_for("products"))

    return render_template("edit_product.html", product=product)

@app.route("/delete_product/<product_id>", methods=["POST"])
def delete_product(product_id):
    products = load_products()
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        return jsonify({"success": False, "error": "Product not found"}), 404

    # Delete image file
    if product["image"]:
        image_path = os.path.join("static", product["image"])
        if os.path.exists(image_path):
            os.remove(image_path)

    products = [p for p in products if p["id"] != product_id]
    save_products(products)
    return jsonify({"success": True}), 200


# ------------------ Order Summary ------------------
@app.route("/order_summary", methods=["POST"])
def order_summary():
    order_data = request.form.get("order_data")
    if not order_data:
        return render_template("order_summary.html", items=[], total_price=0)

    try:
        items = json.loads(order_data)
    except Exception as e:
        print("JSON Decode Error:", e)
        items = []

    total_price = sum(
        float(item.get("price", 0)) * int(item.get("quantity", 0))
        for item in items
    )

    return render_template("order_summary.html", items=items, total_price=total_price)

@app.route("/save_order_changes", methods=["POST"])
def save_order_changes():
    data = request.get_json() or {}
    session["order_items"] = data.get("items", [])
    return jsonify(success=True)

@app.route("/confirm_order", methods=["POST"])
def confirm_order():
    session.pop("order_items", None)
    return jsonify(success=True)


# ------------------ Cache Disable ------------------
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/promotions")
def promotions():
    promotions = load_promotions()
    return render_template("promotions.html", promotions=promotions)



@app.route("/add_promotion", methods=["GET", "POST"])
def add_promotion():
    if request.method == "POST":
        promotions = []

        # load existing promotions.json if it exists
        if os.path.exists("promotions.json"):
            with open("promotions.json", "r") as f:
                promotions = json.load(f)

        name = request.form["name"]
        price = float(request.form["price"])
        saving = float(request.form["saving"])
        quantity = int(request.form["quantity"])
        description = request.form["description"]

        file = request.files["image"]
        image = None
        if file and file.filename:
            filename = file.filename
            filepath = os.path.join("static/uploads", filename)
            file.save(filepath)
            image = f"uploads/{filename}"

        new_item = {
            "id": len(promotions) + 1,
            "name": name,
            "price": price,
            "saving": saving,
            "quantity": quantity,
            "description": description,
            "image": image
        }

        promotions.append(new_item)
        with open("promotions.json", "w") as f:
            json.dump(promotions, f, indent=4)

        return redirect(url_for("promotions"))

    return render_template("add_promotion.html")


import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

    
