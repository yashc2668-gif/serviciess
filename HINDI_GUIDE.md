# BLOCKER #2 & #3 - HINDI GUIDE (बिलकुल आसान)

## 🎯 Ab Kya Karna Hai?

Tum ko 2 cheezon ko set karna hai:
1. **Vercel** mein URL set karo (Blocker #2)
2. **Railway** mein 3 cheezein set karo (Blocker #3)

---

## 🚀 STEP-BY-STEP (Bilkul Simple)

### **PEHLA KAAM: Vercel Deploy Karo**

**PowerShell khol lo** (Windows key + R, type PowerShell)

**Copy-paste karo:**
```powershell
cd d:\M2N_SOFTWARE\frontend
vercel deploy --prod
```

**Kya hona chahiye:**
- Terminal mein "Vercel" likha dikhega
- "Project linked" likha dikhegi
- "Deploy starting..." likha dikhegi
- Build hona start hoga (3-5 minute wait karna)

**Jab ye likha dikhे "Deployment ready"**, toh agle step karo.

---

### **DOOSRA KAAM: Railway CLI Install Karo**

**Same PowerShell mein copy-paste karo:**
```powershell
npm install -g @railway/cli
```

**Kya hona chahiye:**
- Installation start hoga
- "added XXX packages" likha ayega
- Khatam ho jayega (1-2 minute)

---

### **TEESRA KAAM: Railway Login Karo**

**Whi PowerShell mein copy-paste karo:**
```powershell
railway login
```

**Kya hona chahiye:**
- "Visit https://railway.app/oauth/..." likha ayega
- URL browser mein khul jayega
- Approve button dikhega, click karo
- PowerShell mein "Authenticated" likha ayega

---

### **CHAUTHA KAAM: Railway Project Link Karo**

**Whi PowerShell mein copy-paste karo:**
```powershell
railway link
```

**Kya hona chahiye:**
- Projects ki list dikhegi
- "m2n-backend-..." likha hoga
- Usse select karo (name type karo ya number)

---

### **PAANCHWA KAAM: Railway Ko 3 Cheezein Batao**

**Ek-ek copy-paste karo:**

**Pehli cheez:**
```powershell
railway variables set ENVIRONMENT production
```

**Doosri cheez:**
```powershell
railway variables set DEBUG False
```

**Teesri cheez (yeh ek-dum long hai, careful copy karna):**
```powershell
railway variables set ALLOWED_ORIGINS '["https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app","https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app"]'
```

**Kya hona chahiye:**
- Har command ke baad "✓ Added" likha ayega
- Railway backend restart hoga (2-3 minute)

---

## ✅ VERIFICATION (Test Karo)

**Browser mein open karo:**
```
https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app/forgot-password
```

**Expected:**
- Page load hona chahiye ✅
- 404 ERROR nahi aana chahiye ❌

**Agar page load ho gaya, matlab sab kuch sahi hai!** 🎉

---

## 📋 QUICK TIMELINE

| Time | Kya Karna | Wait Time |
|------|-----------|-----------|
| 00:00 | `vercel deploy --prod` | **3-5 min** ⏳ |
| 05:00 | `railway login` | Browser approve |
| 05:30 | `railway link` | Project select |
| 06:00 | 3 variable commands | **2 min** ⏳ |
| 08:00 | Test browser | ✅ DONE |

---

## ⚠️ KYA HO SAKTI HAI Issue?

### Q: "Unknown command" likha aya?
**A:** Vercel CLI nahi installed. Run karo:
```powershell
npm install -g vercel
npm install -g @railway/cli
```

### Q: "Not authenticated" likha aya?
**A:** Login karo:
```powershell
vercel login
railway login
```

### Q: Deploy nahi ho raha?
**A:** Try karo:
```powershell
cd d:\M2N_SOFTWARE\frontend
vercel deploy --prod --confirm
```

### Q: Railway project nahi dikha?
**A:** List dekho:
```powershell
railway projects
```
Usme se correct name copy karo.

---

## 🎯 FINAL CHECK

Ab test karo:

1. Browser: `/forgot-password` page open hona chahiye ✅
2. DevTools console mein run karo:
```javascript
fetch('https://m2n-serviciess-production.up.railway.app/api/v1/health/ready')
.then(r => r.json()).then(console.log)
```
Response aana chahiye ✅

---

## 🎉 DONE!

Jab ye 2 kaam complete ho gaye, matlab **production ready!**

Bilkul simple:
1. Vercel → `vercel deploy --prod`
2. Railway → 3 variables set
3. Test → Browser mein check

**Bas ho gaya!** 🚀

---

**Koi confusion ho toh email karo ya msg karo.**
**Ab shuru karo!**
