from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import sqlite3
import csv
import os

app = Flask(__name__)
app.secret_key = "supersecret"
SALE_PASSWORD = "sell123"

DB_FILE = "inventory.db"

# ---------- DATABASE FUNCTIONS ----------
def create_table():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id TEXT PRIMARY KEY, name TEXT, price REAL, stock INTEGER)''')
    conn.commit()
    conn.close()

def view_products():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, price, stock FROM products")
    rows = c.fetchall()
    conn.close()
    return rows

def fetch_product_by_id(product_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, price, stock FROM products WHERE id=?", (product_id,))
    row = c.fetchone()
    conn.close()
    return row

def add_product(product_id, name, price, stock):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO products (id, name, price, stock) VALUES (?, ?, ?, ?)",
              (product_id, name, price, stock))
    conn.commit()
    conn.close()

def update_product(product_id, name, price, stock):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE products SET name=?, price=?, stock=? WHERE id=?",
              (name, price, stock, product_id))
    conn.commit()
    conn.close()

def delete_product(product_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()

def reduce_stock(product_id, quantity):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT stock FROM products WHERE id=?", (product_id,))
    stock = c.fetchone()[0]
    if stock >= quantity:
        c.execute("UPDATE products SET stock = stock - ? WHERE id=?", (quantity, product_id))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

# ---------- ROUTES ----------
@app.route("/", methods=["GET", "POST"])
def home():
    products = view_products()
    if request.method == "POST":
        pid = request.form.get("product_id")
        product = fetch_product_by_id(pid)
        return render_template("index.html", products=products, product=product)
    return render_template("index.html", products=products, product=None)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "admin":
            session["admin"] = True
            flash("Login successful!", "success")
            return redirect(url_for("admin"))
        else:
            flash("Invalid username or password", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("admin", None)
    flash("Logged out successfully", "info")
    return redirect(url_for("home"))

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "admin" not in session:
        return redirect(url_for("login"))
    products = view_products()
    selected_product = None
    if request.method == "POST":
        pid = request.form.get("product_id")
        if pid:
            selected_product = fetch_product_by_id(pid)
    return render_template("admin.html", products=products, selected_product=selected_product)

@app.route("/add", methods=["POST"])
def add():
    if "admin" not in session:
        return redirect(url_for("login"))
    product_id = request.form["id"]
    name = request.form["name"]
    price = float(request.form["price"])
    stock = int(request.form["stock"])
    try:
        add_product(product_id, name, price, stock)
        flash("Product added successfully", "success")
    except:
        flash("Product ID already exists", "danger")
    return redirect(url_for("admin"))

@app.route("/update/<pid>", methods=["POST"])
def update(pid):
    if "admin" not in session:
        return redirect(url_for("login"))
    name = request.form["name"]
    price = float(request.form["price"])
    stock = int(request.form["stock"])
    update_product(pid, name, price, stock)
    flash("Product updated successfully", "success")
    return redirect(url_for("admin"))

@app.route("/delete/<pid>")
def delete(pid):
    if "admin" not in session:
        return redirect(url_for("login"))
    delete_product(pid)
    flash("Product deleted successfully", "info")
    return redirect(url_for("admin"))

@app.route("/sell/<pid>", methods=["POST"])
def sell(pid):
    qty = int(request.form["quantity"])
    if request.form["password"] == SALE_PASSWORD:
        if reduce_stock(pid, qty):
            flash(f"Sold {qty} units successfully", "success")
        else:
            flash("Not enough stock available", "danger")
    else:
        flash("Invalid Sale Password", "danger")
    return redirect(url_for("home"))

@app.route("/export_csv")
def export_csv():
    products = view_products()
    csv_file = "products.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Name", "Price", "Stock"])
        writer.writerows(products)
    return send_file(csv_file, as_attachment=True)

@app.route("/import_csv_route", methods=["POST"])
def import_csv_route():
    if "admin" not in session:
        return redirect(url_for("login"))
    file = request.files["file"]
    if not file:
        flash("No file selected", "danger")
        return redirect(url_for("admin"))
    csv_data = csv.reader(file.stream.read().decode("UTF-8").splitlines())
    next(csv_data)  # skip header
    count = 0
    for row in csv_data:
        try:
            add_product(row[0], row[1], float(row[2]), int(row[3]))
            count += 1
        except:
            continue
    flash(f"Imported {count} products successfully", "success")
    return redirect(url_for("admin"))

# ---------- RUN SERVER ----------
if __name__ == "__main__":
    create_table()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
