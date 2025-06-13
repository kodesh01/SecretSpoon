
from flask import Flask, render_template, request, session, redirect, url_for, flash
import psycopg2
from psycopg2.extras import RealDictCursor
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename

app = Flask(__name__, template_folder='./templates', static_folder='static')
app.secret_key = 'Kodesh@12'

# ✅ PostgreSQL Supabase Config
DB_USER = "postgres.xapwrudbiysziedhrvcd"
DB_PASSWORD = "Kodesh@12"
DB_HOST = "aws-0-ap-south-1.pooler.supabase.com"
DB_PORT = "5432"
DB_NAME = "postgres"
import os
UPLOAD_FOLDER = os.path.join('static', 'assets', 'img')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ✅ Test connection
try:
    test_conn = psycopg2.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME
    )
    print("✅ Connected to Supabase PostgreSQL for verification\n")
    test_conn.close()
except Exception as e:
    print("❌ Database connection failed:", e)

def get_db_connection():
    return psycopg2.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        cursor_factory=RealDictCursor
    )

@app.route('/set-language', methods=['POST'])
def set_language():
    selected_language = request.form.get('language', 'en')
    session['lang'] = selected_language
    return redirect(request.referrer or url_for('index'))

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()
    cur.execute("SELECT * FROM shop_products")
    products = cur.fetchall()
    conn.close()

    lang = session.get('lang', 'en')

    print("\n[DEBUG] Categories from DB:")
    for category in categories:
        print(dict(category))

    print("\n[DEBUG] Products from DB:")
    for product in products:
        print(dict(product))

    tags = sorted(set(p['tags'].lower() for p in products if p['tags']))
    return render_template("index.html", categories=categories, products=products, tags=tags, lang=lang)

# ✅ Email config
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
    cur = conn.cursor()
    cur.execute("SELECT * FROM shop_products")
    shop_products = cur.fetchall()
    conn.close()

    lang = session.get('lang', 'en')

    print("\n[DEBUG] Shop Products from DB:")
    for sp in shop_products:
        print(dict(sp))

    if category_filter:
        category_filter = category_filter.strip().lower()
        filtered_products = [p for p in shop_products if p['category'].strip().lower() == category_filter]

        print(f"\n[DEBUG] Filtered Shop Products for category '{category_filter}':")
        for fp in filtered_products:
            print(dict(fp))

        return render_template("shop.html", shop_products=filtered_products, lang=lang)

    return render_template("shop.html", shop_products=shop_products, lang=lang)

@app.route('/cart')
def cart():
    lang = session.get('lang', 'en')
    return render_template("cart.html", lang=lang)

@app.route('/story')
def story():
    lang = session.get('lang', 'en')
    return render_template("about.html", lang=lang)

@app.route('/checkout')
def checkout():
    return render_template("checkout.html")

@app.route('/details/<int:product_id>')
def details(product_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM shop_products WHERE id = %s", (product_id,))
    product = cur.fetchone()

    lang = session.get('lang', 'en')
    print("\n🔎 Shop Product Data Retrieved:")
    if product:
        print(dict(product))
    else:
        print("❌ No product found with ID:", product_id)
        conn.close()
        return "Product not found", 404

    cur.execute("SELECT * FROM product_details WHERE product_id = %s", (product_id,))
    product_details = cur.fetchone()
    print("\n📦 Product Details Data Retrieved:")
    if product_details:
        print(dict(product_details))

    product_dict = dict(product)
    product_dict["ingredients"] = product_details["ingredients"] if product_details else "No ingredients listed."
    product_dict["health_benefits"] = product_details["health_benefits"] if product_details else "No health benefits listed."

    cur.execute("SELECT * FROM shop_products WHERE category = %s AND id != %s LIMIT 4",
                (product["category"], product_id))
    related_products = cur.fetchall()

    print("\n🔗 Related Products Retrieved:")
    for rp in related_products:
        print(dict(rp))

    conn.close()
    return render_template("details.html", product=product_dict, related_products=related_products, lang=lang)

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
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()
    cur.execute("SELECT * FROM products")
    products = cur.fetchall()
    cur.execute("SELECT * FROM product_details")
    product_details = cur.fetchall()
    cur.execute("SELECT * FROM shop_products")
    shop_products = cur.fetchall()
    for sp in shop_products:
        print(dict(sp))
    conn.close()
    return render_template('admin.html', categories=categories, products=products,
                           shop_products=shop_products, product_details=product_details)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('login'))



