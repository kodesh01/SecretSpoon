import sqlite3

# Data from Sheets
categories_data = [
    ("Clothing", "category-1.jpg"),
    ("Bags", "category-2.jpg"),
    ("Sandal", "category-3.jpg"),
    ("Scarf Cap", "category-4.jpg"),
    ("Shoes", "category-5.jpg")
]

products_data = [
    (1, "Colorful Pattern Shirt", "Clothing", 238.85, 245.8, "product-1-1.jpg", "product-1-2.jpg", "Hot", "New"),
    (2, "Summer Casual Shirt", "Clothing", 149.99, 199.99, "product-2-1.jpg", "product-2-2.jpg", "-30%", "popular")
]

shop_products_data = [
    ("Colorful Pattern Shirt", "Clothing", "assets/img/product-1-1.jpg", "assets/img/product-1-2.jpg", 238.85, 245.8, "Hot", "light-pink"),
    ("Another Shirt", "Clothing", "assets/img/product-2-1.jpg", "assets/img/product-2-2.jpg", 199, 210, "Hot", "light-green")
]
# Create and connect to the DB
conn = sqlite3.connect("shop_data.db")
cursor = conn.cursor()

# Create tables
cursor.execute('''CREATE TABLE IF NOT EXISTS categories (
    name TEXT,
    image_url TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    title TEXT,
    category TEXT,
    price REAL,
    old_price REAL,
    image1 TEXT,
    image2 TEXT,
    badge TEXT,
    tag TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS shop_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    category TEXT,
    img_default TEXT,
    img_hover TEXT,
    new_price REAL,
    old_price REAL,
    badge TEXT,
    badge_class TEXT,
    description TEXT DEFAULT 'No description available',
    brand TEXT DEFAULT 'Generic',
    sku TEXT DEFAULT 'SKU000',
    tags TEXT DEFAULT '',
    stock_kg INTEGER DEFAULT 0
)''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS product_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    ingredients TEXT DEFAULT 'No ingredients listed.',
    health_benefits TEXT DEFAULT 'No health benefits listed.',
    FOREIGN KEY (product_id) REFERENCES shop_products(id)
)
''')

# Dummy data for testing
# Dummy data for testing
cursor.execute("INSERT INTO product_details (product_id, ingredients, health_benefits) VALUES (?, ?, ?)", 
               (1, 
                "Wheat flour, Sugar, Cocoa, Milk solids", 
                "Boosts energy, Rich in calcium, Improves mood"))

cursor.execute("INSERT INTO product_details (product_id, ingredients, health_benefits) VALUES (?, ?, ?)", 
               (2, 
                "Cotton, Buttons, Dye", 
                "Breathable, Lightweight, Comfortable"))


# Insert data
cursor.executemany("INSERT INTO categories VALUES (?, ?)", categories_data)
cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", products_data)
cursor.executemany("INSERT INTO shop_products (title, category, img_default, img_hover, new_price, old_price, badge, badge_class) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", shop_products_data)

conn.commit()
conn.close()
print("Database initialized successfully.")
