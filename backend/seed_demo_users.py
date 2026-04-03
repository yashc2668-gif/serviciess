#!/usr/bin/env python3
"""
Direct demo user seeding for production database
Run this locally or on Railway to create demo login credentials
"""

import os
import sys
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

# Try to import from app (if running from backend directory)
try:
    from app.core.security import hash_password
    from app.models.user import User
    from app.models.role import Role
    from app.db.base import Base
except ImportError:
    # Fallback: Define what we need
    from hashlib import sha256
    import secrets
    
    def hash_password(password: str) -> str:
        """Basic password hashing for demo"""
        return sha256((password + "salt").encode()).hexdigest()

# Database connection - try Railway environment first
DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    # Build from components (Railway style)
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "m2n_app")
    password = os.getenv("POSTGRES_PASSWORD", "m2n_app_123")
    database = os.getenv("POSTGRES_DB", "m2n_db")
    
    DB_URL = f"postgresql://{user}:{password}@{host}:{port}/{database}"

print(f"[INFO] Connecting to database...")
print(f"[INFO] Host: {DB_URL.split('@')[1].split('/')[0] if '@' in DB_URL else 'unknown'}")

try:
    engine = create_engine(DB_URL, echo=False)
    
    # Test connection
    with engine.connect() as conn:
        print("[OK] Database connection successful")
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # Check if users table exists
    inspector = inspect(engine)
    if not inspector.has_table("users"):
        print("[ERROR] Users table does not exist. Run migrations first.")
        sys.exit(1)
    
    # Demo users data
    DEMO_USERS = [
        {
            "email": "demo-admin@example.com",
            "full_name": "Demo Admin",
            "password": "DemoPass123!",
            "role": "admin",
        },
        {
            "email": "demo-pm@example.com",
            "full_name": "Demo Project Manager",
            "password": "DemoPass123!",
            "role": "project_manager",
        },
        {
            "email": "demo-accounts@example.com",
            "full_name": "Demo Accountant",
            "password": "DemoPass123!",
            "role": "accountant",
        },
    ]
    
    # Seed users
    created = 0
    skipped = 0
    
    for user_data in DEMO_USERS:
        email = user_data["email"]
        
        # Check if user exists
        existing = session.query(User).filter(User.email == email).first()
        if existing:
            print(f"[SKIP] User {email} already exists")
            skipped += 1
            continue
        
        # Create user
        try:
            user = User(
                full_name=user_data["full_name"],
                email=email,
                hashed_password=hash_password(user_data["password"]),
                role=user_data["role"],
                is_active=True,
            )
            session.add(user)
            print(f"[CREATE] {email} (role: {user_data['role']})")
            created += 1
        except Exception as e:
            print(f"[ERROR] Failed to create {email}: {e}")
    
    # Commit all
    session.commit()
    session.close()
    
    print("")
    print(f"[RESULT] Created: {created} | Already existed: {skipped}")
    print("")
    print("=== DEMO LOGIN CREDENTIALS ===")
    for user_data in DEMO_USERS:
        print(f"Email: {user_data['email']}")
        print(f"Password: {user_data['password']}")
        print("")
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
