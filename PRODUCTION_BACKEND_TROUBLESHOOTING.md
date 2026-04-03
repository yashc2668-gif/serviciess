# 🎯 PRODUCTION BACKEND ISSUES - Complete Troubleshooting

**Language**: Hinglish + English  
**Status**: Autonomous Fix Guide  
**Date**: March 31, 2026  

---

## 🔴 QUICK DIAGNOSIS

Pehle check kro **backend ka actual error** Railway dashboard se:

```powershell
# Open PowerShell
railway login
railway link

# Check service status
railway service list

# See backend logs (last 50 lines)
railway logs --service backend | tail -50

# Follow real-time logs
railway logs --service backend --follow
```

---

## ❌ Common Production Issues & Fixes

### Issue #1: PostgreSQL Connection Refused

**Error Message:**
```
psycopg2.OperationalError: could not connect to server: Connection refused
```

**Fix:**
1. See: [FIX_PRODUCTION_POSTGRESQL.md](./FIX_PRODUCTION_POSTGRESQL.md)
2. Or quick fix:
```powershell
railway variables set POSTGRES_HOST="postgres"
railway variables set POSTGRES_PORT="5432"
railway service restart --service backend
sleep 30  # Wait for restart
```

---

### Issue #2: ALLOWED_ORIGINS JSON Error

**Error Message:**
```
json.decoder.JSONDecodeError: Expecting value: line 1 column 2 char 1
```

**Cause**: Invalid JSON in ALLOWED_ORIGINS variable

**Fix:**
```powershell
# Use EXACTLY this format (no localhost in production!):
railway variables set ALLOWED_ORIGINS='["https://m2n-frontend.vercel.app","https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app","https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app"]'

# Restart backend
railway service restart --service backend
```

**Verify:**
- No single quotes inside
- No spaces after `[` or before `]`
- All domains wrapped in double quotes `"https://..."`
- Domains separated by commas

---

### Issue #3: Migrations Failed

**Error Message:**
```
WARNING: Migrations failed after 10 attempts. Starting app anyway...
```

**Cause**: Database not accessible during startup

**Fix:**
```powershell
# 1. Check if postgres service is running
railway service status --service postgres
# Should show: RUNNING or DEPLOYED

# 2. Check connection variables
railway variables get | grep POSTGRES

# 3. If still failing, manual trigger:
railway service restart --service backend
railway logs --service backend --follow
# Wait 2-3 minutes for DB to be ready
```

---

### Issue #4: Secret Key Not Set

**Error Message:**
```
CRITICAL: SECRET_KEY is 'CHANGE-ME' - SECURITY RISK!
```

**Fix:**
```powershell
# Generate random secret (choose one):

# Option A - PowerShell:
[System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))

# Option B - Python:
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Option C - Online: Use https://generate-secret.vercel.app/

# Then set it:
railway variables set SECRET_KEY="<paste-generated-secret-here>"

# Set environment to production
railway variables set ENVIRONMENT="production"
railway variables set DEBUG="False"

# Restart
railway service restart --service backend
```

---

### Issue #5: CORS Error / Frontend Can't Connect

**Error in Browser Console:**
```
Access to XMLHttpRequest at 'https://backend.railway.app/api/v1/...'
from origin 'https://m2n-frontend.vercel.app' has been blocked by CORS policy
```

**Fix:**
```powershell
# 1. Verify ALLOWED_ORIGINS is set correctly
railway variables get | grep ALLOWED_ORIGINS

# Should contain your Vercel domain(s)

# 2. If missing, add it:
railway variables set ALLOWED_ORIGINS='["https://m2n-frontend.vercel.app","https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app","https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app"]'

# 3. If you have multiple builds, add ALL of them:
# Check Vercel dashboard for all deployment preview URLs
# Add any branch preview URLs to ALLOWED_ORIGINS

# 4. Restart
railway service restart --service backend
```

---

### Issue #6: Out of Memory / Crash Loop

**Error Message:**
```
Container killed due to memory limit exceeded
OOMKilled: Container was terminated due to out-of-memory
```

**Fix:**
```powershell
# 1. Check current RAM usage
railway service status --service backend

# 2. Increase RAM via Dashboard:
# - Go to https://railway.app/
# - Click m2n-serviciess → backend
# - Settings → Railway Plan
# - Increase RAM to 1GB minimum

# 3. Or restart service (hard limit check):
railway service restart --service backend

# 4. Monitor after restart:
railway logs --service backend --follow
```

---

### Issue #7: Healthcheck Failing

**Error Message:**
```
Health check failed: returned exit code 1
```

**Fix - Check Healthcheck Path:**
```powershell
# The railway.toml has:
# healthcheckPath = "/health"

# Verify this endpoint works locally:
# curl http://localhost:8000/health

# If that fails, check backend/main.py
# Should have GET /health endpoint that returns:
# {"status":"ok", "app":"M2N Construction ERP", "environment":"production"}

# If still failing, bypass healthcheck temporarily:
# Via Dashboard: 
# - Service Settings → Health Check → Disable
# - (Not recommended for production!)

# Better: Check backend logs
railway logs --service backend --follow
```

---

### Issue #8: Database Username/Password Wrong

**Error Message:**
```
password authentication failed for user "m2n_app"
```

**Fix:**
```powershell
# 1. Get current password from Railway Postgres service:
railway service status --service postgres

# 2. Get the DATABASE_URL or POSTGRES_PASSWORD:
railway variables get --service postgres

# 3. Copy exact password
# 4. Set these in backend service:
railway variables set POSTGRES_USER="m2n_app"
railway variables set POSTGRES_PASSWORD="<paste-exact-password>"
railway variables set POSTGRES_HOST="postgres"
railway variables set POSTGRES_PORT="5432"
railway variables set POSTGRES_DB="m2n_db"

# 5. Restart backend:
railway service restart --service backend
```

