"""
Run SQL migration script using SQLAlchemy - Standalone version
Uses same config as the main application
"""
import os
import sys
from sqlalchemy import create_engine, text

# Default database config (same as app/core/config.py)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "m2n_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "m2n_app")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "m2n_app_123")

# Build DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

def run_migration():
    """Run the SQL migration script"""
    
    # Read SQL file
    sql_file_path = os.path.join(os.path.dirname(__file__), 'ADD_WORK_ORDER_FIELDS.sql')
    
    if not os.path.exists(sql_file_path):
        print(f"[ERROR] SQL file not found: {sql_file_path}")
        sys.exit(1)
    
    print(f"[INFO] Found SQL file: {sql_file_path}")
    
    with open(sql_file_path, 'r') as f:
        sql_content = f.read()
    
    # Create engine
    print(f"[INFO] Connecting to database at {POSTGRES_HOST}:{POSTGRES_PORT}...")
    print(f"       Database: {POSTGRES_DB}")
    print(f"       User: {POSTGRES_USER}")
    
    try:
        engine = create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
        
        # Test connection
        with engine.connect() as test_conn:
            test_conn.execute(text("SELECT 1"))
        print("[OK] Database connection successful\n")
        
    except Exception as e:
        print(f"\n[ERROR] Database connection failed: {e}")
        print("\nPossible solutions:")
        print("   1. Check if PostgreSQL is running")
        print("   2. Check if database exists")
        print("   3. Check username/password")
        print("\nYou can set environment variables:")
        print("   POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD")
        sys.exit(1)
    
    # Split into individual statements
    statements = [s.strip() for s in sql_content.split(';') if s.strip()]
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    with engine.connect() as conn:
        print("[INFO] Running SQL migration...")
        print("=" * 60)
        
        for i, statement in enumerate(statements, 1):
            if not statement or statement.startswith('--'):
                continue
                
            # Skip COMMENT statements
            if statement.upper().startswith('COMMENT'):
                continue
            
            try:
                # Print first line of statement
                first_line = statement.split('\n')[0][:70]
                print(f"  {first_line}...", end=" ")
                
                conn.execute(text(statement))
                print("OK")
                success_count += 1
                
            except Exception as e:
                error_msg = str(e)
                
                # If column/table already exists, it's okay
                if "already exists" in error_msg.lower():
                    print("SKIP (already exists)")
                    skip_count += 1
                else:
                    print(f"ERROR: {error_msg[:60]}")
                    error_count += 1
        
        print("=" * 60)
        print(f"[DONE] Migration completed! Success: {success_count}, Skipped: {skip_count}, Errors: {error_count}")
    
    # Verify columns were added (in a separate connection)
    print("\n[INFO] Verifying columns in 'contracts' table...")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'contracts' 
            AND column_name IN ('wo_type', 'wo_number', 'client_id', 'contractor_category', 
                               'advance_percentage', 'security_deposit', 'billing_cycle', 'approval_status')
            ORDER BY column_name
        """))
        
        columns = [row[0] for row in result]
        if columns:
            print(f"[OK] Found {len(columns)} new columns:")
            for col in columns:
                print(f"     - {col}")
        else:
            print("[WARN] No new columns found!")

if __name__ == "__main__":
    print("Work Order Fields Migration")
    print("=" * 60)
    run_migration()
    print("\nDone! You can now restart the backend server.")
