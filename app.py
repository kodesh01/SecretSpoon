from flask import Flask, render_template, request ,session, redirect, url_for ,flash
import sqlite3
app = Flask(__name__, template_folder='./templates', static_folder='static')
DATABASE = 'shop_data.db'
app.secret_key = 'Kodesh@12'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Enables dict-like access
    return conn
@app.route('/set-language', methods=['POST'])
def set_language():
    selected_language = request.form.get('language', 'en')
    session['lang'] = selected_language
    return redirect(request.referrer or url_for('index'))
@app.route('/')
def index():
    conn = get_db_connection()
    categories = conn.execute("SELECT * FROM categories").fetchall()
    products = conn.execute("SELECT * FROM shop_products").fetchall()
    conn.close()
    lang = session.get('lang', 'en')
    # Debug: Print all categories
    print("\n[DEBUG] Categories from DB:")
    for category in categories:
        print(dict(category))

    # Debug: Print all products
    print("\n[DEBUG] Products from DB:")
    for product in products:
        print(dict(product))

    tags = sorted(set(p['tags'].lower() for p in products if p['tags']))

    return render_template("index.html", categories=categories, products=products, tags=tags ,lang=lang)

from flask_mail import Mail, Message
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'mjanokodesh@gmail.com'
app.config['MAIL_PASSWORD'] = 'gngn wxai cvyq emjq'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/send-message", methods=["POST"])
def send_message():
    name = request.form["name"]
    email = request.form["email"]
    message = request.form["message"]
    msg = Message(
        subject=f"New Contact Message from {name}",
        sender=email,
        recipients=["mjanokodesh@gmail.com"],
        body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
    )
    mail.send(msg)
    flash("success")
    return redirect("/contact")




@app.route('/shop')
def shop():
    category_filter = request.args.get('category')
    conn = get_db_connection()
    shop_products = conn.execute("SELECT * FROM shop_products").fetchall()
    conn.close()

    # Debug: Print all shop products
    print("\n[DEBUG] Shop Products from DB:")
    lang = session.get('lang', 'en')
    for sp in shop_products:
        print(dict(sp))

    if category_filter:
        category_filter = category_filter.strip().lower()
        filtered_products = [p for p in shop_products if p['category'].strip().lower() == category_filter]
        
        # Debug: Filtered shop products
        print(f"\n[DEBUG] Filtered Shop Products for category '{category_filter}':")
        for fp in filtered_products:
            print(dict(fp))

        return render_template("shop.html", shop_products=filtered_products ,lang=lang)
    
    return render_template("shop.html", shop_products=shop_products ,lang=lang)

@app.route('/cart')
def cart():
    lang = session.get('lang', 'en')

    return render_template("cart.html",lang=lang)
@app.route('/story')
def story():
    lang = session.get('lang', 'en')

    return render_template("about.html",lang=lang)

@app.route('/checkout')
def checkout():
    return render_template("checkout.html")

@app.route('/details/<int:product_id>')
def details(product_id):
    conn = get_db_connection()  

    # Get current product
    product = conn.execute("SELECT * FROM shop_products WHERE id = ?", (product_id,)).fetchone()
    print("\n🔎 Shop Product Data Retrieved:")
    lang = session.get('lang', 'en')
    if product:
        print(dict(product))
    else:
        print("❌ No product found with ID:", product_id)
        conn.close()
        return "Product not found", 404

    # Get product details
    product_details = conn.execute("SELECT * FROM product_details WHERE product_id = ?", (product_id,)).fetchone()
    print("\n📦 Product Details Data Retrieved:")
    if product_details:
        print(dict(product_details))
    else:
        print("⚠️ No product details found for ID:", product_id)

    # Convert product to dict and attach additional details
    product_dict = dict(product)
    if product_details:
        product_dict["ingredients"] = product_details["ingredients"]
        product_dict["health_benefits"] = product_details["health_benefits"]
    else:
        product_dict["ingredients"] = "No ingredients listed."
        product_dict["health_benefits"] = "No health benefits listed."

    # ✅ Fetch related products (same category, excluding current)
    related_products = conn.execute(
        "SELECT * FROM shop_products WHERE category = ? AND id != ? LIMIT 4",
        (product["category"], product_id)
    ).fetchall()

    print("\n🔗 Related Products Retrieved:")
    for rp in related_products:
        print(dict(rp))
    conn.close()
    return render_template("details.html", product=product_dict, related_products=related_products,lang=lang)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    categories = conn.execute("SELECT * FROM categories").fetchall()
    products = conn.execute("SELECT * FROM products").fetchall()
    product_details = conn.execute("SELECT * FROM product_details").fetchall()
    shop_products = conn.execute("SELECT * FROM shop_products").fetchall()
    for sp in shop_products:
        print(dict(sp))
    conn.close()
    return render_template('admin.html', categories=categories, products=products,
                           shop_products=shop_products, product_details=product_details)
