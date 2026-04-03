# 🔧 PRODUCTION PostgreSQL FIX - Railway

**Status**: PostgreSQL failed on Railway  
**Date**: March 31, 2026  
**Priority**: 🔴 CRITICAL  

---

## ⚡ QUICK FIX (Do This First - 5 minutes)

### Step 1: Check PostgreSQL Service Status
```powershell
railway login
railway link
railway service list
```

You should see something like:
```
Service            Status      Status Text
postgres           BUILDING    Waiting for deployment...
backend            RUNNING     Deployed
```

**If Status is "FAILED"** → Go to Step 2

### Step 2: Restart PostgreSQL Service
```powershell
# Get current environment
$vars = railway variables get --json

# Restart the database service
railway service run "postgres" "sudo systemctl restart postgresql" --service postgres

# Or through Railway CLI (safest):
railway service list
# Find postgres service ID and:
railway service status --service postgres
```

### Step 3: Check Connection
```powershell
# Test database connection from Railway CLI
railway variables get

# Look for these:
# POSTGRES_HOST: (should be internal Railway hostname)
# POSTGRES_PORT: 5432
# POSTGRES_DB: m2n_db
# POSTGRES_USER: m2n_app
# POSTGRES_PASSWORD: (should be set)
```

---

## 🔍 IF THAT DOESN'T WORK - Full Diagnostic

### Problem 1: Database Connection String Issue

**Check in Railway Dashboard:**
1. Go to: https://railway.app/
2. Project: `m2n-serviciess`
3. Click: `Backend` service
4. Tab: `Variables`
5. Look for: `DATABASE_URL` or `POSTGRES_*` variables

**It should look like:**
```
POSTGRES_HOST=postgres (or Railway's internal hostname)
POSTGRES_PORT=5432
POSTGRES_DB=m2n_db
POSTGRES_USER=m2n_app
POSTGRES_PASSWORD=<generated-random-password>
```

**If missing, fix:**
```powershell
# Set correct variables
railway variables set POSTGRES_HOST="postgres"  
railway variables set POSTGRES_PORT="5432"
railway variables set POSTGRES_DB="m2n_db"
railway variables set POSTGRES_USER="m2n_app"
railway variables set POSTGRES_PASSWORD="<use-strong-password>"
```

---

### Problem 2: Storage Issue

PostgreSQL might be out of storage. **Quick check:**

```powershell
# Check Postgres service logs
railway logs --service postgres --follow

# Look for:
# - "no space left on device"
# - "disk quota exceeded"
# - "connection timeout"
```

**If storage issue:**
```powershell
# Delete and recreate database (⚠️ DATA LOSS - Use backup first!)
# See: ../backend/BACKUP_RECOVERY_RUNBOOK.md
```

---

### Problem 3: Migrations Not Running

Backend can't start if migrations fail. **Quick fix:**

```powershell
# Check backend logs
railway logs --service backend --follow

# Look for:
# [ERROR] Alembic migrations failed
# [ERROR] Connection refused
# [ERROR] psycopg2.OperationalError
```

**Solution:**
```powershell
# Force SSH into backend container (if Railway allows)
# Then run manually:
# python -m alembic upgrade head

# Or restart frontend to trigger:
railway service restart --service backend
```

---

## 🛠️ DEEPER FIX (If Above Didn't Work)

### Step A: Re-create PostgreSQL Service

**Via Railway Dashboard:**
1. Go to: https://railway.app/
2. Click: `m2n-serviciess` project
3. Find: PostgreSQL service
4. Click: ⋮ menu → "Destroy"
5. Click: "+ Add" → "Databases" → "PostgreSQL"
6. Create new with same credentials

**Or via CLI:**
```powershell
# Backup current data first!
railway service destroy --service postgres

# Wait 30 seconds, then Railway auto-creates new one
railway service list
```

### Step B: Restore from Backup

See: [BACKUP_RECOVERY_RUNBOOK.md](backend/BACKUP_RECOVERY_RUNBOOK.md)

```powershell
# If you have a backup:
# 1. Create fresh PostgreSQL
# 2. Get backup file
# 3. Restore: psql -U m2n_app -d m2n_db -f backup.sql
```

---

## ✅ VERIFY FIX

After applying fix, test:

```powershell
# 1. Check services running
railway service list

# Should show both backend and postgres as RUNNING (green)

# 2. Test backend health
Invoke-RestMethod -Uri "https://m2n-serviciess-production.up.railway.app/health"

# Should return:
# {"status":"ok","app":"M2N Construction ERP","environment":"production"}

# 3. Test backend readiness (includes DB check)
Invoke-RestMethod -Uri "https://m2n-serviciess-production.up.railway.app/health/ready"

# Should return:
# {"status":"ok"}

# 4. Test API
Invoke-RestMethod -Uri "https://m2n-serviciess-production.up.railway.app/api/v1/auth/health"

# Should return 200 OK
```

---

## 🚨 EMERGENCY: Database Won't Start

If PostgreSQL keeps crashing:

### Option 1: Scale Resources
```powershell
# PostgreSQL might need more RAM
# Via Dashboard: Service Settings → RAM → Increase to 1GB minimum
```

### Option 2: Force Fresh Database
```powershell
# ⚠️ WARNING: This deletes all data!

# 1. Stop backend
railway service stop --service backend

# 2. Delete postgres
railway service destroy --service postgres

# 3. Railway auto-creates new one
sleep 30

# 4. Run migrations fresh
railway service logs --service backend --follow

# 5. Restart backend
railway service start --service backend
```

### Option 3: Switch to External Database

Create external PostgreSQL and override:
```powershell
# Use managed service (AWS RDS, DigitalOcean, etc)
railway variables set DATABASE_URL="postgresql://user:pass@external-host:5432/dbname"

# Comment out POSTGRES_* variables (they get overridden by DATABASE_URL)

# Restart backend
railway service restart --service backend
```

---

## 📋 CHECKLIST BEFORE RESTARTING

- [ ] PostgreSQL service status: Running
- [ ] Backend variables set correctly (POSTGRES_HOST, PASSWORD, etc)
- [ ] Migrations can run (`python -m alembic upgrade head` locally works)
- [ ] Backend Dockerfile can build locally: `docker build .`  
- [ ] Backend healthcheck path `/health` returns 200
- [ ] DATABASE_URL is empty OR correctly formatted (if set, overrides POSTGRES_*)

---

## 🆘 IF STILL BROKEN

**Collect data for debugging:**
```powershell
# Export all data
$logs = railway logs --service postgres --follow | head -100
$vars = railway variables get --json
$status = railway service status --service postgres

Write-Host "=== POSTGRES STATUS ==="
$status

Write-Host "=== POSTGRES LOGS ==="
$logs

Write-Host "=== VARIABLES ==="
$vars
```

**Then:**
1. Check [DEPLOYMENT_COMPLETE_STATUS.md](./DEPLOYMENT_COMPLETE_STATUS.md)
2. Check [SOLUTION_SUMMARY.md](./SOLUTION_SUMMARY.md)
3. Check [RUNBOOK.md](./backend/RUNBOOK.md) → Troubleshooting section

---

## 📞 SUMMARY

| Issue | Fix |
|-------|-----|
| PostgreSQL won't start | Restart service / Check storage |
| Connection timeout | Verify POSTGRES_* variables |
| Migrations fail | `alembic upgrade head` needed |
| Out of storage | Increase Railway plan or delete old data |
| All else fails | Re-create database from backup |

**Next Action:** Run Step 1 above immediately.
