
from flask import Flask, render_template, request, session, redirect, url_for, flash
import psycopg2
from psycopg2.extras import RealDictCursor
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_bcrypt import Bcrypt
import psycopg2
from datetime import datetime
import psycopg2.extras
from werkzeug.security import generate_password_hash, check_password_hash
import bcrypt
import razorpay
app = Flask(__name__, template_folder='./templates', static_folder='static')
app.secret_key = "Kodesh@12"

# ✅ razorpay authentication
client = razorpay.Client(auth=("rzp_test_uob50EBgd6fzQE", "iJM4KW20FygmRRYRJo1Gr8HI"))

@app.route("/create_order", methods=["POST"])
def create_order():
    data = request.get_json()
    amount = data["amount"]  # in paise. ₹100 = 10000

    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1  # Auto-capture after success
    })

    return jsonify(order)

# ✅ PostgreSQL Supabase Config
DB_USER = "postgres.xapwrudbiysziedhrvcd"
DB_PASSWORD = "Kodesh@12"
DB_HOST = "aws-0-ap-south-1.pooler.supabase.com"
DB_PORT = "5432"
DB_NAME = "postgres"
import os
UPLOAD_FOLDER = os.path.join('static', 'assets', 'img')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif','webp'}
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

    # Fetch categories and products
    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()

    cur.execute("SELECT * FROM shop_products")
    products = cur.fetchall()

    # Fetch user info if logged in
    user_data = None
    if 'user_id' in session:
        cur.execute("SELECT username FROM users WHERE id = %s", (session['user_id'],))
        user_data = cur.fetchone()

    # Now safe to close
    conn.close()

    lang = session.get('lang', 'en')

    # Extract tags
    tags = sorted(set(p['tags'].lower() for p in products if p['tags']))

    return render_template(
        "index.html",
        categories=categories,
        products=products,
        tags=tags,
        lang=lang,
        user=user_data
    )

# ✅ Email config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'mjanokodesh@gmail.com'
app.config['MAIL_PASSWORD'] = 'gngn wxai cvyq emjq'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)
############################################## LOGIN ########################################################

import random
from flask import jsonify
def send_email_otp(email, otp):
    msg = Message('Your OTP Verification Code', sender=app.config['MAIL_USERNAME'], recipients=[email])
    msg.body = f"Your OTP is: {otp}"
    mail.send(msg)

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    entered_otp = request.form.get("otp")
    temp_user = session.get("temp_user")

    if not temp_user or entered_otp != temp_user['otp']:
        return jsonify({'status': 'error', 'message': 'Invalid OTP'})

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO users (username, email, mobile, password, address_line, city, state, pincode)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            temp_user['username'],
            temp_user['email'],
            temp_user['mobile'],
            temp_user['password'],
            temp_user['address_line'],
            temp_user['city'],
            temp_user['state'],
            temp_user['pincode']
        ))
        conn.commit()
        session.pop('temp_user', None)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        cur.close()
        conn.close()

@app.route("/user_login", methods=["GET"])
def user_login():
    if 'user_id' in session:
        return redirect(url_for("account"))
    return render_template("login-register.html")

@app.route("/register", methods=["POST"])
def register_user():
    username = request.form["username"]
    email = request.form["email"]
    mobile = request.form["mobile"]
    password = request.form["password"]
    confirm_password = request.form["confirm_password"]

    address_line = request.form["address_line"]
    city = request.form["city"]
    state = request.form["state"]
    pincode = request.form["pincode"]

    if password != confirm_password:
        return jsonify({'status': 'error', 'message': 'Passwords do not match.'})

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email=%s OR mobile=%s", (email, mobile))
    if cur.fetchone():
        return jsonify({'status': 'error', 'message': 'Email or Mobile already registered.'})

    otp = str(random.randint(100000, 999999))
    send_email_otp(email, otp)

    session['temp_user'] = {
        'username': username,
        'email': email,
        'mobile': mobile,
        'password': bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        'address_line': address_line,
        'city': city,
        'state': state,
        'pincode': pincode,
        'otp': otp
    }

    return jsonify({'status': 'otp_sent'})

