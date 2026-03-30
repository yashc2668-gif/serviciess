# BLOCKER #2 & #3 - EXECUTION GUIDE

## Quick Start (Copy-Paste)

```powershell
cd d:\M2N_SOFTWARE
powershell -File blocker2-vercel.ps1
```

Then:

```powershell
cd d:\M2N_SOFTWARE
powershell -File blocker3-railway.ps1
```

---

## Detailed Walkthrough

### BLOCKER #2: VERCEL ENV VAR

When you run `blocker2-vercel.ps1`, you will see:

```
=== Vercel Environment Variable Setup - Blocker #2 ===
[1/8] Checking Vercel CLI...
OK: Vercel CLI ready
[2/8] Navigating to frontend directory...
OK: In d:\M2N_SOFTWARE\frontend
[3/8] Checking Vercel project link...
Linking project...
OK: Project linked
[4/8] Current environment variables:

> No existing credentials found. Please log in:
> 
  Visit https://vercel.com/oauth/device?user_code=VXDM-TRXV

/ Waiting for authentication...
```

**ACTION**: 
1. Copy the URL: `https://vercel.com/oauth/device?user_code=VXDM-TRXV`
2. Paste into browser
3. Click "Approve"
4. Come back to terminal

Script will continue automatically. Wait for completion (~3 min).

---

### BLOCKER #3: RAILWAY ENV VARS

When you run `blocker3-railway.ps1`, you will see:

```
=== Railway Environment Variable Setup - Blocker #3 ===
[1/6] Checking Railway CLI...
[2/6] Checking Railway authentication...
Starting Railway login...

> Visit https://railway.app/oauth/device?user_code=XXXX

/ Waiting for authentication...
```

**ACTION**:
1. Copy the URL: `https://railway.app/oauth/device?user_code=XXXX`
2. Paste into browser
3. Click "Approve"
4. Come back to terminal

Script will ask:

```
[3/6] Available projects:
- project-xyz (backend-prod-m2n)
- project-abc (staging-db)

Enter project name/ID containing backend
```

**ACTION**: 
1. Look at the list
2. Find one with "backend" or "m2n" in the name
3. Copy its exact name
4. Type it and press Enter

Script will continue and set all 3 variables automatically.

---

## What Gets Set

### In Vercel (Blocker #2):
```
VITE_API_BASE_URL = https://m2n-serviciess-production.up.railway.app/api/v1
Scope: Production
```

### In Railway (Blocker #3):
```
ENVIRONMENT = production
DEBUG = False
ALLOWED_ORIGINS = ["https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app","https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app"]
```

---

## Timeline

```
00:00 - Run blocker2-vercel.ps1
00:01 - Browser: Approve Vercel auth
00:02 - Script settings env vars
00:05 - Vercel deploy starts
00:08 - Vercel deploy complete (BLOCKER #2 FIXED) ✅

00:08 - Run blocker3-railway.ps1
00:09 - Browser: Approve Railway auth
00:10 - Script asks for project
00:11 - You paste project name
00:12 - Script sets 3 env vars
00:13 - Railway auto-restart starts
00:15 - Railway restart complete (BLOCKER #3 FIXED) ✅

RESULT: Production fully working!
```

---

## Testing After Both Complete

**Test 1**: Open browser:
```
https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app/forgot-password
```
Should load (not 404) ✅

**Test 2**: DevTools console:
```javascript
fetch('https://m2n-serviciess-production.up.railway.app/api/v1/health/ready')
.then(r => r.json()).then(console.log)
```
Should show `{status: "ok"}` ✅

---

## If Something Goes Wrong

**Q: Script hangs at authentication?**
A: Just wait 2-3 minutes. If still hangs, close it (Ctrl+C) and run again.

**Q: Can't find project name in Railway?**
A: Look for any name containing "m2n" or "backend". Copy exact spelling.

**Q: Vercel deploy fails?**
A: Run manually: `cd frontend && vercel deploy --prod`

**Q: Railway won't set variables?**
A: Run manually: `railway variables set ENVIRONMENT production`

---

## You Are Ready!

All scripts are in: `d:\M2N_SOFTWARE\`

Just run:
```powershell
powershell -File blocker2-vercel.ps1
```

Then:
```powershell
powershell -File blocker3-railway.ps1
```

That's it! 🚀
