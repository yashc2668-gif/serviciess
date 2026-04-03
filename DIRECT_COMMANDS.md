# BLOCKER #2 & #3 - DIRECT EXECUTION (Copy-Paste)

## Blocker #2: Set VITE_API_BASE_URL in Vercel

**Open Terminal and run these commands:**

```powershell
# Go to frontend
cd d:\M2N_SOFTWARE\frontend

# Link to Vercel project (one-time)
vercel link

# Create .env.production locally
@"
VITE_API_BASE_URL=https://m2n-serviciess-production.up.railway.app/api/v1
"@ | Out-File .env.production -Encoding UTF8

# Deploy to production (this sets env vars and deploys)
vercel deploy --prod
```

**What happens:**
- Vercel will ask for project confirmation
- Click "yes" when asked
- Vercel builds and deploys (~3 minutes)
- Frontend now has correct backend URL ✅

---

## Blocker #3: Set Railway Environment Variables

**Open Terminal and run these commands:**

```powershell
# Install Railway CLI (one-time)
npm install -g @railway/cli

# Login to Railway
railway login
# (Browser will open, click approve)

# Link to backend project
railway link

# Set ENVIRONMENT
railway variables set ENVIRONMENT production

# Set DEBUG
railway variables set DEBUG False

# Set ALLOWED_ORIGINS (PRODUCTION - No localhost!)
railway variables set ALLOWED_ORIGINS='["https://m2n-frontend.vercel.app","https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app","https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app"]'
```

**What happens:**
- Railway restarts backend automatically (~2 minutes)
- Backend now enforces production security ✅
- ALLOWED_ORIGINS includes Vercel domains ✅

---

## Verification After Both Complete

**Test 1: Check SPA Routes**
```
https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app/forgot-password
```
Should load ✅ (not 404)

**Test 2: Check Backend (Terminal)**
```bash
curl https://m2n-serviciess-production.up.railway.app/api/v1/health/ready
```
Should return: `{"status":"ok"}` ✅

**Test 3: Check CORS (Browser DevTools Console)**
```javascript
fetch('https://m2n-serviciess-production.up.railway.app/api/v1/health/ready')
.then(r => r.json()).then(console.log)
```
Should succeed (no CORS error) ✅

---

## Timeline

```
00:00 - Deploy Vercel (blocker #2)
00:03 - Vercel complete
00:03 - Configure Railway (blocker #3)
00:05 - Railway complete
00:05 - PRODUCTION READY
```

Total: ~5 minutes

Done! 🎉
