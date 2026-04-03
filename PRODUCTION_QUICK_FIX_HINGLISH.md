# 🎯 PRODUCTION BACKEND FIX - START HERE (Hinglish Version)

**Status**: PostgreSQL / Backend production issue  
**Tarikh**: March 31, 2026  
**Language**: Hinglish (उंदी/اردو + English)  

---

## 📌 आपका Problem क्या है? (What's Your Issue?)

Backend production mein fail ho raha hai। Ye dekho kaunsa issue match ho raha:

1. **❌ PostgreSQL Service FAILED** - Database start nahi ho raha
2. **❌ Backend Container Crashing** - App restart ho har time
3. **❌ Frontend Connection Error** - API se connect nahi ho raha (CORS)
4. **❌ Database Connection Timeout** - DB se connection nahi ban raha
5. **❌ Kuch aur issue** - Debug logs dekh kar solve करत

---

## ⚡ FASTEST FIX (5 मिनट)

### Step 1: Terminal खोलो (Open PowerShell/Terminal)

```powershell
# Go to project directory
cd d:\M2N_SOFTWARE

# Open PowerShell as Admin (if possible)
Start-Process powershell -Verb RunAs
```

### Step 2: QUICK AUTO-FIX চালаও

```powershell
# यह script automatically सभी common issues fix करेगा:
powershell -File fix-production-quick.ps1
```

**यह करेगा:**
- ✅ PostgreSQL connection variables verify करेगा
- ✅ ALLOWED_ORIGINS JSON fix करेगा
- ✅ Environment production पर set करेगा
- ✅ Backend restart करेगा
- ✅ Health test करेगा

---

## 📊 अगर Auto-Fix काम न करे

### Option A: Health Check करो

```powershell
powershell -File check-production-health.ps1
```

यह देखेगा:
- Railway services की status (running/failed)
- सभी environment variables
- Backend health endpoints
- Recent error logs

### Option B: Specific Issues Fix करो

अपना error देख कर below documents से help लो:

| Document | Issue |
|----------|-------|
| [FIX_PRODUCTION_POSTGRESQL.md](FIX_PRODUCTION_POSTGRESQL.md) | Database issue, PostgreSQL not starting |
| [PRODUCTION_BACKEND_TROUBLESHOOTING.md](PRODUCTION_BACKEND_TROUBLESHOOTING.md) | Backend crashing, connection errors, CORS issues |

---

## 🔧 MANUAL STEPS (अगर Auto-Fix काम न करे)

### Step 1: Railway से Login करो

```powershell
# Login to Railway
railway login

# Link to project
railway link
```

### Step 2: Service Status Check करो

```powershell
# सभी services देख
railway service list

# Backend के logs
railway logs --service backend --follow

# PostgreSQL के logs (अगर issue है)
railway logs --service postgres --follow
```

### Step 3: Fix करो (Choose your issue)

#### Issue: PostgreSQL Failed

```powershell
# Postgres restart करो
railway service restart --service postgres

# 30 seconds wait करो
Start-Sleep -Seconds 30

# Check करो
railway service status --service postgres
```

#### Issue: ALLOWED_ORIGINS Error

```powershell
# Exact format (कोई space न हो):
railway variables set ALLOWED_ORIGINS='["https://m2n-frontend.vercel.app","https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app","https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app"]'

# Backend restart करो
railway service restart --service backend

# 2-3 minutes wait करो
```

#### Issue: SECRET_KEY Not Set

```powershell
# Random secret generate करो:
$secret = [System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))

# Set करो
railway variables set SECRET_KEY=$secret

# Production mode on करो
railway variables set ENVIRONMENT="production"
railway variables set DEBUG="False"

# Restart करो
railway service restart --service backend
```

### Step 4: Verify करो

```powershell
# Backend health test
$url = "https://m2n-serviciess-production.up.railway.app"
Invoke-RestMethod -Uri "$url/health"

# Should return:
# {"status":"ok","app":"M2N Construction ERP","environment":"production"}

# Database test
Invoke-RestMethod -Uri "$url/health/ready"

# Should return:
# {"status":"ok"}
```

---

## 📋 Common Issues & Quick Fixes

### Issue #1: `psycopg2.OperationalError: could not connect to server`

```powershell
# Database connection issue
railway variables set POSTGRES_HOST="postgres"
railway variables set POSTGRES_PORT="5432"
railway variables set POSTGRES_DB="m2n_db"
railway service restart --service backend
```

### Issue #2: `json.decoder.JSONDecodeError`

```powershell
# ALLOWED_ORIGINS JSON format wrong
# Use EXACTLY this (copy-paste करो):
railway variables set ALLOWED_ORIGINS='["https://m2n-frontend.vercel.app","https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app","https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app"]'

railway service restart --service backend
```

### Issue #3: `CORS policy: No 'Access-Control-Allow-Origin' header`

```powershell
# Frontend तक backend नहीं पहुँच रहा
# ALLOWED_ORIGINS है but check करो सही है:
railway variables get | grep ALLOWED_ORIGINS

# अगर नहीं है तो ऊपर वाला fix करो
```