@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('login'))

# ----- Categories -----
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.join('static', 'assets', 'img')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/admin/add/category', methods=['GET', 'POST'])
def add_category():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        image = request.files['image']

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(save_path)

            # Only save filename to DB
            conn = get_db_connection()
            conn.execute("INSERT INTO categories (name, image_url) VALUES (?, ?)", (name, filename))
            conn.commit()
            conn.close()

            return redirect(url_for('admin'))
        else:
            return "Invalid file type", 400
    return render_template('add_category.html')


import os
from werkzeug.utils import secure_filename

@app.route('/admin/edit/category/<name>', methods=['GET', 'POST'])
def edit_category(name):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    category = conn.execute("SELECT * FROM categories WHERE name = ?", (name,)).fetchone()

    if request.method == 'POST':
        new_name = request.form['name']
        image_file = request.files.get('image')

        # Use existing image if no new one is uploaded
        image_filename = category['image_url']

        if image_file and image_file.filename != '':
            image_filename = secure_filename(image_file.filename)
            image_path = os.path.join('static/assets/img', image_filename)
            image_file.save(image_path)

        conn.execute("UPDATE categories SET name = ?, image_url = ? WHERE name = ?",
                     (new_name, image_filename, name))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))

    conn.close()
    return render_template('edit_category.html', category=category)

@app.route('/admin/delete/category/<name>')
def delete_category(name):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute("DELETE FROM categories WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))


# ----- Shop Products -----
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/assets/img/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/admin/add/shop_product', methods=['GET', 'POST'])
def add_shop_product():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        new_price = request.form['new_price']
        old_price = request.form['old_price']
        badge = request.form['badge']
        badge_class = request.form['badge_class']
        description = request.form['description']
        brand = request.form['brand']
        # sku = request.form['sku']
        tags = request.form['tags']
        stock_kg = request.form['stock_kg']

        # Handle image uploads
        img_default = request.files['img_default']
        img_hover = request.files['img_hover']

        if img_default and allowed_file(img_default.filename):
            filename_default = secure_filename(img_default.filename)
            img_default.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_default))
        else:
            filename_default = ""

        if img_hover and allowed_file(img_hover.filename):
            filename_hover = secure_filename(img_hover.filename)
            img_hover.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_hover))
        else:
            filename_hover = ""

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO shop_products (title, category, img_default, img_hover, new_price, old_price, badge, badge_class, description, brand, tags, stock_kg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title, category,
            f"assets/img/{filename_default}",
            f"assets/img/{filename_hover}",
            new_price, old_price,
            badge, badge_class,
            description, brand, tags, stock_kg
        ))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    
    return render_template('add_shop_product.html')

@app.route('/admin/edit/shop_product/<int:id>', methods=['GET', 'POST'])
def edit_shop_product(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    sp = conn.execute("SELECT * FROM shop_products WHERE id = ?", (id,)).fetchone()

    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        new_price = request.form['new_price']
        old_price = request.form['old_price']
        badge = request.form['badge']
        badge_class = request.form['badge_class']
        description = request.form['description']
        brand = request.form['brand']
        sku = 'Null'
        tags = request.form['tags']
        stock_kg = request.form['stock_kg']

        img_default = request.files.get('img_default')
        img_hover = request.files.get('img_hover')

        img_default_path = sp['img_default']
        img_hover_path = sp['img_hover']

        if img_default and img_default.filename != '':
            filename_default = secure_filename(img_default.filename)
            img_default.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_default))
            img_default_path = f"assets/img/{filename_default}"

        if img_hover and img_hover.filename != '':
            filename_hover = secure_filename(img_hover.filename)
            img_hover.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_hover))
            img_hover_path = f"assets/img/{filename_hover}"

        conn.execute("""
            UPDATE shop_products SET 
              title=?, category=?, img_default=?, img_hover=?, new_price=?, old_price=?, 
              badge=?, badge_class=?, description=?, brand=?, sku=?, tags=?, stock_kg=?
            WHERE id=?
        """, (
            title, category, img_default_path, img_hover_path, new_price, old_price,
            badge, badge_class, description, brand, sku, tags, stock_kg, id
        ))

        conn.commit()
        conn.close()
        return redirect(url_for('admin'))

    conn.close()
    return render_template('edit_shop_product.html', sp=sp)


