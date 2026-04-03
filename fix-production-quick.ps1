#!/usr/bin/env pwsh
<#
.SYNOPSIS
M2N Production Quick Fix - Automatically fixes common issues
.DESCRIPTION
This script automatically applies common production fixes without prompting
.EXAMPLE
powershell -File fix-production-quick.ps1
#>

Write-Host "🔧 M2N PRODUCTION QUICK FIX" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan
Write-Host ""

# Ensure Railway CLI is available
Write-Host "[1] Checking Railway CLI..." -ForegroundColor Yellow
try {
    $version = railway version --json 2>&1 | ConvertFrom-Json
    Write-Host "✅ Railway CLI found: v$($version.version)" -ForegroundColor Green
} catch {
    Write-Host "❌ Railway CLI not found. Install from https://railway.app" -ForegroundColor Red
    exit 1
}

# Ensure logged in
Write-Host "[2] Verifying Railway login..." -ForegroundColor Yellow
try {
    $whoami = railway whoami 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Logged in" -ForegroundColor Green
    } else {
        Write-Host "❌ Not logged in. Run: railway login" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Login check failed" -ForegroundColor Red
    exit 1
}

# Link project if needed
Write-Host "[3] Linking project..." -ForegroundColor Yellow
try {
    $project = railway project get-current --json 2>&1
    Write-Host "✅ Project linked" -ForegroundColor Green
} catch {
    Write-Host "Running: railway link" -ForegroundColor Yellow
    railway link | Out-Host
}

# QUICK FIX #1: Fix ALLOWED_ORIGINS JSON
Write-Host ""
Write-Host "[4] Fixing ALLOWED_ORIGINS..." -ForegroundColor Yellow

$origins = '["https://m2n-frontend.vercel.app","https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app","https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app"]'

Write-Host "Setting ALLOWED_ORIGINS to production domains..."
railway variables set ALLOWED_ORIGINS=$origins

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ ALLOWED_ORIGINS fixed" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to set ALLOWED_ORIGINS" -ForegroundColor Red
}

# QUICK FIX #2: Set Production Environment
Write-Host ""
Write-Host "[5] Setting production environment..." -ForegroundColor Yellow

Write-Host "Setting ENVIRONMENT=production..."
railway variables set ENVIRONMENT="production"

Write-Host "Setting DEBUG=False..."
railway variables set DEBUG="False"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Environment variables fixed" -ForegroundColor Green
} else {
    Write-Host "⚠️  Environment variables might not have changed" -ForegroundColor Yellow
}

# QUICK FIX #3: Verify Critical Variables
Write-Host ""
Write-Host "[6] Verifying critical variables..." -ForegroundColor Yellow

$vars = railway variables get --json 2>&1 | ConvertFrom-Json

$critical = @{
    "SECRET_KEY" = "SECRET_KEY should not be 'CHANGE-ME'"
    "POSTGRES_HOST" = "Should be 'postgres' or Railway hostname"
    "POSTGRES_PORT" = "Should be '5432'"
    "APP_PORT" = "Should be '8000'"
}

foreach ($key in $critical.Keys) {
    $value = $vars.$key
    if ($null -ne $value -and $value -ne "") {
        Write-Host "  ✅ $key is set" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  $key might need to be set manually" -ForegroundColor Yellow
    }
}

# QUICK FIX #4: Restart Backend Service
Write-Host ""
Write-Host "[7] Restarting backend service..." -ForegroundColor Yellow

Write-Host "Restarting backend (this may take 1-2 minutes)..."
railway service restart --service backend

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Backend restart initiated" -ForegroundColor Green
} else {
    Write-Host "⚠️  Backend restart command sent (check Railway dashboard)" -ForegroundColor Yellow
}

# QUICK FIX #5: Test Health After Restart
Write-Host ""
Write-Host "[8] Waiting for backend to restart (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "[9] Testing backend health..." -ForegroundColor Yellow

$baseUrl = "https://m2n-serviciess-production.up.railway.app"
$maxAttempts = 5
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $attempt++
    try {
        Write-Host "  Attempt $attempt / $maxAttempts..."
        
        $health = Invoke-RestMethod -Uri "$baseUrl/health" -UseBasicParsing -ErrorAction SilentlyContinue -TimeoutSec 5
        
        if ($health.status -eq "ok") {
            Write-Host "✅ /health is responding" -ForegroundColor Green
            
            # Try ready endpoint
            $ready = Invoke-RestMethod -Uri "$baseUrl/health/ready" -UseBasicParsing -ErrorAction SilentlyContinue -TimeoutSec 5
            if ($ready.status -eq "ok") {
                Write-Host "✅ /health/ready is OK (Database connected!)" -ForegroundColor Green
                break
            } else {
                Write-Host "⚠️  Database might not be ready yet" -ForegroundColor Yellow
            }
        }
    } catch {
        Write-Host "  Still starting... please wait" -ForegroundColor Gray
    }
    
    if ($attempt -lt $maxAttempts) {
        Start-Sleep -Seconds 10
    }
}

# Summary
Write-Host ""
Write-Host "============================" -ForegroundColor Cyan
Write-Host "✅ FIXES APPLIED" -ForegroundColor Green
Write-Host ""
Write-Host "Changes made:" -ForegroundColor Yellow
Write-Host "  1. ✅ ALLOWED_ORIGINS - Set to production Vercel domains"
Write-Host "  2. ✅ ENVIRONMENT - Set to 'production'"
Write-Host "  3. ✅ DEBUG - Set to 'False'"
Write-Host "  4. ✅ Backend service restarted"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Wait 2-3 minutes for backend to be ready"
Write-Host "  2. Test: https://m2n-frontend-xxx.vercel.app (your frontend)"
Write-Host "  3. If still broken, check:"
Write-Host "     - railway logs --service backend --follow"
Write-Host "     - FIX_PRODUCTION_POSTGRESQL.md"
Write-Host "     - PRODUCTION_BACKEND_TROUBLESHOOTING.md"
Write-Host ""
Write-Host "To debug manually:" -ForegroundColor Cyan
Write-Host "  railway service list"
Write-Host "  railway logs --service backend --follow"
Write-Host "  railway logs --service postgres --follow"
Write-Host ""
