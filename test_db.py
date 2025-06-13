import psycopg2

# Supabase PostgreSQL credentials
DB_USER = "postgres.xapwrudbiysziedhrvcd"
DB_PASSWORD = "Kodesh@12"
DB_HOST = "aws-0-ap-south-1.pooler.supabase.com"
DB_PORT = "5432"
DB_NAME = "postgres"

try:
    conn = psycopg2.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME
    )
    cursor = conn.cursor()
    print("✅ Connected to Supabase PostgreSQL for verification\n")

    tables = ["categories", "products", "shop_products", "product_details"]

    for table in tables:
        print(f"📦 Table: {table}")
        # Check if table exists
        cursor.execute(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = '{table}'
            );
        """)
        exists = cursor.fetchone()[0]
        if not exists:
            print(f"❌ Table '{table}' does NOT exist.\n")
            continue

        # Count rows
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        count = cursor.fetchone()[0]
        print(f"✅ Table exists with {count} rows.")

        # Print top 2 rows
        cursor.execute(f"SELECT * FROM {table} LIMIT 2;")
        rows = cursor.fetchall()
        for row in rows:
            print("   ↪", row)
        print()

    cursor.close()
    conn.close()
    print("✅ Verification completed.")

except Exception as e:
    print(f"❌ Verification failed: {e}")
