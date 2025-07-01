from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import psycopg2
from psycopg2.extras import RealDictCursor
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime
import os
import random
from typing import Optional, List, Dict
from pydantic import BaseModel
import hashlib  # Using hashlib as a fallback for password hashing

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure templates
templates = Jinja2Templates(directory="templates")

# Session middleware
app.add_middleware(SessionMiddleware, secret_key="Kodesh@12")


# Password hashing context
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Custom flash message implementation
class FlashMessage(BaseModel):
    message: str
    category: str = "message"

async def set_flash(request: Request, message: str, category: str = "message"):
    if "_flash_messages" not in request.session:
        request.session["_flash_messages"] = []
    request.session["_flash_messages"].append({"message": message, "category": category})

async def get_flashed_messages(request: Request) -> List[Dict[str, str]]:
    return request.session.pop("_flash_messages", [])

# Database configuration
DB_USER = "postgres.xapwrudbiysziedhrvcd"
DB_PASSWORD = "Kodesh@12"
DB_HOST = "aws-0-ap-south-1.pooler.supabase.com"
DB_PORT = "5432"
DB_NAME = "postgres"

UPLOAD_FOLDER = os.path.join('static', 'assets', 'img')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    return psycopg2.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        cursor_factory=RealDictCursor
    )

# Email configuration (placeholder - you'll need to implement this)
class Mail:
    def __init__(self):
        pass
    
    def send(self, message):
        print(f"Email would be sent to {message['recipients']} with subject {message['subject']}")
        # Implement actual email sending here

mail = Mail()

# Models
class Message(BaseModel):
    subject: str
    sender: str
    recipients: list[str]
    body: str

# Helper functions
async def flash(request: Request, message: str, category: str = "message"):
    request.session.setdefault("_flashes", []).append({"message": message, "category": category})

async def get_flashed_messages(request: Request):
    return request.session.pop("_flashes", [])

# Routes
@app.post("/set-language")
async def set_language(request: Request):
    form_data = await request.form()
    selected_language = form_data.get("language", "en")
    request.session["lang"] = selected_language
    referrer = request.headers.get("referer", "/")
    return RedirectResponse(referrer, status_code=status.HTTP_303_SEE_OTHER)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()

    cur.execute("SELECT * FROM shop_products")
    products = cur.fetchall()

    user_data = None
    if "user_id" in request.session:
        cur.execute("SELECT username FROM users WHERE id = %s", (request.session["user_id"],))
        user_data = cur.fetchone()

    conn.close()

    lang = request.session.get("lang", "en")
    tags = sorted(set(p["tags"].lower() for p in products if p["tags"]))

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

@app.post("/verify-otp")
async def verify_otp(request: Request):
    form_data = await request.form()
    entered_otp = form_data.get("otp")
    temp_user = request.session.get("temp_user")

    if not temp_user or entered_otp != temp_user["otp"]:
        return JSONResponse({"status": "error", "message": "Invalid OTP"})

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO users (username, email, mobile, password, address_line, city, state, pincode)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            temp_user["username"],
            temp_user["email"],
            temp_user["mobile"],
            temp_user["password"],
            temp_user["address_line"],
            temp_user["city"],
            temp_user["state"],
            temp_user["pincode"]
        ))
        conn.commit()
        request.session.pop("temp_user", None)
        return JSONResponse({"status": "success"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})
    finally:
        cur.close()
        conn.close()

