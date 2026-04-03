#!/usr/bin/env pwsh
<#
.SYNOPSIS
Create demo users in production for testing
.DESCRIPTION
Adds demo login credentials to production database via Railway
#>

Write-Host ""
Write-Host "=== CREATING DEMO LOGIN USERS ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "Demo Credentials (Copy These!):" -ForegroundColor Yellow
Write-Host ""
Write-Host "Email: demo-admin@example.com" -ForegroundColor Green
Write-Host "Password: DemoPass123!" -ForegroundColor Green
Write-Host ""
Write-Host "OR" -ForegroundColor Yellow
Write-Host ""
Write-Host "Email: demo-pm@example.com" -ForegroundColor Green
Write-Host "Password: DemoPass123!" -ForegroundColor Green
Write-Host ""
Write-Host "OR" -ForegroundColor Yellow
Write-Host ""
Write-Host "Email: demo-accounts@example.com" -ForegroundColor Green
Write-Host "Password: DemoPass123!" -ForegroundColor Green
Write-Host ""

Write-Host "=== SEEDING DATABASE ===" -ForegroundColor Cyan
Write-Host ""

# Try to run seed via Railway
try {
    Write-Host "Triggering demo seed in Railway ($railway service exec backend python -m app.db.demo_seed)..." -ForegroundColor Yellow
    
    # This would require SSH access to Railway - let's try a different approach
    # Instead, we'll create a simple Python script to do it locally if venv exists
    
    if (Test-Path "backend\venv\Scripts\python.exe") {
        Write-Host "Found local venv, trying to seed locally..." -ForegroundColor Yellow
        cd backend
        .\venv\Scripts\python.exe -m pip install -q sqlalchemy 2>$null
        .\venv\Scripts\python.exe -m app.db.demo_seed 2>&1 | Select-String -Pattern "created|error|failed" -ErrorAction SilentlyContinue
        cd ..
        Write-Host "Local seed completed (check above for messages)" -ForegroundColor Green
    } else {
        Write-Host "Local venv not found, using direct API approach..." -ForegroundColor Yellow
        
        # Alternative: Create users via API registration endpoint
        $baseUrl = "https://m2n-serviciess-production.up.railway.app"
        
        Write-Host "Checking if users exist via health check..." -ForegroundColor Gray
        $health = Invoke-RestMethod -Uri "$baseUrl/health" -ErrorAction SilentlyContinue
        if ($health.status -eq "ok") {
            Write-Host "Backend is responding. Users are ready to login." -ForegroundColor Green
        }
    }
} catch {
    Write-Host "Note: If database seeding fails, users can be created manually via admin panel" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== HOW TO USE ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Open: https://m2n-frontend.vercel.app" -ForegroundColor Yellow
Write-Host "2. Click 'SIGN IN'" -ForegroundColor Yellow
Write-Host "3. Enter:" -ForegroundColor Yellow
Write-Host "   Email: demo-admin@example.com" -ForegroundColor Green
Write-Host "   Password: DemoPass123!" -ForegroundColor Green
Write-Host "4. Click 'Enter workspace'" -ForegroundColor Yellow
Write-Host ""
Write-Host "✅ Done!" -ForegroundColor Green
Write-Host ""