@app.route('/admin/delete/shop_product/<int:id>')
def delete_shop_product(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute("DELETE FROM shop_products WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

# ----- Product Details -----
@app.route('/admin/add/product_detail', methods=['GET', 'POST'])
def add_product_detail():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        product_id = request.form['product_id']
        ingredients = request.form['ingredients']
        health_benefits = request.form['health_benefits']
        conn = get_db_connection()
        conn.execute("INSERT INTO product_details (product_id, ingredients, health_benefits) VALUES (?, ?, ?)",
                     (product_id, ingredients, health_benefits))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    return render_template('add_product_detail.html')

@app.route('/admin/edit/product_detail/<int:product_id>', methods=['GET', 'POST'])
def edit_product_detail(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    detail = conn.execute("SELECT * FROM product_details WHERE product_id = ?", (product_id,)).fetchone()
    if request.method == 'POST':
        ingredients = request.form['ingredients']
        health_benefits = request.form['health_benefits']
        conn.execute("""UPDATE product_details SET ingredients=?, health_benefits=? WHERE product_id=?""",
                     (ingredients, health_benefits, product_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    conn.close()
    return render_template('edit_product_detail.html', detail=detail)

@app.route('/admin/delete/product_detail/<int:product_id>')
def delete_product_detail(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute("DELETE FROM product_details WHERE product_id = ?", (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)


# from flask import Flask, render_template ,request
# import pandas as pd
# import requests
# from io import StringIO
# app = Flask(__name__, template_folder='.', static_folder='static')

# BASE_SHEET_URL = "https://docs.google.com/spreadsheets/d/17UHh3lh6XxjtIr5orxJ5ZJWyZkonZehGGUV9aE7dMTo/export?format=csv&gid={gid}"
# CATEGORIES_GID = "0"
# PRODUCTS_GID = "2001520264"

# def fetch_sheet(gid):
#     url = BASE_SHEET_URL.format(gid=gid)
#     response = requests.get(url)
#     if response.status_code != 200:
#         print(f"Failed to fetch GID {gid} with status code: {response.status_code}")
#         return None
#     print(f"Fetched data for GID {gid}:\n{response.text[:500]}...") 
#     return pd.read_csv(StringIO(response.text))

# @app.route('/')
# def index():
#     categories_df = fetch_sheet(CATEGORIES_GID)
#     products_df = fetch_sheet(PRODUCTS_GID)
#     if categories_df is None or products_df is None:
#         return "Failed to fetch data from Google Sheets", 500
#     # Debug output
#     print("Categories DataFrame:")
#     print(categories_df)
#     print("Products DataFrame:")
#     print(products_df)
#     categories = categories_df.to_dict(orient='records')
#     products = products_df.to_dict(orient='records')
#     # Debug output
#     print("Converted Categories:")
#     print(categories)
#     print("Converted Products:")
#     print(products)
#     # Extract unique tags from the products
#     tags = sorted(set(product.get('tag', '').lower() for product in products if product.get('tag')))
#     print("Extracted Tags:")
#     print(tags)

#     return render_template("index.html", categories=categories, products=products, tags=tags)
# SHOP_PRODUCTS_GID = "542676221"  # Sheet 3 for shop.html

# from flask import request

# @app.route('/shop')
# def shop():
#     print("\n[DEBUG] /shop route has been called\n")
#     category_filter = request.args.get('category')
#     print(f"\n[DEBUG] Received category filter from URL: '{category_filter}'\n")

#     shop_products_df = fetch_sheet(SHOP_PRODUCTS_GID)
#     if shop_products_df is None:
#         return "Failed to fetch shop products data from Google Sheets", 500

#     shop_products = shop_products_df.to_dict(orient='records')
#     print(f"[DEBUG] Total products fetched: {len(shop_products)}")

#     # Normalize all categories
#     for product in shop_products:
#         if 'category' in product and isinstance(product['category'], str):
#             product['category'] = product['category'].strip().lower()

#     if category_filter:
#         normalized_filter = category_filter.strip().lower()

#         available_categories = set(p.get('category') for p in shop_products if p.get('category'))
#         print(f"[DEBUG] Available categories: {available_categories}")

#         shop_products = [
#             p for p in shop_products
#             if p.get('category') == normalized_filter
#         ]
#         print(f"[DEBUG] Filtered products count for '{category_filter}': {len(shop_products)}")

#     return render_template("shop.html", shop_products=shop_products)



# @app.route('/details')
# def details():
#     return render_template("details.html")

# if __name__ == '__main__':
#     app.run(debug=True)