# ----- Category Routes -----
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

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO categories (name, image_url) VALUES (%s, %s)", (name, filename))
            conn.commit()
            cur.close()
            conn.close()

            return redirect(url_for('admin'))
        else:
            return "Invalid file type", 400
    return render_template('add_category.html')

@app.route('/admin/edit/category/<name>', methods=['GET', 'POST'])
def edit_category(name):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories WHERE name = %s", (name,))
    category = cur.fetchone()

    if request.method == 'POST':
        new_name = request.form['name']
        image_file = request.files.get('image')
        image_filename = category['image_url']

        if image_file and image_file.filename != '':
            image_filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image_file.save(image_path)

        cur.execute("UPDATE categories SET name = %s, image_url = %s WHERE name = %s",
                    (new_name, image_filename, name))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('admin'))

    cur.close()
    conn.close()
    return render_template('edit_category.html', category=category)

@app.route('/admin/delete/category/<name>')
def delete_category(name):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM categories WHERE name = %s", (name,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('admin'))

# ----- Shop Products Routes -----
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
        sku = 'Null'
        tags = request.form['tags']
        stock_kg = request.form['stock_kg']

        img_default = request.files['img_default']
        img_hover = request.files['img_hover']

        filename_default = secure_filename(img_default.filename) if img_default and allowed_file(img_default.filename) else ""
        filename_hover = secure_filename(img_hover.filename) if img_hover and allowed_file(img_hover.filename) else ""

        if filename_default:
            img_default.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_default))
        if filename_hover:
            img_hover.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_hover))

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO shop_products (title, category, img_default, img_hover, new_price, old_price, badge, badge_class, description, brand, sku, tags, stock_kg)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            title, category, f"assets/img/{filename_default}", f"assets/img/{filename_hover}", new_price, old_price,
            badge, badge_class, description, brand, sku, tags, stock_kg
        ))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('admin'))

    return render_template('add_shop_product.html')

@app.route('/admin/edit/shop_product/<int:id>', methods=['GET', 'POST'])
def edit_shop_product(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM shop_products WHERE id = %s", (id,))
    sp = cur.fetchone()

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

        if img_default and img_default.filename:
            filename_default = secure_filename(img_default.filename)
            img_default.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_default))
            img_default_path = f"assets/img/{filename_default}"

        if img_hover and img_hover.filename:
            filename_hover = secure_filename(img_hover.filename)
            img_hover.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_hover))
            img_hover_path = f"assets/img/{filename_hover}"

        cur.execute("""
            UPDATE shop_products SET 
                title=%s, category=%s, img_default=%s, img_hover=%s, new_price=%s, old_price=%s, 
                badge=%s, badge_class=%s, description=%s, brand=%s, sku=%s, tags=%s, stock_kg=%s
            WHERE id=%s
        """, (
            title, category, img_default_path, img_hover_path, new_price, old_price,
            badge, badge_class, description, brand, sku, tags, stock_kg, id
        ))

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('admin'))

    cur.close()
    conn.close()
    return render_template('edit_shop_product.html', sp=sp)

@app.route('/admin/delete/shop_product/<int:id>')
def delete_shop_product(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM shop_products WHERE id = %s", (id,))
    conn.commit()
    cur.close()
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
        cur = conn.cursor()
        cur.execute("INSERT INTO product_details (product_id, ingredients, health_benefits) VALUES (%s, %s, %s)",
                    (product_id, ingredients, health_benefits))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('admin'))
    return render_template('add_product_detail.html')

@app.route('/admin/edit/product_detail/<int:product_id>', methods=['GET', 'POST'])
def edit_product_detail(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM product_details WHERE product_id = %s", (product_id,))
    detail = cur.fetchone()
    if request.method == 'POST':
        ingredients = request.form['ingredients']
        health_benefits = request.form['health_benefits']
        cur.execute("UPDATE product_details SET ingredients=%s, health_benefits=%s WHERE product_id=%s",
                    (ingredients, health_benefits, product_id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('admin'))
    cur.close()
    conn.close()
    return render_template('edit_product_detail.html', detail=detail)

@app.route('/admin/delete/product_detail/<int:product_id>')
def delete_product_detail(product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM product_details WHERE product_id = %s", (product_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)