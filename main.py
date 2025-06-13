from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request as StarletteRequest
import psycopg2
from psycopg2.extras import RealDictCursor
import psycopg2.extras
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from werkzeug.utils import secure_filename
import bcrypt
from datetime import datetime
import random
import json
import os
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import shutil

# Initialize FastAPI app
app = FastAPI(title="Shop Application", version="1.0.0")

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key="Kodesh@12")

# Mount static files

app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")  # not "/templates"

# Database Configuration
DB_USER = "postgres.xapwrudbiysziedhrvcd"
DB_PASSWORD = "Kodesh@12"
DB_HOST = "aws-0-ap-south-1.pooler.supabase.com"
DB_PORT = "5432"
DB_NAME = "postgres"

# Upload Configuration
UPLOAD_FOLDER = os.path.join('static', 'assets', 'img')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Admin Configuration
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

# Email Configuration
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USERNAME = 'mjanokodesh@gmail.com'
MAIL_PASSWORD = 'gngn wxai cvyq emjq'

# Pydantic Models
class UserRegister(BaseModel):
    username: str
    email: str
    mobile: str
    password: str
    confirm_password: str
    address_line: str
    city: str
    state: str
    pincode: str

class UserLogin(BaseModel):
    email: str
    password: str

class OrderItem(BaseModel):
    title: str
    quantity: float
    unit: str
    price: float

class BulkOrder(BaseModel):
    cart: List[OrderItem]

class ContactMessage(BaseModel):
    name: str
    email: str
    message: str

class ProfileUpdate(BaseModel):
    username: str
    mobile: str

class AddressUpdate(BaseModel):
    address_line: str
    city: str
    state: str
    pincode: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class OrderStatusUpdate(BaseModel):
    status: str

# Utility Functions
def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
@app.get("/test-static")
def test_static():
    return {
        "static_url": "/static/assets/img/icon.png"
    }
def get_db_connection():
    return psycopg2.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        cursor_factory=RealDictCursor
    )

def send_email_otp(email: str, otp: str):
    try:
        msg = MIMEMultipart()
        msg['From'] = MAIL_USERNAME
        msg['To'] = email
        msg['Subject'] = 'Your OTP Verification Code'
        
        body = f"Your OTP is: {otp}"
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
        server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(MAIL_USERNAME, email, text)
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")

def send_contact_email(name: str, email: str, message: str):
    try:
        msg = MIMEMultipart()
        msg['From'] = email
        msg['To'] = MAIL_USERNAME
        msg['Subject'] = f"New Contact Message from {name}"
        
        body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
        server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(MAIL_USERNAME, MAIL_USERNAME, text)
        server.quit()
    except Exception as e:
        print(f"Failed to send contact email: {e}")

def require_login(request: Request):
    if 'user_id' not in request.session:
        raise HTTPException(status_code=401, detail="Authentication required")
    return request.session.get('user_id')

def require_admin(request: Request):
    if not request.session.get('admin_logged_in'):
        raise HTTPException(status_code=401, detail="Admin authentication required")
    return True

# Test database connection
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

# Routes

@app.post("/set-language")
async def set_language(request: Request, language: str = Form(default='en')):
    request.session['lang'] = language
    return RedirectResponse(url=request.headers.get('referer', '/'), status_code=302)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch categories and products
    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()

    cur.execute("SELECT * FROM shop_products")
    products = cur.fetchall()

    # Fetch user info if logged in
    user_data = None
    if 'user_id' in request.session:
        cur.execute("SELECT username FROM users WHERE id = %s", (request.session['user_id'],))
        user_data = cur.fetchone()

    conn.close()

    lang = request.session.get('lang', 'en')
    tags = sorted(set(p['tags'].lower() for p in products if p['tags']))

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "categories": categories,
            "products": products,
            "tags": tags,
            "lang": lang,
            "user": user_data
        }
    )

# Authentication Routes

@app.post("/verify-otp")
async def verify_otp(request: Request, otp: str = Form(...)):
    temp_user = request.session.get("temp_user")

    if not temp_user or otp != temp_user['otp']:
        return JSONResponse({'status': 'error', 'message': 'Invalid OTP'})

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
        request.session.pop('temp_user', None)
        return JSONResponse({'status': 'success'})
    except Exception as e:
        return JSONResponse({'status': 'error', 'message': str(e)})
    finally:
        cur.close()
        conn.close()