@app.route("/user_login_post", methods=["POST"])
def user_login_post():
    
    email = request.form["email"]
    password = request.form["password"]

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        print("Fetched user:", user)

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash("Login successful!", "success")
            return redirect(url_for("account"))
        else:
            flash("Invalid credentials", "error")
    except Exception as e:
        flash("Login failed: " + str(e), "error")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("user_login"))

@app.route("/user_logout", methods=["GET"])
def user_logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("user_login"))


##############################################################################
                           # ---    PLACE  ORDER --------
##############################################################################



@app.route('/place_order', methods=['POST'])
def place_order():
    try:
        user_id = session.get('user_id')  # Check if user is logged in
        if not user_id:
            return jsonify({'status': 'redirect', 'url': '/user_login'}), 401

        data = request.json
        product_title = data.get('title')
        quantity = int(data.get('quantity'))
        unit = data.get('unit')
        price = float(data.get('price'))
        


        total_cost = price * (quantity / 1000 if unit == "g" else quantity)

        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
    INSERT INTO orders (user_id, order_date, title, quantity, unit, total_cost, status)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
""", (user_id, datetime.now(), product_title, quantity, unit, total_cost, 'Pending'))

        print("🛒 Order Data to Insert:")
        print(f"User ID: {user_id}")
        print(f"Title: {product_title}")
        print(f"Quantity: {quantity} {unit}")
        print(f"Price per Unit: ₹{price}")
        print(f"Total Cost: ₹{total_cost:.2f}")
        print("Status: Pending")
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Order placed successfully'}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
import json 
@app.route('/place_order_bulk', methods=['POST'])
def place_order_bulk():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'status': 'redirect', 'url': '/user_login'}), 401

        data = request.get_json()
        cart = data.get("cart", [])
        address = data.get("address", "").strip()
        payment_type = data.get("payment", "").strip().upper()

        print("Incoming JSON:", data)

        if not cart:
            return jsonify({'status': 'error', 'message': 'Cart is empty'}), 400
        if not address or not payment_type:
            return jsonify({'status': 'error', 'message': 'Address and payment type required'}), 400

        # Convert payment type string to boolean value
        payment_status = True if payment_type == "UPI" else False

        conn = get_db_connection()
        cur = conn.cursor()

        for item in cart:
            title = item.get('title')
            quantity = float(item.get('quantity'))  # Quantity
            unit = item.get('unit', 'g').lower()
            price = float(item.get('price'))        # ₹ per unit

            # Calculate total cost
            if unit in ["g", "gram", "grams", "kg", "kilogram", "kilograms"]:
                total_cost = price * (quantity / 1000)
            elif unit in ["ml", "millilitre", "millilitres", "litre", "litres"]:
                total_cost = price * (quantity / 1000)
            elif unit in ["pcs", "pieces", "unit", "shirt", "pants", "item"]:
                total_cost = price * quantity
            else:
                total_cost = price * quantity  # fallback

            # ✅ Insert payment_status as boolean
            cur.execute("""
                INSERT INTO orders (user_id, order_date, title, total_cost, status, quantity, unit, address, payment)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, datetime.now(), title, round(total_cost, 2), 'Pending', quantity, unit, address, payment_status))

            print("📝 Inserting order:", {
                "user_id": user_id,
                "order_date": datetime.now(),
                "title": title,
                "total_cost": round(total_cost, 2),
                "status": 'Pending',
                "quantity": quantity,
                "unit": unit,
                "address": address,
                "payment": payment_status
            })

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'status': 'success', 'message': 'All items ordered successfully'})
    except Exception as e:
        print("🔥 Error placing order:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

#########################################################################################################################
                                               #----- Account Manager ------
########################################################################################################################
import psycopg2.extras
@app.route("/account")
def account():
    if 'user_id' not in session:
        return redirect(url_for("user_login"))

    user_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get orders
    cursor.execute("""
        SELECT id, order_date, title, status, total_cost 
        FROM orders 
        WHERE user_id = %s 
        ORDER BY order_date DESC
    """, (user_id,))
    user_orders = cursor.fetchall()

    # Get user details
    cursor.execute("""
        SELECT username, email, mobile, address_line, city, state, pincode
        FROM users 
        WHERE id = %s
    """, (user_id,))
    user_data = cursor.fetchone()

    cursor.close()
    conn.close()
    print("User Data:", user_data)
    print("User Orders:")
    for order in user_orders:
        print(order)


    return render_template("accounts.html", orders=user_orders, user=user_data , username=user_data["username"])

@app.route("/cancel-order/<int:order_id>", methods=["POST"])
def cancel_order(order_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'})

    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Ensure user owns the order
        cur.execute("SELECT id FROM orders WHERE id = %s AND user_id = %s", (order_id, user_id))
        if not cur.fetchone():
            return jsonify({'status': 'error', 'message': 'Order not found or not yours'})

        # Delete the order
        cur.execute("DELETE FROM orders WHERE id = %s AND user_id = %s", (order_id, user_id))
        conn.commit()

        return jsonify({'status': 'success', 'message': 'Order cancelled successfully'})

    except Exception as e:
        print("❌ Error cancelling order:", str(e))
        return jsonify({'status': 'error', 'message': 'Failed to cancel order'})

    finally:
        cur.close()
        conn.close()
@app.route("/update-profile", methods=["POST"])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for("user_login"))

    user_id = session.get('user_id')
    username = request.form.get('username')
    mobile = request.form.get('mobile')

    # Validate input
    if not username or not mobile:
        return "Invalid input", 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users 
        SET username = %s, mobile = %s 
        WHERE id = %s
    """, (username, mobile, user_id))

    conn.commit()
    cursor.close()
    conn.close()

    # Optional: update session
    session['username'] = username

    return redirect(url_for("account"))

@app.route("/update-address", methods=["POST"])
def update_address():
    if 'user_id' not in session:
        return redirect(url_for("user_login"))

    user_id = session.get('user_id')

    address_line = request.form["address_line"]
    city = request.form["city"]
    state = request.form["state"]
    pincode = request.form["pincode"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET address_line = %s, city = %s, state = %s, pincode = %s
        WHERE id = %s
    """, (address_line, city, state, pincode, user_id))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for("account"))
