# 🔧 FIX RAILWAY DEPLOYMENT (ALLOWED_ORIGINS Issue)

## Problem
Backend deployment failing due to malformed ALLOWED_ORIGINS JSON.

Error: `json.decoder.JSONDecodeError: Expecting value: line 1 column 2`

This means the JSON was invalid (wrong format, wrong quotes, etc).

---

## Solution: Set ALLOWED_ORIGINS Correctly

### Step 1: Open Railway Dashboard
Go to: https://railway.app/

### Step 2: Select Backend Service
Click on: `m2n-serviciess` project → Backend service

### Step 3: Go to Variables
Click: "Variables" tab

### Step 4: Find ALLOWED_ORIGINS
Look for the variable named: `ALLOWED_ORIGINS`

### Step 5: Delete and Recreate
1. Click delete/trash icon next to ALLOWED_ORIGINS
2. Click "New Variable"
3. Enter:
   - **Name**: `ALLOWED_ORIGINS`
   - **Value**: Copy exactly this (with quotes):
```
["https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app","https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app"]
```

### Step 6: Save
Click "Save" → Railway restarts backend

### Step 7: Wait
Wait 2-3 minutes for container restart

### Step 8: Check Status
Go back to deployments → Should show "Running" (green)

---

## OR Use Railway CLI (Faster)

Open PowerShell:

```powershell
railway link
```

Then:

```powershell
railway variables set ALLOWED_ORIGINS '["https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app","https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app"]'
```

---

## Verify It Works

After Railway restarts (~2-3 min), test:

```bash
curl https://m2n-serviciess-production.up.railway.app/api/v1/health/ready
```

Should return:
```json
{"status":"ok"}
```

If you get this, deployment is ✅ FIXED!

---

## What If It Still Fails?

Check the logs:
1. Go to Railway dashboard
2. Select m2n-serviciess
3. Click "Deployments" tab
4. Click latest deployment
5. Look at logs

Common issues:
- Missing quotes: `["domain"]` ✅ vs `[domain]` ❌
- Wrong quotes: `["domain"]` ✅ vs `['domain']` ❌
- Extra spaces: Should be no spaces between brackets and quotes
- Invalid domain name: Check spelling

---

## Full Env Vars Check

Also verify these are set:
```
ENVIRONMENT=production
DEBUG=False
ALLOWED_ORIGINS=["https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app","https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app"]
```

All 3 should be there. If any missing, add them.

---

## Frontend Fix

Also fixed `frontend/vercel.json` to correct SPA config. 

Redeploy frontend:
```powershell
cd d:\M2N_SOFTWARE\frontend
git add .
git commit -m "fix: restore vercel.json SPA config"
git push origin main
```

Vercel auto-redeploys on push.

---

## Timeline

1. Fix ALLOWED_ORIGINS in Railway (5 min)
2. Wait for Railway restart (3 min)
3. Redeploy frontend via git push (instant auto-trigger)
4. Wait for Vercel build (3 min)
5. Test in browser (2 min)

**Total: ~13 minutes**

---

**Do this now and message results!**