@app.get("/user_login", response_class=HTMLResponse)
async def user_login(request: Request):
    if 'user_id' in request.session:
        return RedirectResponse(url="/account", status_code=302)
    return templates.TemplateResponse("login-register.html", {"request": request})

@app.post("/register")
async def register_user(request: Request, user_data: UserRegister):
    if user_data.password != user_data.confirm_password:
        return JSONResponse({'status': 'error', 'message': 'Passwords do not match.'})

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email=%s OR mobile=%s", (user_data.email, user_data.mobile))
    if cur.fetchone():
        return JSONResponse({'status': 'error', 'message': 'Email or Mobile already registered.'})

    otp = str(random.randint(100000, 999999))
    send_email_otp(user_data.email, otp)

    request.session['temp_user'] = {
        'username': user_data.username,
        'email': user_data.email,
        'mobile': user_data.mobile,
        'password': bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        'address_line': user_data.address_line,
        'city': user_data.city,
        'state': user_data.state,
        'pincode': user_data.pincode,
        'otp': otp
    }

    cur.close()
    conn.close()
    return JSONResponse({'status': 'otp_sent'})

@app.post("/user_login_post")
async def user_login_post(request: Request, email: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        print("Fetched user:", user)

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            request.session['user_id'] = user['id']
            request.session['username'] = user['username']
            return RedirectResponse(url="/account", status_code=302)
        else:
            return RedirectResponse(url="/user_login?error=invalid_credentials", status_code=302)
    except Exception as e:
        print("Login error:", str(e))
        return RedirectResponse(url="/user_login?error=login_failed", status_code=302)
    finally:
        cur.close()
        conn.close()

@app.get("/user_logout")
async def user_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/user_login", status_code=302)

# Order Routes

@app.post('/place_order')
async def place_order(request: Request, order_data: OrderItem):
    user_id = require_login(request)

    try:
        total_cost = order_data.price * (order_data.quantity / 1000 if order_data.unit == "g" else order_data.quantity)

        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO orders (user_id, order_date, title, quantity, unit, total_cost, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, datetime.now(), order_data.title, order_data.quantity, order_data.unit, total_cost, 'Pending'))

        print("🛒 Order Data to Insert:")
        print(f"User ID: {user_id}")
        print(f"Title: {order_data.title}")
        print(f"Quantity: {order_data.quantity} {order_data.unit}")
        print(f"Price per Unit: ₹{order_data.price}")
        print(f"Total Cost: ₹{total_cost:.2f}")
        print("Status: Pending")
        
        conn.commit()
        cur.close()
        conn.close()
        return JSONResponse({'status': 'success', 'message': 'Order placed successfully'})

    except Exception as e:
        return JSONResponse({'status': 'error', 'message': str(e)})

