import os
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL")

print("=" * 50)
print("DATABASE_URL from .env:")
print(database_url)
print("=" * 50)

if database_url:
    # Try to connect
    import psycopg
    try:
        conn = psycopg.connect(database_url)
        print("✅ Connection successful!")
        
        # Test a query
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"PostgreSQL version: {version[0]}")
        
        # Check tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cur.fetchall()
        print(f"\nTables found: {[t[0] for t in tables]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
else:
    print("❌ DATABASE_URL not found in .env")