from flask import request, jsonify, session
import bcrypt

@app.route("/change-password", methods=["POST"])
def change_password():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'User not logged in'})

    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    print("📥 Got:")
    print("Current Password:", current_password)
    print("New Password:", new_password)
    print("Confirm Password:", confirm_password)

    if new_password != confirm_password:
        return jsonify({'status': 'error', 'message': 'New passwords do not match'})

    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT password FROM users WHERE id = %s", (user_id,))
        result = cur.fetchone()
        if not result:
            return jsonify({'status': 'error', 'message': 'User not found'})

        # Fix: Use column name to access password
        hashed_password = result['password']
        print("🔐 Stored hashed password (from DB):", hashed_password)


        if not bcrypt.checkpw(current_password.encode(), hashed_password.encode()):
            print("❌ Password check failed")
            return jsonify({'status': 'error', 'message': 'Current password is incorrect'})

        print("✅ Password check passed")

        # 🧂 Hash the new password
        new_hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        print("📤 New Hashed Password to store:", new_hashed)

        # 🔄 Update in DB
        cur.execute("UPDATE users SET password = %s WHERE id = %s", (new_hashed, user_id))
        conn.commit()


        return jsonify({'status': 'success', 'message': 'Password updated successfully'})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'Exception: {str(e)}'})

    finally:
        cur.close()
        conn.close()

##########################################################################################################################

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
    user_id=None
    user_data = None

    lang = session.get('lang', 'en')
    if 'user_id' in session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE id = %s", (session['user_id'],))
        user_data = cur.fetchone()
        conn.close()

    print("\n[DEBUG] Shop Products from DB:")
    for sp in shop_products:
        print(dict(sp))

    if category_filter:
        category_filter = category_filter.strip().lower()
        filtered_products = [p for p in shop_products if p['category'].strip().lower() == category_filter]

        print(f"\n[DEBUG] Filtered Shop Products for category '{category_filter}':")
        for fp in filtered_products:
            print(dict(fp))

        return render_template("shop.html", shop_products=filtered_products, lang=lang ,user=user_data)

    return render_template("shop.html", shop_products=shop_products, lang=lang ,user=user_data)

