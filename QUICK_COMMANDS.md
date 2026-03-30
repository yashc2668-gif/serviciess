# ⚡ QUICK COMMANDS - Copy & Paste Ready

## Monitor Deployment Status

```powershell
# Check latest deployment
cd d:\M2N_SOFTWARE\backend
railway deployment list | Select-Object -First 1

# Check if it changed to SUCCESS
railway service status --service m2n-serviciess

# Check Postgres status
railway service status --service Postgres
```

## Redeploy Backend (After Postgres Fixed)

```powershell
cd d:\M2N_SOFTWARE\backend
railway deployment redeploy --service m2n-serviciess -y
```

## Check Backend Health

```powershell
# Direct URL call
Invoke-WebRequest -Uri "https://m2n-serviciess-production.up.railway.app/health" -Method GET

# Test from PowerShell
$response = Invoke-WebRequest "https://m2n-serviciess-production.up.railway.app/health" -ErrorAction SilentlyContinue
$response.StatusCode
```

## Test CORS (From Browser Console)

```javascript
// Open browser at: https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app
// Open DevTools: F12
// Paste this in Console:

fetch('https://m2n-serviciess-production.up.railway.app/health')
  .then(r => r.json())
  .then(d => console.log('✅ Success:', d))
  .catch(e => console.error('❌ Failed:', e.message))
```

## Check Environment Variables

```powershell
# See what's set on Railway
railway variables

# See just ALLOWED_ORIGINS
railway variables | Select-String "ALLOWED_ORIGINS"

# See DATABASE_URL
railway variables | Select-String "DATABASE_URL"
```

---

## Links

- **Railway Project**: https://railway.app/project/21f8b4ef-f25d-4ec2-8ef9-556548a2ad82
- **Vercel Project**: https://vercel.com/projects  
- **GitHub Repo**: https://github.com/yashc2668-gif/serviciess
- **Frontend Live**: https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app
- **Backend URL** (when fixed): https://m2n-serviciess-production.up.railway.app

---

## Run These In Order

### 1. Check Current Status
```powershell
cd d:\M2N_SOFTWARE\backend
railway deployment list | Select-Object -First 3
```

### 2. If Postgres FAILED, Manual Fix Required
Go to: https://railway.app → Postgres service → Deployments → Restart

### 3. Wait 5 Minutes, Then Check Again
```powershell
Start-Sleep -Seconds 300
railway deployment list | Select-Object -First 1
```

### 4. If Status Still FAILED, Redeploy
```powershell
railway deployment redeploy --service m2n-serviciess -y
Start-Sleep -Seconds 300
railway deployment list | Select-Object -First 1
```

### 5. Final Test
```powershell
curl https://m2n-serviciess-production.up.railway.app/health
```

Should return: `{"status":"ok","app":"M2N Construction ERP","environment":"production"}`

---

**Save this file - you'll need these commands!**
