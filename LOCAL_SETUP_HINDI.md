# M2N Software - Local Setup Guide (Hindi)

## Prerequisites (Pehle yeh install karein)

### 1. PostgreSQL Install Karein

**Option A: Windows par PostgreSQL install karna**
1. Download karein: https://www.postgresql.org/download/windows/
2. Installer run karein
3. Password set karein: `m2n_app_123` (ya apna password)
4. Port 5432 select karein
5. pgAdmin 4 bhi install karein

**Option B: Docker use karna (Recommended for developers)**
```powershell
# Docker install karein agar nahi hai: https://docs.docker.com/desktop/install/windows-install/
# Phir run karein:
docker run --name m2n-postgres -e POSTGRES_PASSWORD=m2n_app_123 -e POSTGRES_USER=m2n_app -e POSTGRES_DB=m2n_db -p 5432:5432 -d postgres:15
```

---

## Step 1: Backend Setup

### 1.1 Virtual Environment Banayein
```powershell
cd d:\M2N_SOFTWARE\backend

# Virtual environment create karein
python -m venv venv

# Activate karein (Windows)
venv\Scripts\activate

# Activate karein (Mac/Linux)
# source venv/bin/activate
```

### 1.2 Dependencies Install Karein
```powershell
# Virtual env activate hone ke baad
pip install -r requirements.txt
```

### 1.3 Database Setup
```powershell
# Agar PostgreSQL running hai to database create karein
# pgAdmin 4 mein jaake manually create karein ya terminal se:

# Windows mein psql ka path (example):
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "CREATE DATABASE m2n_db;"
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "CREATE USER m2n_app WITH PASSWORD 'm2n_app_123';"
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE m2n_db TO m2n_app;"
```

### 1.4 Environment Variables Check Karein
`backend/.env` file already hai. Check karein ki values sahi hain:
```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=m2n_db
POSTGRES_USER=m2n_app
POSTGRES_PASSWORD=m2n_app_123
```

### 1.5 Backend Run Karein
```powershell
# backend directory mein, virtual env activate hone ke baad
uvicorn main:app --reload --port 8000
```

**Success check:** Browser mein kholein: http://localhost:8000/docs
Yahan FastAPI Swagger UI dikhna chahiye.

---

## Step 2: Frontend Setup

### 2.1 New Terminal Open Karein
Backend wale terminal ko band na karein, naya terminal open karein.

### 2.2 Dependencies Install Karein
```powershell
cd d:\M2N_SOFTWARE\frontend

npm install
```

### 2.3 Environment Variables Set Karein
`frontend/.env` file create karein:
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### 2.4 Frontend Run Karein
```powershell
npm run dev
```

**Success check:** Browser mein kholein: http://localhost:5173
Login page dikhna chahiye.

---

## Step 3: Test Karein

### Backend Test
```powershell
# Terminal mein curl command:
curl http://localhost:8000/api/v1/health/ready

# Expected output:
# {"status": "ok"}
```

### Frontend Se Backend Connection Test
Browser DevTools console mein:
```javascript
fetch('http://localhost:8000/api/v1/health/ready')
  .then(r => r.json())
  .then(console.log)
```
Output: `{status: "ok"}`

---

## Common Issues (Samasyaein)

### Issue 1: PostgreSQL Connection Error
**Error:** `psycopg2.OperationalError: connection refused`

**Solution:**
1. Check PostgreSQL service running hai: `services.msc` mein check karein
2. Check port 5432: `netstat -an | findstr 5432`
3. Password check karein in `.env`

### Issue 2: CORS Error
**Error:** `CORS policy: No 'Access-Control-Allow-Origin' header`

**Solution:**
`backend/.env` mein ensure karein:
```env
ALLOWED_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
```

### Issue 3: Port Already in Use
**Error:** `Port 8000 is already in use`

**Solution:**
```powershell
# Process find karein
netstat -ano | findstr :8000

# Ya different port use karein
uvicorn main:app --reload --port 8001
```

### Issue 4: npm install error
**Solution:**
```powershell
# Cache clean karein
npm cache clean --force

# Phir retry karein
npm install
```

---

## Quick Start Commands (Summary)

**Terminal 1 - Backend:**
```powershell
cd d:\M2N_SOFTWARE\backend
venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```powershell
cd d:\M2N_SOFTWARE\frontend
npm run dev
```

**Access:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Demo Users (Agar seed data hai to)

Default login credentials:
- **Email:** admin@m2n.com
- **Password:** admin123

Ya seed script run karein:
```powershell
cd d:\M2N_SOFTWARE\backend
venv\Scripts\activate
python seed_demo_users.py
```

---

**Ready!** Aapka M2N Software local par run raha hai! 🚀