@app.route('/cart')
def cart():
    lang = session.get('lang', 'en')
    user_id=None

    lang = session.get('lang', 'en')
    if 'user_id' in session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE id = %s", (session['user_id'],))
        user_data = cur.fetchone()
        conn.close()
    return render_template("cart.html", lang=lang, user=user_data)


@app.route('/story')
def story():
    lang = session.get('lang', 'en')
    user_data = None

    if 'user_id' in session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE id = %s", (session['user_id'],))
        user_data = cur.fetchone()
        conn.close()
    return render_template("about.html", lang=lang, user=user_data)

@app.route("/checkout")
def checkout():
    order = session.get("order")
    if not order:
        return redirect("/")  # or show a message

    return render_template("checkout.html", order=order)

@app.route('/details/<int:product_id>')
def details(product_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get product
    cur.execute("SELECT * FROM shop_products WHERE id = %s", (product_id,))
    product = cur.fetchone()

    if not product:
        conn.close()
        return "Product not found", 404

    # Get language
    lang = session.get('lang', 'en')

    # Get user (optional)
    user_data = None
    if 'user_id' in session:
        user_cur = conn.cursor()
        user_cur.execute("SELECT username FROM users WHERE id = %s", (session['user_id'],))
        user_data = user_cur.fetchone()
        user_cur.close()

    print("\n🔎 Shop Product Data Retrieved:")
    print(dict(product))

    # Get product details
    cur.execute("SELECT * FROM product_details WHERE product_id = %s", (product_id,))
    product_details = cur.fetchone()

    print("\n📦 Product Details Data Retrieved:")
    if product_details:
        print(dict(product_details))

    # Prepare product dictionary
    product_dict = dict(product)
    product_dict["ingredients"] = product_details["ingredients"] if product_details else "No ingredients listed."
    product_dict["health_benefits"] = product_details["health_benefits"] if product_details else "No health benefits listed."

    # Get related products
    cur.execute("SELECT * FROM shop_products WHERE category = %s AND id != %s LIMIT 4",
                (product["category"], product_id))
    related_products = cur.fetchall()
    print("\n🔗 Related Products Retrieved:")
    for rp in related_products:
        print(dict(rp))

    cur.close()
    conn.close()

    return render_template("details.html", product=product_dict, related_products=related_products, lang=lang, user=user_data)

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
@app.route('/admin/products')
def admin_products():
    conn = get_db_connection()
    categories = conn.execute("SELECT * FROM categories").fetchall()
    shop_products = conn.execute("SELECT * FROM shop_products").fetchall()
    product_details = conn.execute("SELECT * FROM product_details").fetchall()
    conn.close()
    return render_template('admin_products.html',
                           categories=categories,
                           shop_products=shop_products,
                           product_details=product_details)

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()

    cur.execute("SELECT * FROM products")
    products = cur.fetchall()

    cur.execute("SELECT * FROM product_details")
    product_details = cur.fetchall()

    cur.execute("SELECT * FROM shop_products")
    shop_products = cur.fetchall()

    cur.execute("""
        SELECT 
            orders.id AS order_id,
            orders.title,
            orders.total_cost,
            orders.quantity,
            orders.unit,
            orders.status,
            orders.order_date,
            users.username,
            users.email,
            users.mobile,
            users.address_line,
            users.city,
            users.state,
            users.pincode
        FROM orders
        JOIN users ON orders.user_id = users.id
    """)
    orders = cur.fetchall()

    conn.close()

    return render_template('admin.html',
                           orders=orders,
                           categories=categories,
                           products=products,
                           shop_products=shop_products,
                           product_details=product_details)

@app.route("/get_user_info", methods=["GET"])
def get_user_info():
    user_id = session.get("user_id")
    print("Session user_id:", user_id)  # 🔍 DEBUG

    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = psycopg2.connect(
            host="aws-0-ap-south-1.pooler.supabase.com",
            database="postgres",
            user="postgres.xapwrudbiysziedhrvcd",
            password="Kodesh@12",
            port="5432"
        )
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT username AS name, address_line AS address FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()

        print("Fetched user:", user)  # 🔍 DEBUG

        cur.close()
        conn.close()

        if user:
            return jsonify(user)
        else:
            return jsonify({"error": "User not found"}), 404

    except Exception as e:
        print("DB error:", e)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/admin/analytics_data')
def analytics_data():
    print("🔍 [INFO] Request received for /admin/analytics_data")

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get sales per product
    cur.execute("""
        SELECT title, SUM(quantity) AS quantity, SUM(total_cost) AS total_sales
        FROM orders
        GROUP BY title
        ORDER BY total_sales DESC
    """)
    sales_per_product = cur.fetchall()
    print("📦 [DATA] Sales per product:", sales_per_product)

    # Get sales over time (grouped by date)
    cur.execute("""
        SELECT TO_CHAR(order_date, 'YYYY-MM-DD') AS date, SUM(total_cost) AS total
        FROM orders
        GROUP BY date
        ORDER BY date
    """)
    sales_over_time = cur.fetchall()
    print("📈 [DATA] Sales over time:", sales_over_time)

    # Get profit by category (JOIN with products table)
    cur.execute("""
        SELECT p.category, SUM(o.total_cost) AS total_profit
        FROM orders o
        JOIN products p ON o.title = p.title
        GROUP BY p.category
        ORDER BY total_profit DESC
    """)
    profit_by_category = cur.fetchall()
    print("📊 [DATA] Profit by category:", profit_by_category)

    conn.close()
    print("✅ [INFO] Database connection closed.")

    response_data = {
        'sales_per_product': sales_per_product,
        'sales_over_time': sales_over_time,
        'profit_by_category': profit_by_category
    }

    print("📤 [RESPONSE] Sending JSON data:", response_data)
    return jsonify(response_data)


@app.route("/update_order_status/<int:order_id>", methods=["POST"])
def update_order_status(order_id):
    if 'user_id' not in session:
        print("🚫 Unauthorized: No user_id in session.")
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session['user_id']
    data = request.get_json()
    print(f"🔄 Received request to update order {order_id} by user {user_id} with data: {data}")

    new_status = data.get("status")
    if new_status not in ["Pending", "Shipped", "Delivered"]:
        print(f"⚠️ Invalid status: {new_status}")
        return jsonify({"error": "Invalid status"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Optional: Check if the order exists
        cursor.execute("SELECT id FROM orders WHERE id = %s", (order_id,))
        if not cursor.fetchone():
            print(f"❌ Order {order_id} not found.")
            return jsonify({"error": "Order not found"}), 404

        cursor.execute("UPDATE orders SET status = %s WHERE id = %s", (new_status, order_id))
        conn.commit()
        cursor.close()
        conn.close()
        print(f"✅ Order {order_id} status updated to {new_status}")
        return jsonify({"message": "Status updated successfully"})
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        return jsonify({"error": str(e)}), 500


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
@app.route("/contact")
def contact():
    user_data = None

    if 'user_id' in session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE id = %s", (session['user_id'],))
        user_data = cur.fetchone()
        conn.close()
        
    return render_template("contact.html",user=user_data)
################################################# Payment 

if __name__ == '__main__':
    app.run(debug=True)
    
# from flask import Flask, render_template, request ,session, redirect, url_for ,flash
# import sqlite3
# app = Flask(__name__, template_folder='./templates', static_folder='static')
# DATABASE = 'shop_data.db'
# app.secret_key = 'Kodesh@12'

# def get_db_connection():
#     conn = sqlite3.connect(DATABASE)
#     conn.row_factory = sqlite3.Row  # Enables dict-like access
#     return conn

# @app.route('/set-language', methods=['POST'])
# def set_language():
#     selected_language = request.form.get('language', 'en')
#     session['lang'] = selected_language
#     return redirect(request.referrer or url_for('index'))
# @app.route('/')
# def index():
#     conn = get_db_connection()
#     categories = conn.execute("SELECT * FROM categories").fetchall()
#     products = conn.execute("SELECT * FROM shop_products").fetchall()
#     conn.close()
#     lang = session.get('lang', 'en')
#     # Debug: Print all categories
#     print("\n[DEBUG] Categories from DB:")
#     for category in categories:
#         print(dict(category))

#     # Debug: Print all products
#     print("\n[DEBUG] Products from DB:")
#     for product in products:
#         print(dict(product))

#     tags = sorted(set(p['tags'].lower() for p in products if p['tags']))

#     return render_template("index.html", categories=categories, products=products, tags=tags ,lang=lang)

# from flask_mail import Mail, Message
# app.config['MAIL_SERVER'] = 'smtp.gmail.com'
# app.config['MAIL_PORT'] = 587
# app.config['MAIL_USERNAME'] = 'mjanokodesh@gmail.com'
# app.config['MAIL_PASSWORD'] = 'gngn wxai cvyq emjq'
# app.config['MAIL_USE_TLS'] = True
# app.config['MAIL_USE_SSL'] = False

# mail = Mail(app)

# @app.route("/contact")
# def contact():
#     return render_template("contact.html")

# @app.route("/send-message", methods=["POST"])
# def send_message():
#     name = request.form["name"]
#     email = request.form["email"]
#     message = request.form["message"]
#     msg = Message(
#         subject=f"New Contact Message from {name}",
#         sender=email,
#         recipients=["mjanokodesh@gmail.com"],
#         body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
#     )
#     mail.send(msg)
#     flash("success")
#     return redirect("/contact")




# @app.route('/shop')
# def shop():
#     category_filter = request.args.get('category')
#     conn = get_db_connection()
#     shop_products = conn.execute("SELECT * FROM shop_products").fetchall()
#     conn.close()

#     # Debug: Print all shop products
#     print("\n[DEBUG] Shop Products from DB:")
#     lang = session.get('lang', 'en')
#     for sp in shop_products:
#         print(dict(sp))

#     if category_filter:
#         category_filter = category_filter.strip().lower()
#         filtered_products = [p for p in shop_products if p['category'].strip().lower() == category_filter]
        
#         # Debug: Filtered shop products
#         print(f"\n[DEBUG] Filtered Shop Products for category '{category_filter}':")
#         for fp in filtered_products:
#             print(dict(fp))

#         return render_template("shop.html", shop_products=filtered_products ,lang=lang)
    
#     return render_template("shop.html", shop_products=shop_products ,lang=lang)

# @app.route('/cart')
# def cart():
#     lang = session.get('lang', 'en')

#     return render_template("cart.html",lang=lang)
# @app.route('/story')
# def story():
#     lang = session.get('lang', 'en')

#     return render_template("about.html",lang=lang)

# @app.route('/checkout')
# def checkout():
#     return render_template("checkout.html")

# @app.route('/details/<int:product_id>')
# def details(product_id):
#     conn = get_db_connection()  

#     # Get current product
#     product = conn.execute("SELECT * FROM shop_products WHERE id = ?", (product_id,)).fetchone()
#     print("\n🔎 Shop Product Data Retrieved:")
#     lang = session.get('lang', 'en')
#     if product:
#         print(dict(product))
#     else:
#         print("❌ No product found with ID:", product_id)
#         conn.close()
#         return "Product not found", 404

#     # Get product details
#     product_details = conn.execute("SELECT * FROM product_details WHERE product_id = ?", (product_id,)).fetchone()
#     print("\n📦 Product Details Data Retrieved:")
#     if product_details:
#         print(dict(product_details))
#     else:
#         print("⚠️ No product details found for ID:", product_id)

#     # Convert product to dict and attach additional details
#     product_dict = dict(product)
#     if product_details:
#         product_dict["ingredients"] = product_details["ingredients"]
#         product_dict["health_benefits"] = product_details["health_benefits"]
#     else:
#         product_dict["ingredients"] = "No ingredients listed."
#         product_dict["health_benefits"] = "No health benefits listed."

#     # ✅ Fetch related products (same category, excluding current)
#     related_products = conn.execute(
#         "SELECT * FROM shop_products WHERE category = ? AND id != ? LIMIT 4",
#         (product["category"], product_id)
#     ).fetchall()

#     print("\n🔗 Related Products Retrieved:")
#     for rp in related_products:
#         print(dict(rp))
#     conn.close()
#     return render_template("details.html", product=product_dict, related_products=related_products,lang=lang)
# ADMIN_USERNAME = "admin"
# ADMIN_PASSWORD = "password123"

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
#             session['admin_logged_in'] = True
#             return redirect(url_for('admin'))
#         else:
#             flash('Invalid credentials', 'error')
#     return render_template('login.html')

# @app.route('/admin')
# def admin():
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     conn = get_db_connection()
#     categories = conn.execute("SELECT * FROM categories").fetchall()
#     products = conn.execute("SELECT * FROM products").fetchall()
#     product_details = conn.execute("SELECT * FROM product_details").fetchall()
#     shop_products = conn.execute("SELECT * FROM shop_products").fetchall()
#     for sp in shop_products:
#         print(dict(sp))
#     conn.close()
#     return render_template('admin.html', categories=categories, products=products,
#                            shop_products=shop_products, product_details=product_details)
# @app.route('/logout')
# def logout():
#     session.pop('admin_logged_in', None)
#     return redirect(url_for('login'))

# # ----- Categories -----
# import os
# from werkzeug.utils import secure_filename

# UPLOAD_FOLDER = os.path.join('static', 'assets', 'img')
# ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# @app.route('/admin/add/category', methods=['GET', 'POST'])
# def add_category():
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     if request.method == 'POST':
#         name = request.form['name']
#         image = request.files['image']

#         if image and allowed_file(image.filename):
#             filename = secure_filename(image.filename)
#             save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#             image.save(save_path)

#             # Only save filename to DB
#             conn = get_db_connection()
#             conn.execute("INSERT INTO categories (name, image_url) VALUES (?, ?)", (name, filename))
#             conn.commit()
#             conn.close()

#             return redirect(url_for('admin'))
#         else:
#             return "Invalid file type", 400
#     return render_template('add_category.html')


# import os
# from werkzeug.utils import secure_filename

# @app.route('/admin/edit/category/<name>', methods=['GET', 'POST'])
# def edit_category(name):
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     conn = get_db_connection()
#     category = conn.execute("SELECT * FROM categories WHERE name = ?", (name,)).fetchone()

#     if request.method == 'POST':
#         new_name = request.form['name']
#         image_file = request.files.get('image')

#         # Use existing image if no new one is uploaded
#         image_filename = category['image_url']

#         if image_file and image_file.filename != '':
#             image_filename = secure_filename(image_file.filename)
#             image_path = os.path.join('static/assets/img', image_filename)
#             image_file.save(image_path)

#         conn.execute("UPDATE categories SET name = ?, image_url = ? WHERE name = ?",
#                      (new_name, image_filename, name))
#         conn.commit()
#         conn.close()
#         return redirect(url_for('admin'))

#     conn.close()
#     return render_template('edit_category.html', category=category)

# @app.route('/admin/delete/category/<name>')
# def delete_category(name):
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     conn = get_db_connection()
#     conn.execute("DELETE FROM categories WHERE name = ?", (name,))
#     conn.commit()
#     conn.close()
#     return redirect(url_for('admin'))


# # ----- Shop Products -----
# import os
# from werkzeug.utils import secure_filename

# UPLOAD_FOLDER = 'static/assets/img/'
# ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# @app.route('/admin/add/shop_product', methods=['GET', 'POST'])
# def add_shop_product():
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     if request.method == 'POST':
#         title = request.form['title']
#         category = request.form['category']
#         new_price = request.form['new_price']
#         old_price = request.form['old_price']
#         badge = request.form['badge']
#         badge_class = request.form['badge_class']
#         description = request.form['description']
#         brand = request.form['brand']
#         # sku = request.form['sku']
#         sku = 'Null'
#         tags = request.form['tags']
#         stock_kg = request.form['stock_kg']

#         # Handle image uploads
#         img_default = request.files['img_default']
#         img_hover = request.files['img_hover']

#         if img_default and allowed_file(img_default.filename):
#             filename_default = secure_filename(img_default.filename)
#             img_default.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_default))
#         else:
#             filename_default = ""

#         if img_hover and allowed_file(img_hover.filename):
#             filename_hover = secure_filename(img_hover.filename)
#             img_hover.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_hover))
#         else:
#             filename_hover = ""

#         conn = get_db_connection()
#         conn.execute("""
#             INSERT INTO shop_products (title, category, img_default, img_hover, new_price, old_price, badge, badge_class, description, brand,sku, tags, stock_kg)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """, (
#             title, category,
#             f"assets/img/{filename_default}",
#             f"assets/img/{filename_hover}",
#             new_price, old_price,
#             badge, badge_class,
#             description, brand, sku, tags, stock_kg
#         ))
#         conn.commit()
#         conn.close()
#         return redirect(url_for('admin'))
    
#     return render_template('add_shop_product.html')

# @app.route('/admin/edit/shop_product/<int:id>', methods=['GET', 'POST'])
# def edit_shop_product(id):
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     conn = get_db_connection()
#     sp = conn.execute("SELECT * FROM shop_products WHERE id = ?", (id,)).fetchone()

#     if request.method == 'POST':
#         title = request.form['title']
#         category = request.form['category']
#         new_price = request.form['new_price']
#         old_price = request.form['old_price']
#         badge = request.form['badge']
#         badge_class = request.form['badge_class']
#         description = request.form['description']
#         brand = request.form['brand']
#         sku = 'Null'
#         tags = request.form['tags']
#         stock_kg = request.form['stock_kg']

#         img_default = request.files.get('img_default')
#         img_hover = request.files.get('img_hover')

#         img_default_path = sp['img_default']
#         img_hover_path = sp['img_hover']

#         if img_default and img_default.filename != '':
#             filename_default = secure_filename(img_default.filename)
#             img_default.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_default))
#             img_default_path = f"assets/img/{filename_default}"

#         if img_hover and img_hover.filename != '':
#             filename_hover = secure_filename(img_hover.filename)
#             img_hover.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_hover))
#             img_hover_path = f"assets/img/{filename_hover}"

#         conn.execute("""
#             UPDATE shop_products SET 
#               title=?, category=?, img_default=?, img_hover=?, new_price=?, old_price=?, 
#               badge=?, badge_class=?, description=?, brand=?, sku=?, tags=?, stock_kg=?
#             WHERE id=?
#         """, (
#             title, category, img_default_path, img_hover_path, new_price, old_price,
#             badge, badge_class, description, brand, sku, tags, stock_kg, id
#         ))

#         conn.commit()
#         conn.close()
#         return redirect(url_for('admin'))

#     conn.close()
#     return render_template('edit_shop_product.html', sp=sp)


# @app.route('/admin/delete/shop_product/<int:id>')
# def delete_shop_product(id):
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     conn = get_db_connection()
#     conn.execute("DELETE FROM shop_products WHERE id = ?", (id,))
#     conn.commit()
#     conn.close()
#     return redirect(url_for('admin'))

# # ----- Product Details -----
# @app.route('/admin/add/product_detail', methods=['GET', 'POST'])
# def add_product_detail():
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     if request.method == 'POST':
#         product_id = request.form['product_id']
#         ingredients = request.form['ingredients']
#         health_benefits = request.form['health_benefits']
#         conn = get_db_connection()
#         conn.execute("INSERT INTO product_details (product_id, ingredients, health_benefits) VALUES (?, ?, ?)",
#                      (product_id, ingredients, health_benefits))
#         conn.commit()
#         conn.close()
#         return redirect(url_for('admin'))
#     return render_template('add_product_detail.html')

# @app.route('/admin/edit/product_detail/<int:product_id>', methods=['GET', 'POST'])
# def edit_product_detail(product_id):
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     conn = get_db_connection()
#     detail = conn.execute("SELECT * FROM product_details WHERE product_id = ?", (product_id,)).fetchone()
#     if request.method == 'POST':
#         ingredients = request.form['ingredients']
#         health_benefits = request.form['health_benefits']
#         conn.execute("""UPDATE product_details SET ingredients=?, health_benefits=? WHERE product_id=?""",
#                      (ingredients, health_benefits, product_id))
#         conn.commit()
#         conn.close()
#         return redirect(url_for('admin'))
#     conn.close()
#     return render_template('edit_product_detail.html', detail=detail)

# @app.route('/admin/delete/product_detail/<int:product_id>')
# def delete_product_detail(product_id):
#     if not session.get('admin_logged_in'):
#         return redirect(url_for('login'))

#     conn = get_db_connection()
#     conn.execute("DELETE FROM product_details WHERE product_id = ?", (product_id,))
#     conn.commit()
#     conn.close()
#     return redirect(url_for('admin'))

# if __name__ == '__main__':
#     app.run(debug=True)