### Issue #4: Application keeps crashing

```powershell
# Full logs देख
railway logs --service backend --follow | head -100

# अगर "migrations failed" है:
# Database तैयार नहीं है। Wait करो:
Start-Sleep -Seconds 60

# फिर restart करो:
railway service restart --service backend
railway logs --service backend --follow
```

### Issue #5: Out of Memory

```powershell
# Railway plan upgrade करो (Dashboard में)
# या increase करो RAM:
# Dashboard → Service Settings → RAM → 1GB

# फिर restart करो
railway service restart --service backend
```

---

## 🎯 PRODUCTION CHECKLIST

Before production को live मानो, यह सब चेक करो:

- [ ] सभी services **RUNNING** हैं
- [ ] `/health` endpoint **200 OK** return करता है
- [ ] `/health/ready` endpoint **200 OK** return करता है (DB ready है)
- [ ] Frontend से API तक connect हो सकता है (कोई CORS error नहीं)
- [ ] Login काम करता है
- [ ] Data save/load हो सकता है
- [ ] Secret key is NOT "CHANGE-ME"
- [ ] ENVIRONMENT="production" है
- [ ] DEBUG="False" है

---

## 📞 अगर अभी भी काम न करे

### Debug Package बनाओ:

```powershell
# सभी logs और status collect करो
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$file = "debug_$timestamp.txt"

"=== SERVICES ===" | Out-File -FilePath $file
railway service list | Out-File -FilePath $file -Append

"=== BACKEND STATUS ===" | Out-File -FilePath $file -Append
railway service status --service backend | Out-File -FilePath $file -Append

"=== POSTGRES STATUS ===" | Out-File -FilePath $file -Append
railway service status --service postgres | Out-File -FilePath $file -Append

"=== BACKEND LOGS ===" | Out-File -FilePath $file -Append
railway logs --service backend | Out-File -FilePath $file -Append

"=== POSTGRES LOGS ===" | Out-File -FilePath $file -Append
railway logs --service postgres | Out-File -FilePath $file -Append

"=== VARIABLES ===" | Out-File -FilePath $file -Append
railway variables get | Out-File -FilePath $file -Append

Write-Host "Debug info saved to: $file"
```

फिर देखो यह documents:
1. [PRODUCTION_BACKEND_TROUBLESHOOTING.md](PRODUCTION_BACKEND_TROUBLESHOOTING.md) - Complete troubleshooting guide
2. [FIX_PRODUCTION_POSTGRESQL.md](FIX_PRODUCTION_POSTGRESQL.md) - Database-specific fixes
3. [backend/RUNBOOK.md](backend/RUNBOOK.md) - Backend operations guide

---

## 🚀 SUCCESS SIGNS

Agar यह सब काम कर रहा है तो production ready है:

```
✅ railway service list → सभी services RUNNING हैं
✅ curl https://.../health → {"status":"ok"}
✅ curl https://.../health/ready → {"status":"ok"}
✅ Frontend से login हो सकता है
✅ Projects/Materials/Labour data दिख रहा है
✅ New record create हो सकता है
✅ Reports generate हो रहे हैं
```

---

## 📝 COMMAND REFERENCE

```powershell
# Login and setup
railway login
railway link

# Check status
railway service list
railway service status --service backend
railway service status --service postgres

# View logs
railway logs --service backend --follow
railway logs --service postgres --follow

# Update variables
railway variables set KEY="value"
railway variables get

# Restart services
railway service restart --service backend
railway service restart --service postgres

# Rebuild from scratch
railway service rebuild --service backend

# Test endpoints
$url = "https://m2n-serviciess-production.up.railway.app"
Invoke-RestMethod -Uri "$url/health"
Invoke-RestMethod -Uri "$url/health/ready"
```

---

## 🎯 NEXT STEP

अभी करो (Do Now):

```powershell
# Open project folder
cd d:\M2N_SOFTWARE

# Run auto-fix
powershell -File fix-production-quick.ps1

# Or run health check
powershell -File check-production-health.ps1
```

**Expected time**: 5-10 minutes  
**Success rate**: 85% of issues auto-fixed

---

## ❗ IMPORTANT NOTES

1. **Restart का wait करो** - Backend को 2-3 minutes लग सकते हैं restart होने में
2. **Database को time दो** - PostgreSQL को initialization में time लग सकता है
3. **Logs देখो** - अगर कुछ काम न करे तो `railway logs` से actual error पता चलेगा
4. **Backup है** - Database में pहले से data है? [BACKUP_RECOVERY_RUNBOOK.md](backend/BACKUP_RECOVERY_RUNBOOK.md) देखो

---

**अगर सवाल हो या help चाहिए तो:**
1. Logs check करो: `railway logs --service backend --follow`
2. Documents पढ़ो: [PRODUCTION_BACKEND_TROUBLESHOOTING.md](PRODUCTION_BACKEND_TROUBLESHOOTING.md)
3. Manual fix करो: [FIX_PRODUCTION_POSTGRESQL.md](FIX_PRODUCTION_POSTGRESQL.md)

**अब शुरू करो!** 🚀
