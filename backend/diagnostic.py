#!/usr/bin/env python3
"""Comprehensive Railway deployment diagnostic"""
import os
import sys

print("=" * 60)
print("M2N RAILWAY DEPLOYMENT DIAGNOSTIC")
print("=" * 60)

# Test 1: Check environment variables
print("\n1️⃣  CHECKING ENVIRONMENT VARIABLES")
print("-" * 60)

required_vars = ["ENVIRONMENT", "DEBUG", "ALLOWED_ORIGINS", "DATABASE_URL"]
set_vars = {}

for var in required_vars:
    value = os.environ.get(var, "NOT SET")
    set_vars[var] = value
    status = "✅" if value != "NOT SET" else "❌"
    print(f"{status} {var}: {value[:50]}..." if len(str(value)) > 50 else f"{status} {var}: {value}")

# Test 2: Parse ALLOWED_ORIGINS
print("\n2️⃣  PARSING ALLOWED_ORIGINS")
print("-" * 60)

allowed_origins_str = set_vars.get("ALLOWED_ORIGINS", "[]")
print(f"Raw value: {allowed_origins_str}")

# Simulate pydantic validator
if isinstance(allowed_origins_str, str):
    trimmed = allowed_origins_str.strip()
    if trimmed.startswith("["):
        parsed = trimmed
        print("Format: JSON array (string)")
    else:
        parsed = [item.strip() for item in trimmed.split(",") if item.strip()]
        print("Format: Comma-separated list")
else:
    parsed = allowed_origins_str
    print("Format: Already a list")

if isinstance(parsed, list):
    print(f"✅ Successfully parsed {len(parsed)} origins:")
    for i, origin in enumerate(parsed, 1):
        print(f"   {i}. {origin}")
else:
    print(f"⚠️  Parsed as string (will be processed by Pydantic): {parsed[:100]}")

# Test 3: Database URL parsing
print("\n3️⃣  DATABASE URL")
print("-" * 60)

db_url = set_vars.get("DATABASE_URL", "NOT SET")
if db_url != "NOT SET":
    # Hide password for security
    if "@" in db_url:
        user_part, host_part = db_url.split("@", 1)
        user_prefix = user_part.split("://")[0] + "://"
        print(f"✅ Connection string: {user_prefix}***:***@{host_part}")
    else:
        print(f"⚠️  Unexpected format: {db_url[:100]}")
else:
    print("❌ DATABASE_URL not set")

# Test 4: Check if we can import the config
print("\n4️⃣  LOADING PYDANTIC SETTINGS")
print("-" * 60)

try:
    # Add backend to path
    sys.path.insert(0, os.path.dirname(__file__))
    from app.core.config import settings
    
    print(f"✅ Settings loaded successfully")
    print(f"   Environment: {settings.ENVIRONMENT}")
    print(f"   Debug: {settings.DEBUG}")
    print(f"   Project: {settings.PROJECT_NAME}")
    print(f"   ALLOWED_ORIGINS ({len(settings.ALLOWED_ORIGINS)} items):")
    for origin in settings.ALLOWED_ORIGINS:
        print(f"     - {origin}")
    
    # Test database URL
    print(f"   Database URL:")
    db_url = settings.sqlalchemy_database_url
    if "@" in db_url:
        user_part, host_part = db_url.split("@", 1)
        user_prefix = user_part.split("://")[0] + "://"
        print(f"     {user_prefix}***:***@{host_part}")
    else:
        print(f"     {db_url}")
        
except Exception as e:
    print(f"❌ Error loading settings: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Try connecting to database (if available)
print("\n5️⃣  DATABASE CONNECTIVITY TEST")
print("-" * 60)

try:
    from sqlalchemy import create_engine, text
    
    db_url = settings.sqlalchemy_database_url
    print(f"Attempting to connect to database...")
    
    engine = create_engine(db_url, pool_pre_ping=True, echo=False)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()")).scalar()
        print(f"✅ Connected successfully!")
        print(f"   Database version: {result[:50]}...")
        
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print(f"   This is expected if database isn't reachable locally")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
