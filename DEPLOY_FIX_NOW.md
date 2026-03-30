# 🚨 DEPLOY FAIL FIX - QUICK STEPS

## Problem
Railway deployment failing at healthcheck because **ALLOWED_ORIGINS is empty `[]`**

railwayCLI rejected our attempts to set the variable. We'll use the **Dashboard** instead.

---

## INSTANT FIX (2 minutes)

### Step 1: Go to Railway Dashboard
```
https://railway.app/project/21f8b4ef-f25d-4ec2-8ef9-556548a2ad82/deployments
```

Or:
1. Open https://railway.app
2. Click **m2n-serviciess** project
3. Click **m2n-serviciess** service  
4. Click **Variables** tab

### Step 2: Add ALLOWED_ORIGINS

Click "+ New Variable"

**Name**: `ALLOWED_ORIGINS`

**Value**: Copy-paste exactly this:
```
https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app,https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app,http://localhost:5173
```

### Step 3: Save
Click **Save** button

### Step 4: Redeploy
Go to **Deployments** tab → Click **Redeploy** on latest deployment

OR click the **Redeploy** button at top

### Step 5: Wait
Wait 3-5 minutes for healthcheck to pass ✅

---

## Verify It Worked

Once deployment shows **RUNNING** (green):

```powershell
curl https://m2n-serviciess-production.up.railway.app/api/v1/health/ready
```

Should return: `{"status":"ok"}`

---

## Why This Failed

1. ALLOWED_ORIGINS was set to empty `[]`
2. Application needs at least one allowed origin
3. Healthcheck failed because CORS validation failed
4. Railway CLI has issues parsing special characters in variable values

Solution: Use dashboard UI instead of CLI.

---

**Do this now - should take 2 minutes total!**
