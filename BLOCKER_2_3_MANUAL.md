# PRODUCTION DEPLOYMENT - MANUAL STEPS FOR BLOCKER #2 & #3

## Status Summary

- **Blocker #1**: ✅ FIXED (vercel.json pushed, commit: bfbc67a)
- **Blocker #2**: ⏳ READY TO FIX (Vercel env var)
- **Blocker #3**: ⏳ READY TO FIX (Railway env vars)

---

## BLOCKER #2: Frontend → Backend Connection

### Problem
Frontend still uses fallback: `http://localhost:8000/api/v1` (dev URL)
Should use: `https://m2n-serviciess-production.up.railway.app/api/v1` (prod URL)

### Solution: Set VITE_API_BASE_URL in Vercel

**Automated Script Ready**: `d:\M2N_SOFTWARE\blocker2-vercel.ps1`

**To run it**:
```powershell
cd d:\M2N_SOFTWARE
powershell -File blocker2-vercel.ps1
```

**What it does**:
1. Authenticates with Vercel (you'll see browser URL, visit and approve)
2. Sets `VITE_API_BASE_URL=https://m2n-serviciess-production.up.railway.app/api/v1` in Production
3. Deploys with `vercel deploy --prod`

**Manual steps if script doesn't work**:
```bash
cd d:\M2N_SOFTWARE\frontend
vercel link --yes
vercel env add VITE_API_BASE_URL
# When prompted: https://m2n-serviciess-production.up.railway.app/api/v1
# Select: Production environment
vercel deploy --prod
```

**Expected result**:
- ✅ Vercel builds and deploys (2-3 min)
- ✅ Frontend now knows backend URL
- ✅ API calls reach Railway

---

## BLOCKER #3: Backend CORS & Production Security

### Problem
Backend doesn't know it's running in production mode
ALLOWED_ORIGINS not set for Vercel domains

### Solution: Set env vars in Railway

**Automated Script Ready**: `d:\M2N_SOFTWARE\blocker3-railway.ps1`

**To run it**:
```powershell
cd d:\M2N_SOFTWARE
powershell -File blocker3-railway.ps1
```

**What it does**:
1. Authenticates with Railway (you'll see browser URL, visit and approve)
2. Asks you to select the backend project
3. Sets 3 environment variables:
   - `ENVIRONMENT=production`
   - `DEBUG=False`
   - `ALLOWED_ORIGINS=[vercel_domains]`
4. Railway auto-restarts the backend

**Manual steps if script doesn't work**:
```bash
railway link --project [your-backend-project-id]
railway variables set ENVIRONMENT production
railway variables set DEBUG False
railway variables set ALLOWED_ORIGINS '["https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app","https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app"]'
```

**Expected result**:
- ✅ Railway restarts backend (1-2 min)
- ✅ Backend now enforces production security
- ✅ CORS headers include Vercel domains
- ✅ Backend accepts requests from frontend

---

## VERIFICATION TESTS (After both fixed)

### Test 1: SPA Routing (should NOT 404)
Open in browser:
```
https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app/forgot-password
```
Expected: Page loads ✅ (not 404)

### Test 2: Backend Health
From terminal:
```bash
curl https://m2n-serviciess-production.up.railway.app/api/v1/health/ready
```
Expected:
```json
{"status": "ok"}
```

### Test 3: CORS Headers
Browser DevTools Console:
```javascript
fetch('https://m2n-serviciess-production.up.railway.app/api/v1/health/ready', {
  headers: {'Origin': 'https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app'}
})
.then(r => console.log('CORS header:', r.headers.get('Access-Control-Allow-Origin')))
```
Expected: Shows Vercel domain ✅

### Test 4: All Auth Pages
Click these (none should 404):
- https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app/login
- https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app/forgot-password
- https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app/reset-password

---

## TIMELINE

```
NOW        - Run blocker2-vercel.ps1 (need to authenticate once)
+3 min     - Vercel deploy completes
+5 min     - Run blocker3-railway.ps1 (need to authenticate once)
+6 min     - Railway restart completes
+10 min    - PRODUCTION READY - All blockers fixed
```

---

## IF YOU GET STUCK

**Vercel script waiting for auth**:
1. Look for URL with `user_code=...`
2. Copy that URL, paste into browser
3. Click "Approve"
4. Script will continue

**Railway script asking for project**:
1. Look at the project list shown
2. Find one with "backend" or "m2n" in name
3. Copy exact project name/ID
4. Paste when prompted

**Script errors**:
- Make sure you're in `d:\M2N_SOFTWARE` directory
- Make sure PowerShell is available
- Try running as Administrator if permission issues

---

## NEXT STEPS

1. **Now**: Run `blocker2-vercel.ps1`
2. **Wait 3 min**: Vercel builds
3. **Then**: Run `blocker3-railway.ps1`
4. **Wait 2 min**: Railway restarts
5. **Finally**: Run verification tests

That's it! All production blockers will be fixed. 🎉
