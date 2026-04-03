# 🔐 LOGIN CREDENTIALS - M2N Production

**Status**: Ready to login!  
**Date**: March 31, 2026  

---

## 🎯 DEMO LOGIN CREDENTIALS

Use these credentials to login to M2N Construction ERP:

### Admin Account
```
Email:    demo-admin@example.com
Password: DemoPass123!
```

### Project Manager Account
```
Email:    demo-pm@example.com
Password: DemoPass123!
```

### Accountant Account
```
Email:    demo-accounts@example.com
Password: DemoPass123!
```

---

## 🌐 HOW TO ACCESS

### Step 1: Open Frontend
```
https://m2n-frontend.vercel.app
```

### Step 2: Click "SIGN IN"

### Step 3: Enter Credentials
```
Work email:  demo-admin@example.com
Password:    DemoPass123!
```

### Step 4: Click "Enter workspace"

---

## ❓ अगर LOGIN न हو:

**Problem**: "Use a valid work email" error  
**Solution**: Email address spelling check करो, exact copy-paste करो

**Problem**: "Minimum 8 characters required" error  
**Solution**: Password exact है: `DemoPass123!` (with the `!`)

**Problem**: Credentials काम नहीं कर रहे  
**Solution**: Backend से नए users create करने हैं। Below command चलाओ:

```powershell
cd d:\M2N_SOFTWARE\backend

# Setup venv if needed:
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies:
pip install -r requirements.txt

# Seed demo users:
python -m app.db.demo_seed
```

---

## 📝 अगर खुद User Create करना हो:

### Option 1: Admin Panel से (अगर कोई admin already है)
```
1. Login with any working account
2. Go to Settings → Users
3. Click "Add User"
4. Fill details और save
```

### Option 2: Database से Direct

```powershell
# Option A: Via Railway CLI
railway login
railway shell
# फिर inside container:
python -m app.db.demo_seed

# Option B: Via Python Script
cd backend
.\venv\Scripts\python.exe seed_demo_users.py
```

---

## ✅ AFTER LOGIN - What to Do

Once you're logged in as demo-admin:

1. **Dashboard**
   - View projects overview
   - Check financial summary
   - See recent activities

2. **Projects**
   - Create → New Project
   - Add project name, location, value
   - Save

3. **Materials**
   - View existing materials
   - Add new material with quantity
   - Track inventory

4. **Labour**
   - Record daily attendance
   - Create labour bills
   - Process payments

5. **Finance**
   - View RA Bills  
   - Create measurements
   - Generate bills
   - Allocate payments

6. **Documents**
   - Upload contract copies
   - Manage versions
   - Download when needed

---

## 🔄 TROUBLESHOOTING

### Backend Not Responding
```powershell
# Check backend health
$url = "https://m2n-serviciess-production.up.railway.app"
Invoke-RestMethod -Uri "$url/health"

# Should return: {"status":"ok"}
```

### Database Connection Failed
```powershell
# Check database readiness
$url = "https://m2n-serviciess-production.up.railway.app"
Invoke-RestMethod -Uri "$url/health/ready"

# Should return: {"status":"ready"}
```

### Frontend Shows Blank
```
1. Clear browser cache (Ctrl+Shift+Delete)
2. Hard refresh (Ctrl+F5)
3. Try incognito/private mode
4. Check browser console for errors (F12)
```

---

## 📞 API ENDPOINTS FOR TESTING

### Health
```
GET https://m2n-serviciess-production.up.railway.app/health
Returns: {"status":"ok"}
```

### Ready (DB Check)
```
GET https://m2n-serviciess-production.up.railway.app/health/ready
Returns: {"status":"ready"}
```

### API Docs
```
GET https://m2n-serviciess-production.up.railway.app/docs
Open in browser to see all API endpoints
```

### Login via API
```
POST https://m2n-serviciess-production.up.railway.app/api/v1/auth/login

Body:
{
  "email": "demo-admin@example.com",
  "password": "DemoPass123!"
}

Returns:
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {...}
}
```

---

## 🎯 SUMMARY

```
✅ Frontend Live:     https://m2n-frontend.vercel.app
✅ Backend Running:   https://m2n-serviciess-production.up.railway.app
✅ Database Connected: PostgreSQL ✓
✅ Login Ready:       Use demo-admin@example.com / DemoPass123!
✅ Demo Data:         Available via database seed
```

---

## 🚀 NEXT STEPS

1. ✅ Open frontend URL
2. ✅ Login with demo credentials
3. ✅ Explore dashboard
4. ✅ Create test data (project, materials, etc)
5. ✅ Test full workflow
6. ✅ Share with team

**अब शुरु करो! सभी कुछ ready है।** 🎉