---

### Issue #9: File Upload / Temp Directory Issues

**Error Message:**
```
OSError: [Errno 28] No space left on device
FileNotFoundError: [Errno 2] No such file or directory: 'uploads'
```

**Fix:**
```powershell
# In backend deployment, uploads folder should auto-create
# If not, volumes might be missing

# Check Dockerfile (should have):
# RUN mkdir -p /app/uploads /app/logs

# If issue persists:
# 1. Rebuild container:
railway service rebuild --service backend

# 2. Or increase Railway storage quota:
# Dashboard → Settings → Storage → Upgrade Plan
```

---

### Issue #10: App Crashing on Startup

**Error Message:**
```
[critical] Application startup failed
Traceback (most recent call last):
  ...
```

**Diagnosis Steps:**
```powershell
# 1. Check full logs
railway logs --service backend --follow | head -100

# 2. Common causes:
# - Missing environment variables
# - Database not ready
# - Port already in use (unlikely in Railway)
# - Python import error

# 3. Check all required variables are set:
railway variables get

# Must have:
# - SECRET_KEY (not "CHANGE-ME")
# - POSTGRES_* OR DATABASE_URL
# - ENVIRONMENT="production"
# - ALLOWED_ORIGINS (valid JSON array)

# 4. Force rebuild with fresh dependencies:
railway service rebuild --service backend

# 5. Monitor restart:
railway logs --service backend --follow
```

---

## 🔧 CHECK THESE VARIABLES IN ORDER

```powershell
# Run this to see what's set:
railway variables get --json | ConvertFrom-Json | Format-Table Key, Value

# Should have:
✅ SECRET_KEY = (something random, NOT "CHANGE-ME")
✅ ENVIRONMENT = "production"
✅ DEBUG = "False"
✅ POSTGRES_HOST = "postgres" (or Railway hostname)
✅ POSTGRES_PORT = "5432"
✅ POSTGRES_DB = "m2n_db"
✅ POSTGRES_USER = "m2n_app"
✅ POSTGRES_PASSWORD = (random generated password)
✅ ALLOWED_ORIGINS = ["https://m2n-frontend.vercel.app", ...]
✅ APP_PORT = "8000"
✅ LOG_LEVEL = "INFO"
✅ STORAGE_BACKEND = "local"
```

---

## 🧪 PRODUCTION HEALTH TESTS

After fix, run these:

```powershell
# Test 1: Backend is responding
$url = "https://m2n-serviciess-production.up.railway.app"
$health = Invoke-RestMethod -Uri "$url/health" -ErrorAction SilentlyContinue
Write-Host "Health: $health"
# Should return: {"status":"ok", ...}

# Test 2: Database is connected
$ready = Invoke-RestMethod -Uri "$url/health/ready" -ErrorAction SilentlyContinue
Write-Host "Ready: $ready"
# Should return: {"status":"ok"}

# Test 3: API is working
$api = Invoke-RestMethod -Uri "$url/api/v1/auth/health" -ErrorAction SilentlyContinue
Write-Host "API Health: $api"
# Should return 200 OK

# Test 4: Frontend can reach it (from browser console)
# fetch('https://m2n-serviciess-production.up.railway.app/api/v1/auth/health')
#  .then(r => r.json()).then(console.log)
```

---

## 📝 STEP-BY-STEP FIX EXECUTION

**If you're seeing an error:**

1. **Identify the error** → Read logs via:
   ```powershell
   railway logs --service backend --follow
   ```

2. **Find matching issue** → Look above (Issue #1-10)

3. **Apply fix** → Run the code block

4. **Wait** → 2-3 minutes for restart

5. **Test** → Run health tests above

6. **Verify** → Check frontend can connect

---

## 🆘 IF NOTHING WORKS

**Create Emergency Package:**
```powershell
# Collect all diagnostic data
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$outfile = "production_debug_$timestamp.txt"

"=== BACKEND SERVICE STATUS ===" | Tee-Object -FilePath $outfile
railway service status --service backend | Tee-Object -FilePath $outfile -Append

"=== POSTGRES SERVICE STATUS ===" | Tee-Object -FilePath $outfile -Append
railway service status --service postgres | Tee-Object -FilePath $outfile -Append

"=== BACKEND LOGS (Last 100 lines) ===" | Tee-Object -FilePath $outfile -Append
railway logs --service backend | tail -100 | Tee-Object -FilePath $outfile -Append

"=== POSTGRES LOGS (Last 50 lines) ===" | Tee-Object -FilePath $outfile -Append
railway logs --service postgres | tail -50 | Tee-Object -FilePath $outfile -Append

"=== ENVIRONMENT VARIABLES ===" | Tee-Object -FilePath $outfile -Append
railway variables get | Tee-Object -FilePath $outfile -Append

Write-Host "Debug info saved to: $outfile"
```

**Then:**
1. Check [DEPLOYMENT_README.md](./DEPLOYMENT_README.md)
2. Check [backend/RUNBOOK.md](./backend/RUNBOOK.md)
3. Review individual service Docker logs
4. Consider full rollback if needed

---

## 🎯 NEXT STEPS RIGHT NOW

1. ✅ Run diagnostic (see top of file)
2. ✅ Find your error in Issue #1-10 above
3. ✅ Apply the fix
4. ✅ Wait 2-3 minutes
5. ✅ Test with health checks
6. ✅ If still broken, redo with DEBUG=True temporarily to see actual error
7. ✅ Reference docs if help needed

**Time to fix**: Usually 5-10 minutes per issue.
