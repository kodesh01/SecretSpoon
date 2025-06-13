import psycopg2

# PostgreSQL connection details
DB_USER = "postgres.xapwrudbiysziedhrvcd"
DB_PASSWORD = "Kodesh@12"
DB_HOST = "aws-0-ap-south-1.pooler.supabase.com"
DB_PORT = "5432"
DB_NAME = "postgres"

# Sample data
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

product_details_data = [
    (1, "Wheat flour, Sugar, Cocoa, Milk solids", "Boosts energy, Rich in calcium, Improves mood"),
    (2, "Cotton, Buttons, Dye", "Breathable, Lightweight, Comfortable")
]

try:
    # Connect to Supabase PostgreSQL
    conn = psycopg2.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME
    )
    cursor = conn.cursor()
    print("✅ Connected to Supabase PostgreSQL")

    # === Create Tables ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name TEXT,
            image_url TEXT
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            title TEXT,
            category TEXT,
            price NUMERIC,
            old_price NUMERIC,
            image1 TEXT,
            image2 TEXT,
            badge TEXT,
            tag TEXT
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shop_products (
            id SERIAL PRIMARY KEY,
            title TEXT,
            category TEXT,
            img_default TEXT,
            img_hover TEXT,
            new_price NUMERIC,
            old_price NUMERIC,
            badge TEXT,
            badge_class TEXT,
            description TEXT DEFAULT 'No description available',
            brand TEXT DEFAULT 'Generic',
            sku TEXT DEFAULT 'SKU000',
            tags TEXT DEFAULT '',
            stock_kg INTEGER DEFAULT 0
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_details (
            id SERIAL PRIMARY KEY,
            product_id INTEGER REFERENCES shop_products(id),
            ingredients TEXT DEFAULT 'No ingredients listed.',
            health_benefits TEXT DEFAULT 'No health benefits listed.'
        );
    """)

    cursor.execute("DROP TABLE IF EXISTS users CASCADE;")  # Deletes users table and related foreign keys (like in orders)
 
    cursor.execute("""
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            mobile TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            address_line TEXT,
            city TEXT,
            state TEXT,
            pincode TEXT
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            title TEXT NOT NULL,
            total_cost NUMERIC NOT NULL,
            status TEXT DEFAULT 'Pending'
        );
    """)
    cursor.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS quantity INTEGER;")
    cursor.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS unit TEXT;")
        

    # === Insert Sample Data if not exists ===
    for name, image in categories_data:
        cursor.execute("SELECT * FROM categories WHERE name=%s", (name,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO categories (name, image_url) VALUES (%s, %s)", (name, image))

    for product in products_data:
        cursor.execute("SELECT * FROM products WHERE id=%s", (product[0],))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO products (id, title, category, price, old_price, image1, image2, badge, tag)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, product)

    for shop_product in shop_products_data:
        title = shop_product[0]
        cursor.execute("SELECT * FROM shop_products WHERE title=%s", (title,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO shop_products (title, category, img_default, img_hover, new_price, old_price, badge, badge_class)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, shop_product)

    for detail in product_details_data:
        product_id = detail[0]
        cursor.execute("SELECT * FROM product_details WHERE product_id=%s", (product_id,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO product_details (product_id, ingredients, health_benefits)
                VALUES (%s, %s, %s)
            """, detail)

    conn.commit()
    print("✅ Tables created and data inserted successfully.\n")

    # === Verify that tables contain expected data ===
    verification_queries = {
        "categories": "SELECT COUNT(*) FROM categories;",
        "products": "SELECT COUNT(*) FROM products;",
        "shop_products": "SELECT COUNT(*) FROM shop_products;",
        "product_details": "SELECT COUNT(*) FROM product_details;",
        "users": "SELECT COUNT(*) FROM users;",
        "orders": "SELECT COUNT(*) FROM orders;"
    }

    for table, query in verification_queries.items():
        cursor.execute(query)
        count = cursor.fetchone()[0]
        print(f"📦 Table '{table}' has {count} row(s).")

    cursor.close()
    conn.close()
    print("\n✅ Verification complete.")

except Exception as e:
    print(f"❌ Error: {e}")
