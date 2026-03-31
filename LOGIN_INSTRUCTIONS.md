# M2N ERP - Login Instructions (UPDATED)

## ✅ Status: FULLY OPERATIONAL

The login system is now working correctly. The frontend can communicate with the production backend.

## 🔐 How to Access

### Frontend URL
https://m2n-frontend.vercel.app

### Create New Account
1. Click **"Forgot your password?"** link on login page, OR
2. Go directly to registration at: https://m2n-frontend.vercel.app

### Register a New Account
- **Full Name**: Any name
- **Email**: Any valid email
- **Password**: Must have:
  - Minimum 8 characters
  - At least 1 uppercase letter
  - At least 1 number
  - At least 1 special character (!@#$%^&* etc)
- **Role**: Select "viewer" (default)

Example: `Site Manager / manager123@company.com / Manager@123!`

### Test Credentials (Pre-configured)
- **Email**: test2025@example.com
- **Password**: TestPass123!

## 🧪 Testing the API Directly

### Login Endpoint
```bash
POST https://m2n-serviciess-production.up.railway.app/api/v1/auth/login
Content-Type: application/json

{
  "email": "test2025@example.com",
  "password": "TestPass123!"
}
```

### Response
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600,
  "csrf_token": "...",
  "user": {
    "id": 1,
    "email": "test2025@example.com",
    "full_name": "Test User",
    "role": "viewer",
    "is_active": true
  }
}
```

## 🔧 Technical Details

### What Was Fixed
The frontend environment variable `VITE_API_BASE_URL` was not configured on Vercel, causing it to default to localhost instead of the production backend on Railway.

### Current Configuration
- **Production Backend**: https://m2n-serviciess-production.up.railway.app/api/v1
- **Development Backend**: http://localhost:8000/api/v1
- **Frontend**: https://m2n-frontend.vercel.app

### Verification Checklist
- ✅ Frontend loads (200 OK)
- ✅ Backend responds to login requests
- ✅ JWT tokens are generated correctly
- ✅ Protected endpoints work with tokens
- ✅ CORS headers are correct
- ✅ User registration works
- ✅ Session storage configured

## 📞 Support

If you encounter any issues:

1. **Clear browser cache** and try again
2. **Check the console** for error messages (F12 → Console tab)
3. **Verify email address** has been registered
4. **Ensure password** meets requirements (8+ chars, uppercase, number, special char)

---

**Last Updated**: 2025-03-31 06:55 UTC
**Status**: Production Ready ✅