@app.post('/place_order_bulk')
async def place_order_bulk(request: Request, bulk_order: BulkOrder):
    user_id = require_login(request)

    try:
        if not bulk_order.cart:
            return JSONResponse({'status': 'error', 'message': 'Cart is empty'})

        conn = get_db_connection()
        cur = conn.cursor()

        for item in bulk_order.cart:
            quantity = float(item.quantity)
            unit = item.unit.lower()
            price = float(item.price)

            # Calculate total cost
            if unit in ["g", "gram", "grams", "kg", "kilogram", "kilograms"]:
                total_cost = price * (quantity / 1000)
            elif unit in ["ml", "millilitre", "millilitres", "litre", "litres"]:
                total_cost = price * (quantity / 1000)
            elif unit in ["pcs", "pieces", "unit", "shirt", "pants", "item"]:
                total_cost = price * quantity
            else:
                total_cost = price * quantity  # fallback

            cur.execute("""
                INSERT INTO orders (user_id, order_date, title, total_cost, status, quantity, unit)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, datetime.now(), item.title, round(total_cost, 2), 'Pending', quantity, unit))

            print(f"🧾 Title: {item.title}, Qty: {quantity}{unit}, ₹{price}, Total: ₹{round(total_cost, 2)}")

        conn.commit()
        cur.close()
        conn.close()

        return JSONResponse({'status': 'success', 'message': 'All items ordered successfully'})
    except Exception as e:
        return JSONResponse({'status': 'error', 'message': str(e)})

# Account Management Routes

@app.get("/account", response_class=HTMLResponse)
async def account(request: Request):
    user_id = require_login(request)

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

    return templates.TemplateResponse(
        "accounts.html", 
        {
            "request": request,
            "orders": user_orders,
            "user": user_data,
            "username": user_data["username"]
        }
    )

@app.post("/cancel-order/{order_id}")
async def cancel_order(request: Request, order_id: int):
    user_id = require_login(request)
    
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Ensure user owns the order
        cur.execute("SELECT id FROM orders WHERE id = %s AND user_id = %s", (order_id, user_id))
        if not cur.fetchone():
            return JSONResponse({'status': 'error', 'message': 'Order not found or not yours'})

        # Delete the order
        cur.execute("DELETE FROM orders WHERE id = %s AND user_id = %s", (order_id, user_id))
        conn.commit()

        return JSONResponse({'status': 'success', 'message': 'Order cancelled successfully'})

    except Exception as e:
        print("❌ Error cancelling order:", str(e))
        return JSONResponse({'status': 'error', 'message': 'Failed to cancel order'})

    finally:
        cur.close()
        conn.close()

@app.post("/update-profile")
async def update_profile(request: Request, username: str = Form(...), mobile: str = Form(...)):
    user_id = require_login(request)

    # Validate input
    if not username or not mobile:
        raise HTTPException(status_code=400, detail="Invalid input")

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

    # Update session
    request.session['username'] = username

    return RedirectResponse(url="/account", status_code=302)

@app.post("/update-address")
async def update_address(
    request: Request,
    address_line: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    pincode: str = Form(...)
):
    user_id = require_login(request)

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

    return RedirectResponse(url="/account", status_code=302)

@app.post("/change-password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    user_id = require_login(request)

    print("📥 Got:")
    print("Current Password:", current_password)
    print("New Password:", new_password)
    print("Confirm Password:", confirm_password)

    if new_password != confirm_password:
        return JSONResponse({'status': 'error', 'message': 'New passwords do not match'})

    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT password FROM users WHERE id = %s", (user_id,))
        result = cur.fetchone()
        if not result:
            return JSONResponse({'status': 'error', 'message': 'User not found'})

        hashed_password = result['password']
        print("🔐 Stored hashed password (from DB):", hashed_password)

        if not bcrypt.checkpw(current_password.encode(), hashed_password.encode()):
            print("❌ Password check failed")
            return JSONResponse({'status': 'error', 'message': 'Current password is incorrect'})

        print("✅ Password check passed")

        # Hash the new password
        new_hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        print("📤 New Hashed Password to store:", new_hashed)

        # Update in DB
        cur.execute("UPDATE users SET password = %s WHERE id = %s", (new_hashed, user_id))
        conn.commit()

        return JSONResponse({'status': 'success', 'message': 'Password updated successfully'})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({'status': 'error', 'message': f'Exception: {str(e)}'})

    finally:
        cur.close()
        conn.close()

# Contact Route

@app.post("/send-message")
async def send_message(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...)
):
    send_contact_email(name, email, message)
    return RedirectResponse(url="/contact?success=true", status_code=302)

# Shop Routes

@app.get('/shop', response_class=HTMLResponse)
async def shop(request: Request, category: Optional[str] = None):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM shop_products")
    shop_products = cur.fetchall()
    conn.close()

    lang = request.session.get('lang', 'en')
    user_data = None
    
    if 'user_id' in request.session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE id = %s", (request.session['user_id'],))
        user_data = cur.fetchone()
        conn.close()

    print("\n[DEBUG] Shop Products from DB:")
    for sp in shop_products:
        print(dict(sp))

    if category:
        category_filter = category.strip().lower()
        filtered_products = [p for p in shop_products if p['category'].strip().lower() == category_filter]

        print(f"\n[DEBUG] Filtered Shop Products for category '{category_filter}':")
        for fp in filtered_products:
            print(dict(fp))

        return templates.TemplateResponse(
            "shop.html",
            {
                "request": request,
                "shop_products": filtered_products,
                "lang": lang,
                "user": user_data
            }
        )

    return templates.TemplateResponse(
        "shop.html",
        {
            "request": request,
            "shop_products": shop_products,
            "lang": lang,
            "user": user_data
        }
    )

@app.get('/cart', response_class=HTMLResponse)
async def cart(request: Request):
    lang = request.session.get('lang', 'en')
    user_data = None

    if 'user_id' in request.session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE id = %s", (request.session['user_id'],))
        user_data = cur.fetchone()
        conn.close()
        
    return templates.TemplateResponse(
        "cart.html",
        {
            "request": request,
            "lang": lang,
            "user": user_data
        }
    )

@app.get('/story', response_class=HTMLResponse)
async def story(request: Request):
    lang = request.session.get('lang', 'en')
    user_data = None

    if 'user_id' in request.session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE id = %s", (request.session['user_id'],))
        user_data = cur.fetchone()
        conn.close()
        
    return templates.TemplateResponse(
        "about.html",
        {
            "request": request,
            "lang": lang,
            "user": user_data
        }
    )

@app.get('/checkout', response_class=HTMLResponse)
async def checkout(request: Request):
    return templates.TemplateResponse("checkout.html", {"request": request})

@app.get('/details/{product_id}', response_class=HTMLResponse)
async def details(request: Request, product_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get product
    cur.execute("SELECT * FROM shop_products WHERE id = %s", (product_id,))
    product = cur.fetchone()

    if not product:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")

    # Get language
    lang = request.session.get('lang', 'en')

    # Get user (optional)
    user_data = None
    if 'user_id' in request.session:
        user_cur = conn.cursor()
        user_cur.execute("SELECT username FROM users WHERE id = %s", (request.session['user_id'],))
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

    return templates.TemplateResponse(
        "details.html",
        {
            "request": request,
            "product": product_dict,
            "related_products": related_products,
            "lang": lang,
            "user": user_data
        }
    )

@app.get('/contact', response_class=HTMLResponse)
async def contact(request: Request):
    user_data = None

    if 'user_id' in request.session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE id = %s", (request.session['user_id'],))
        user_data = cur.fetchone()
        conn.close()
        
    return templates.TemplateResponse(
        "contact.html",
        {
            "request": request,
            "user": user_data
        }
    )

# Admin Routes

@app.get('/login', response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse('login.html', {"request": request})

@app.post('/login')
async def admin_login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        request.session['admin_logged_in'] = True
        return RedirectResponse(url='/admin', status_code=302)
    else:
        return RedirectResponse(url='/login?error=invalid_credentials', status_code=302)

@app.get('/admin/products', response_class=HTMLResponse)
async def admin_products(request: Request):
    require_admin(request)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()
    
    cur.execute("SELECT * FROM shop_products")
    shop_products = cur.fetchall()
    
    cur.execute("SELECT * FROM product_details")
    product_details = cur.fetchall()
    
    conn.close()
    
    return templates.TemplateResponse(
        'admin_products.html',
        {
            "request": request,
            "categories": categories,
            "shop_products": shop_products,
            "product_details": product_details
        }
    )

@app.get('/admin', response_class=HTMLResponse)
async def admin(request: Request):
    require_admin(request)

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

    return templates.TemplateResponse(
        'admin.html',
        {
            "request": request,
            "orders": orders,
            "categories": categories,
            "products": products,
            "shop_products": shop_products,
            "product_details": product_details
        }
    )

# @app.get('/admin/analytics_data')
# async def analytics_data(request: Request):
#     require_admin(request)
    
#     print("🔍 [INFO] Request received for /admin/analytics_data")

#     conn = get_db_connection()
#     cur = conn.cursor(cursor_factory=RealDictCursor)

#     # Get sales per product
#     cur.execute("""
#         SELECT title, SUM(quantity) AS quantity, SUM(total_cost) AS total_sales
#         FROM orders
#         GROUP BY title
#         ORDER BY total_sales DESC
#     """)
#     sales_per_product = cur.fetchall()
#     print("📦 [DATA] Sales per product:", sales_per_product)

#     # Get sales over time (grouped by date)
#     cur.execute("""
#         SELECT TO_CHAR(order_date, 'YYYY-MM-DD') AS date, SUM(total_cost) AS total
#         FROM orders
#         GROUP BY date
#         ORDER BY date
#     """)
#     sales_over_time = cur.fetchall()
#     print("📈 [DATA] Sales over time:", sales_over_time)

#     # Get profit by category (JOIN with products table)
#     cur.execute("""
#         SELECT p.category, SUM(o.total_cost) AS total_profit
#         FROM orders o

# Run using uvicorn if this script is run directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)