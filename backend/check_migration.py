"""Check which columns are missing and try to add them"""
from sqlalchemy import create_engine, text

DATABASE_URL = 'postgresql://m2n_app:m2n_app_123@localhost:5432/m2n_db'
engine = create_engine(DATABASE_URL, isolation_level='AUTOCOMMIT')

statements = [
    ("wo_type", "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS wo_type VARCHAR(20) NOT NULL DEFAULT 'outgoing' CHECK (wo_type IN ('incoming', 'outgoing'))"),
    ("client_id", "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS client_id INTEGER REFERENCES companies(id)"),
    ("contractor_category", "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS contractor_category VARCHAR(50)"),
    ("advance_percentage", "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS advance_percentage DECIMAL(5,2) NOT NULL DEFAULT 0"),
    ("approval_status", "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (approval_status IN ('draft', 'pending', 'approved', 'rejected'))"),
]

with engine.connect() as conn:
    for col_name, stmt in statements:
        print(f"Adding {col_name}...")
        try:
            conn.execute(text(stmt))
            print(f"  -> OK")
        except Exception as e:
            print(f"  -> ERROR: {e}")

print("\nCreating missing indexes...")
index_statements = [
    "CREATE INDEX IF NOT EXISTS idx_contracts_wo_type ON contracts(wo_type)",
    "CREATE INDEX IF NOT EXISTS idx_contracts_client_id ON contracts(client_id)",
    "CREATE INDEX IF NOT EXISTS idx_contracts_approval_status ON contracts(approval_status)",
]

with engine.connect() as conn:
    for stmt in index_statements:
        print(f"Running: {stmt[:50]}...")
        try:
            conn.execute(text(stmt))
            print("  -> OK")
        except Exception as e:
            print(f"  -> ERROR: {e}")

print("\nVerifying all columns...")
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
    print(f"Found {len(columns)} columns:")
    for col in columns:
        print(f"  - {col}")