@app.get("/user_login", response_class=HTMLResponse)
async def user_login(request: Request):
    if "user_id" in request.session:
        return RedirectResponse("/account", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("login-register.html", {"request": request})

@app.post("/register")
async def register_user(request: Request):
    form_data = await request.form()
    username = form_data["username"]
    email = form_data["email"]
    mobile = form_data["mobile"]
    password = form_data["password"]
    confirm_password = form_data["confirm_password"]
    address_line = form_data["address_line"]
    city = form_data["city"]
    state = form_data["state"]
    pincode = form_data["pincode"]

    if password != confirm_password:
        return JSONResponse({"status": "error", "message": "Passwords do not match."})

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email=%s OR mobile=%s", (email, mobile))
    if cur.fetchone():
        return JSONResponse({"status": "error", "message": "Email or Mobile already registered."})

    otp = str(random.randint(100000, 999999))
    # send_email_otp(email, otp)  # Implement this function

    request.session["temp_user"] = {
        "username": username,
        "email": email,
        "mobile": mobile,
        "password": bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        "address_line": address_line,
        "city": city,
        "state": state,
        "pincode": pincode,
        "otp": otp
    }

    return JSONResponse({"status": "otp_sent"})

@app.post("/user_login_post")
async def user_login_post(request: Request):
    form_data = await request.form()
    email = form_data["email"]
    password = form_data["password"]

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        if user and bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
            request.session["user_id"] = user["id"]
            request.session["username"] = user["username"]
            await flash(request, "Login successful!", "success")
            return RedirectResponse("/account", status_code=status.HTTP_303_SEE_OTHER)
        else:
            await flash(request, "Invalid credentials", "error")
    except Exception as e:
        await flash(request, "Login failed: " + str(e), "error")
    finally:
        cur.close()
        conn.close()

    return RedirectResponse("/user_login", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/user_logout")
async def user_logout(request: Request):
    request.session.clear()
    await flash(request, "You have been logged out.", "success")
    return RedirectResponse("/user_login", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/place_order")
async def place_order(request: Request):
    try:
        user_id = request.session.get("user_id")
        if not user_id:
            return JSONResponse({"status": "redirect", "url": "/user_login"}, status_code=401)

        data = await request.json()
        product_title = data.get("title")
        quantity = int(data.get("quantity"))
        unit = data.get("unit")
        price = float(data.get("price"))

        total_cost = price * (quantity / 1000 if unit == "g" else quantity)

        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO orders (user_id, order_date, title, quantity, unit, total_cost, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, datetime.now(), product_title, quantity, unit, total_cost, "Pending"))

        conn.commit()
        cur.close()
        conn.close()
        return JSONResponse({"status": "success", "message": "Order placed successfully"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/place_order_bulk")
async def place_order_bulk(request: Request):
    try:
        user_id = request.session.get("user_id")
        if not user_id:
            return JSONResponse({"status": "redirect", "url": "/user_login"}, status_code=401)

        data = (await request.json()).get("cart", [])
        if not data:
            return JSONResponse({"status": "error", "message": "Cart is empty"}, status_code=400)

        conn = get_db_connection()
        cur = conn.cursor()

        for item in data:
            title = item.get("title")
            quantity = float(item.get("quantity"))
            unit = item.get("unit", "g").lower()
            price = float(item.get("price"))

            if unit in ["g", "gram", "grams", "kg", "kilogram", "kilograms"]:
                total_cost = price * (quantity / 1000)
            elif unit in ["ml", "millilitre", "millilitres", "litre", "litres"]:
                total_cost = price * (quantity / 1000)
            elif unit in ["pcs", "pieces", "unit", "shirt", "pants", "item"]:
                total_cost = price * quantity
            else:
                total_cost = price * quantity

            cur.execute("""
                INSERT INTO orders (user_id, order_date, title, total_cost, status, quantity, unit)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, datetime.now(), title, round(total_cost, 2), "Pending", quantity, unit))

        conn.commit()
        cur.close()
        conn.close()

        return JSONResponse({"status": "success", "message": "All items ordered successfully"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/account", response_class=HTMLResponse)
async def account(request: Request):
    if "user_id" not in request.session:
        return RedirectResponse("/user_login", status_code=status.HTTP_303_SEE_OTHER)

    user_id = request.session.get("user_id")

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT id, order_date, title, status, total_cost 
        FROM orders 
        WHERE user_id = %s 
        ORDER BY order_date DESC
    """, (user_id,))
    user_orders = cursor.fetchall()

    cursor.execute("""
        SELECT username, email, mobile, address_line, city, state, pincode
        FROM users 
        WHERE id = %s
    """, (user_id,))
    user_data = cursor.fetchone()

    cursor.close()
    conn.close()

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
async def cancel_order(order_id: int, request: Request):
    if "user_id" not in request.session:
        return JSONResponse({"status": "error", "message": "Not logged in"})

    user_id = request.session["user_id"]
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM orders WHERE id = %s AND user_id = %s", (order_id, user_id))
        if not cur.fetchone():
            return JSONResponse({"status": "error", "message": "Order not found or not yours"})

        cur.execute("DELETE FROM orders WHERE id = %s AND user_id = %s", (order_id, user_id))
        conn.commit()
        return JSONResponse({"status": "success", "message": "Order cancelled successfully"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})
    finally:
        cur.close()
        conn.close()

@app.post("/update-profile")
async def update_profile(request: Request):
    if "user_id" not in request.session:
        return RedirectResponse("/user_login", status_code=status.HTTP_303_SEE_OTHER)

    form_data = await request.form()
    user_id = request.session.get("user_id")
    username = form_data.get("username")
    mobile = form_data.get("mobile")

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

    request.session["username"] = username
    return RedirectResponse("/account", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/update-address")
async def update_address(request: Request):
    if "user_id" not in request.session:
        return RedirectResponse("/user_login", status_code=status.HTTP_303_SEE_OTHER)

    form_data = await request.form()
    user_id = request.session.get("user_id")
    address_line = form_data["address_line"]
    city = form_data["city"]
    state = form_data["state"]
    pincode = form_data["pincode"]

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

    return RedirectResponse("/account", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/change-password")
async def change_password(request: Request):
    if "user_id" not in request.session:
        return JSONResponse({"status": "error", "message": "User not logged in"})

    form_data = await request.form()
    current_password = form_data.get("current_password")
    new_password = form_data.get("new_password")
    confirm_password = form_data.get("confirm_password")

    if new_password != confirm_password:
        return JSONResponse({"status": "error", "message": "New passwords do not match"})

    user_id = request.session["user_id"]
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT password FROM users WHERE id = %s", (user_id,))
        result = cur.fetchone()
        if not result:
            return JSONResponse({"status": "error", "message": "User not found"})

        hashed_password = result["password"]

        if not bcrypt.checkpw(current_password.encode(), hashed_password.encode()):
            return JSONResponse({"status": "error", "message": "Current password is incorrect"})

        new_hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        cur.execute("UPDATE users SET password = %s WHERE id = %s", (new_hashed, user_id))
        conn.commit()
        return JSONResponse({"status": "success", "message": "Password updated successfully"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})
    finally:
        cur.close()
        conn.close()

@app.post("/send-message")
async def send_message(request: Request):
    form_data = await request.form()
    name = form_data["name"]
    email = form_data["email"]
    message = form_data["message"]
    
    msg = Message(
        subject=f"New Contact Message from {name}",
        sender=email,
        recipients=["mjanokodesh@gmail.com"],
        body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
    )
    mail.send(msg)
    await flash(request, "success")
    return RedirectResponse("/contact", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/shop", response_class=HTMLResponse)
async def shop(request: Request, category: Optional[str] = None):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM shop_products")
    shop_products = cur.fetchall()
    conn.close()
    
    user_data = None
    lang = request.session.get("lang", "en")
    
    if "user_id" in request.session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE id = %s", (request.session["user_id"],))
        user_data = cur.fetchone()
        conn.close()

    if category:
        category = category.strip().lower()
        filtered_products = [p for p in shop_products if p["category"].strip().lower() == category]
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

@app.get("/cart", response_class=HTMLResponse)
async def cart(request: Request):
    lang = request.session.get("lang", "en")
    user_data = None

    if "user_id" in request.session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE id = %s", (request.session["user_id"],))
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

@app.get("/story", response_class=HTMLResponse)
async def story(request: Request):
    lang = request.session.get("lang", "en")
    user_data = None

    if "user_id" in request.session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE id = %s", (request.session["user_id"],))
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

@app.get("/checkout", response_class=HTMLResponse)
async def checkout(request: Request):
    return templates.TemplateResponse("checkout.html", {"request": request})

@app.get("/details/{product_id}", response_class=HTMLResponse)
async def details(product_id: int, request: Request):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM shop_products WHERE id = %s", (product_id,))
    product = cur.fetchone()

    if not product:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")

    lang = request.session.get("lang", "en")
    user_data = None
    if "user_id" in request.session:
        user_cur = conn.cursor()
        user_cur.execute("SELECT username FROM users WHERE id = %s", (request.session["user_id"],))
        user_data = user_cur.fetchone()
        user_cur.close()

    cur.execute("SELECT * FROM product_details WHERE product_id = %s", (product_id,))
    product_details = cur.fetchone()

    product_dict = dict(product)
    product_dict["ingredients"] = product_details["ingredients"] if product_details else "No ingredients listed."
    product_dict["health_benefits"] = product_details["health_benefits"] if product_details else "No health benefits listed."

    cur.execute("SELECT * FROM shop_products WHERE category = %s AND id != %s LIMIT 4",
                (product["category"], product_id))
    related_products = cur.fetchall()

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

# Admin routes
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

security = HTTPBasic()

async def get_current_admin(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != ADMIN_USERNAME or credentials.password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/admin/products", response_class=HTMLResponse)
async def admin_products(request: Request, admin: str = Depends(get_current_admin)):
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
        "admin_products.html",
        {
            "request": request,
            "categories": categories,
            "shop_products": shop_products,
            "product_details": product_details
        }
    )

@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request, admin: str = Depends(get_current_admin)):
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
        "admin.html",
        {
            "request": request,
            "orders": orders,
            "categories": categories,
            "products": products,
            "shop_products": shop_products,
            "product_details": product_details
        }
    )

@app.get("/admin/analytics_data")
async def analytics_data(admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT title, SUM(quantity) AS quantity, SUM(total_cost) AS total_sales
        FROM orders
        GROUP BY title
        ORDER BY total_sales DESC
    """)
    sales_per_product = cur.fetchall()

    cur.execute("""
        SELECT TO_CHAR(order_date, 'YYYY-MM-DD') AS date, SUM(total_cost) AS total
        FROM orders
        GROUP BY date
        ORDER BY date
    """)
    sales_over_time = cur.fetchall()

    cur.execute("""
        SELECT p.category, SUM(o.total_cost) AS total_profit
        FROM orders o
        JOIN products p ON o.title = p.title
        GROUP BY p.category
        ORDER BY total_profit DESC
    """)
    profit_by_category = cur.fetchall()

    conn.close()

    response_data = {
        'sales_per_product': sales_per_product,
        'sales_over_time': sales_over_time,
        'profit_by_category': profit_by_category
    }

    return response_data

@app.post("/update_order_status/{order_id}")
async def update_order_status(order_id: int, request: Request, admin: str = Depends(get_current_admin)):
    data = await request.json()
    new_status = data.get("status")

    if new_status not in ["Pending", "Shipped", "Delivered"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status = %s WHERE id = %s", (new_status, order_id))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Status updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)

# Admin category routes
@app.get("/admin/add/category", response_class=HTMLResponse)
async def add_category_page(request: Request, admin: str = Depends(get_current_admin)):
    return templates.TemplateResponse("add_category.html", {"request": request})

@app.post("/admin/add/category")
async def add_category(request: Request, admin: str = Depends(get_current_admin)):
    form_data = await request.form()
    name = form_data["name"]
    image = form_data["image"]

    if image and allowed_file(image.filename):
        filename = secure_filename(image.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(save_path, "wb") as buffer:
            buffer.write(await image.read())

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO categories (name, image_url) VALUES (%s, %s)", (name, filename))
        conn.commit()
        cur.close()
        conn.close()

        return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)
    else:
        raise HTTPException(status_code=400, detail="Invalid file type")

@app.get("/admin/edit/category/{name}", response_class=HTMLResponse)
async def edit_category_page(name: str, request: Request, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories WHERE name = %s", (name,))
    category = cur.fetchone()
    cur.close()
    conn.close()
    
    return templates.TemplateResponse(
        "edit_category.html",
        {
            "request": request,
            "category": category
        }
    )

@app.post("/admin/edit/category/{name}")
async def edit_category(name: str, request: Request, admin: str = Depends(get_current_admin)):
    form_data = await request.form()
    new_name = form_data["name"]
    image_file = form_data.get("image")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories WHERE name = %s", (name,))
    category = cur.fetchone()

    image_filename = category["image_url"]

    if image_file and image_file.filename != '':
        image_filename = secure_filename(image_file.filename)
        image_path = os.path.join(UPLOAD_FOLDER, image_filename)
        with open(image_path, "wb") as buffer:
            buffer.write(await image_file.read())

    cur.execute("UPDATE categories SET name = %s, image_url = %s WHERE name = %s",
                (new_name, image_filename, name))
    conn.commit()
    cur.close()
    conn.close()
    
    return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/admin/delete/category/{name}")
async def delete_category(name: str, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM categories WHERE name = %s", (name,))
    conn.commit()
    cur.close()
    conn.close()
    return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)

# Admin shop products routes
@app.get("/admin/add/shop_product", response_class=HTMLResponse)
async def add_shop_product_page(request: Request, admin: str = Depends(get_current_admin)):
    return templates.TemplateResponse("add_shop_product.html", {"request": request})

@app.post("/admin/add/shop_product")
async def add_shop_product(request: Request, admin: str = Depends(get_current_admin)):
    form_data = await request.form()
    title = form_data["title"]
    category = form_data["category"]
    new_price = form_data["new_price"]
    old_price = form_data["old_price"]
    badge = form_data["badge"]
    badge_class = form_data["badge_class"]
    description = form_data["description"]
    brand = form_data["brand"]
    tags = form_data["tags"]
    stock_kg = form_data["stock_kg"]

    img_default = form_data["img_default"]
    img_hover = form_data["img_hover"]

    filename_default = secure_filename(img_default.filename) if img_default and allowed_file(img_default.filename) else ""
    filename_hover = secure_filename(img_hover.filename) if img_hover and allowed_file(img_hover.filename) else ""

    if filename_default:
        with open(os.path.join(UPLOAD_FOLDER, filename_default), "wb") as buffer:
            buffer.write(await img_default.read())
    if filename_hover:
        with open(os.path.join(UPLOAD_FOLDER, filename_hover), "wb") as buffer:
            buffer.write(await img_hover.read())

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO shop_products (title, category, img_default, img_hover, new_price, old_price, badge, badge_class, description, brand, sku, tags, stock_kg)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        title, category, f"assets/img/{filename_default}", f"assets/img/{filename_hover}", new_price, old_price,
        badge, badge_class, description, brand, "Null", tags, stock_kg
    ))
    conn.commit()
    cur.close()
    conn.close()
    
    return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/admin/edit/shop_product/{id}", response_class=HTMLResponse)
async def edit_shop_product_page(id: int, request: Request, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM shop_products WHERE id = %s", (id,))
    sp = cur.fetchone()
    cur.close()
    conn.close()
    
    return templates.TemplateResponse(
        "edit_shop_product.html",
        {
            "request": request,
            "sp": sp
        }
    )

@app.post("/admin/edit/shop_product/{id}")
async def edit_shop_product(id: int, request: Request, admin: str = Depends(get_current_admin)):
    form_data = await request.form()
    title = form_data["title"]
    category = form_data["category"]
    new_price = form_data["new_price"]
    old_price = form_data["old_price"]
    badge = form_data["badge"]
    badge_class = form_data["badge_class"]
    description = form_data["description"]
    brand = form_data["brand"]
    tags = form_data["tags"]
    stock_kg = form_data["stock_kg"]

    img_default = form_data.get("img_default")
    img_hover = form_data.get("img_hover")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM shop_products WHERE id = %s", (id,))
    sp = cur.fetchone()

    img_default_path = sp["img_default"]
    img_hover_path = sp["img_hover"]

    if img_default and img_default.filename:
        filename_default = secure_filename(img_default.filename)
        with open(os.path.join(UPLOAD_FOLDER, filename_default), "wb") as buffer:
            buffer.write(await img_default.read())
        img_default_path = f"assets/img/{filename_default}"

    if img_hover and img_hover.filename:
        filename_hover = secure_filename(img_hover.filename)
        with open(os.path.join(UPLOAD_FOLDER, filename_hover), "wb") as buffer:
            buffer.write(await img_hover.read())
        img_hover_path = f"assets/img/{filename_hover}"

    cur.execute("""
        UPDATE shop_products SET 
            title=%s, category=%s, img_default=%s, img_hover=%s, new_price=%s, old_price=%s, 
            badge=%s, badge_class=%s, description=%s, brand=%s, sku=%s, tags=%s, stock_kg=%s
        WHERE id=%s
    """, (
        title, category, img_default_path, img_hover_path, new_price, old_price,
        badge, badge_class, description, brand, "Null", tags, stock_kg, id
    ))

    conn.commit()
    cur.close()
    conn.close()
    
    return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/admin/delete/shop_product/{id}")
async def delete_shop_product(id: int, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM shop_products WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)

# Admin product details routes
@app.get("/admin/add/product_detail", response_class=HTMLResponse)
async def add_product_detail_page(request: Request, admin: str = Depends(get_current_admin)):
    return templates.TemplateResponse("add_product_detail.html", {"request": request})

@app.post("/admin/add/product_detail")
async def add_product_detail(request: Request, admin: str = Depends(get_current_admin)):
    form_data = await request.form()
    product_id = form_data["product_id"]
    ingredients = form_data["ingredients"]
    health_benefits = form_data["health_benefits"]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO product_details (product_id, ingredients, health_benefits) VALUES (%s, %s, %s)",
                (product_id, ingredients, health_benefits))
    conn.commit()
    cur.close()
    conn.close()
    
    return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/admin/edit/product_detail/{product_id}", response_class=HTMLResponse)
async def edit_product_detail_page(product_id: int, request: Request, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM product_details WHERE product_id = %s", (product_id,))
    detail = cur.fetchone()
    cur.close()
    conn.close()
    
    return templates.TemplateResponse(
        "edit_product_detail.html",
        {
            "request": request,
            "detail": detail
        }
    )

@app.post("/admin/edit/product_detail/{product_id}")
async def edit_product_detail(product_id: int, request: Request, admin: str = Depends(get_current_admin)):
    form_data = await request.form()
    ingredients = form_data["ingredients"]
    health_benefits = form_data["health_benefits"]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE product_details SET ingredients=%s, health_benefits=%s WHERE product_id=%s",
                (ingredients, health_benefits, product_id))
    conn.commit()
    cur.close()
    conn.close()
    
    return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/admin/delete/product_detail/{product_id}")
async def delete_product_detail(product_id: int, admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM product_details WHERE product_id = %s", (product_id,))
    conn.commit()
    cur.close()
    conn.close()
    return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    user_data = None

    if "user_id" in request.session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE id = %s", (request.session["user_id"],))
        user_data = cur.fetchone()
        conn.close()
        
    return templates.TemplateResponse(
        "contact.html",
        {
            "request": request,
            "user": user_data
        }
    )