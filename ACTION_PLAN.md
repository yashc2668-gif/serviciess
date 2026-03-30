# 📋 DEPLOYMENT FIX CHECKLIST - Do This NOW

**Status**: Railway deployment failed ❌ | Frontend vercel.json fixed ✅ | Last issue: ALLOWED_ORIGINS JSON malformed

---

## ✅ TASK 1: Fix Railway Backend (CRITICAL - Do First!)

**Time**: 5-10 minutes

**Option A: Dashboard (Easy)**
```
1. Go to https://railway.app
2. Select m2n-serviciess service
3. Click Variables tab
4. Find ALLOWED_ORIGINS
5. Delete it
6. Create new:
   Name: ALLOWED_ORIGINS
   Value: ["https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app","https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app"]
7. Save
8. Wait 3 minutes for restart
```

**Option B: CLI (Fast)**
```powershell
cd d:\M2N_SOFTWARE\backend
railway link
railway variables set ALLOWED_ORIGINS '["https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app","https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app"]'
```

Then check logs go to green (running) state.

**Verification**:
```powershell
curl https://m2n-serviciess-production.up.railway.app/api/v1/health/ready
```
Should return: `{"status":"ok"}`

---

## ✅ TASK 2: Push Frontend Fix

**Time**: 2 minutes

vercel.json was simplified incorrectly by system. Just fixed it back to correct SPA config.

```powershell
cd d:\M2N_SOFTWARE
git status  # Check if vercel.json shows M (modified)
git add .
git commit -m "fix: restore vercel.json SPA routing config"
git push origin main
```

Vercel auto-redeploys on push. Wait ~3 minutes for Vercel build to complete.

---

## ✅ TASK 3: Set Frontend Env Variable in Vercel

**Time**: 3 minutes

Frontend needs to know backend URL. Currently falling back to localhost.

```
1. Go to https://vercel.com
2. Select m2n-Frontend project
3. Settings → Environment Variables
4. Add new:
   Name: VITE_API_BASE_URL
   Value: https://m2n-serviciess-production.up.railway.app/api/v1
   Scope: Production
5. Save
6. Trigger redeploy (or auto-triggers from git push)
```

Wait for build to complete (green checkmark).

---

## ✅ TASK 4: End-to-End Test

**Time**: 5 minutes

Open browser and test:

1. **SPA Routes Work?**
   - Visit: https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app/forgot-password
   - Should show page, NOT 404
   
2. **Backend Reachable?**
   - Open browser console (F12)
   - Try login (if available)
   - Check Network tab → API calls to backend should succeed
   - Status: 200 (not 403, 401, 500)

3. **CORS Working?**
   - In console run:
     ```javascript
     fetch('https://m2n-serviciess-production.up.railway.app/api/v1/health/ready')
       .then(r => r.json())
       .then(d => console.log(d))
     ```
   - Should print: `{status: "ok"}`
   - NOT: CORS error

---

## Timeline

| Task | Time | Cumulative |
|------|------|-----------|
| Fix Railway ALLOWED_ORIGINS | 5 min | 5 min |
| Wait for Railway restart | 3 min | 8 min |
| Push frontend fix | 2 min | 10 min |
| Wait for Vercel build | 3 min | 13 min |
| Set Vercel env var | 3 min | 16 min |
| Trigger Vercel redeploy | 3 min | 19 min |
| Test in browser | 5 min | 24 min |

**Total: ~25 minutes**

---

## If Something Fails

**Railway stuck on deploying?**
- Go to deployments, click latest, scroll down
- Look for error in logs
- Common: JSON syntax error → check ALLOWED_ORIGINS quotes and brackets

**Frontend still 404s?**
- Check vercel.json got committed and deployed
- Check build logs in Vercel

**Frontend can't reach backend?**
- Check VITE_API_BASE_URL is set in Vercel
- Check spelling (exact: `https://m2n-serviciess-production.up.railway.app/api/v1`)
- Check backend is running (green in Railway)

**CORS error in console?**
- Check ALLOWED_ORIGINS includes your Vercel domain
- Check backend CSP headers (should be set in config.py)
- Restart Railway service

---

## Just Do This:

```powershell
# 1. Fix Railway (choose one option above)

# 2. Commit and push frontend changes
cd d:\M2N_SOFTWARE
git add .
git commit -m "fix: restore vercel.json and frontend config"
git push origin main

# 3. Set Vercel env var via https://vercel.com dashboard

# 4. Wait ~25 minutes and test all 4 endpoints in browser

# Done! ✅
```

---

**Questions?** Check FIX_RAILWAY.md for detailed steps.

**Need help?** Run the verification commands above.

**Ab kya karna hoga? → YE KARO! (Now do this!)**
