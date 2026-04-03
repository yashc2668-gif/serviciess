#!/usr/bin/env pwsh
# M2N Production Quick Test

Write-Host ""
Write-Host "=== M2N PRODUCTION STATUS CHECK ===" -ForegroundColor Cyan
Write-Host ""

# Check Railway login
Write-Host "[1] Checking Railway connection..." -ForegroundColor Yellow
try {
    $test = railway whoami 2>&1
    Write-Host "Connected to Railway" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Railway CLI not found. Install from railway.app" -ForegroundColor Red
    exit 1
}

# Get services
Write-Host ""
Write-Host "[2] Checking services..." -ForegroundColor Yellow
$services = railway service list --json 2>&1 | ConvertFrom-Json

foreach ($svc in $services) {
    $stat = $svc.status
    if ($stat -eq "RUNNING" -or $stat -eq "DEPLOYED") {
        Write-Host "  OK: $($svc.name) - $stat" -ForegroundColor Green
    } else {
        Write-Host "  ISSUE: $($svc.name) - $stat" -ForegroundColor Red
    }
}

# Check variables
Write-Host ""
Write-Host "[3] Checking variables..." -ForegroundColor Yellow
$vars = railway variables get --json 2>&1 | ConvertFrom-Json

if ($vars.ENVIRONMENT -eq "production") {
    Write-Host "  OK: ENVIRONMENT set to production" -ForegroundColor Green
} else {
    Write-Host "  WARN: ENVIRONMENT not set to production" -ForegroundColor Yellow
}

if ($vars.DEBUG -eq "False" -or $vars.DEBUG -eq "false") {
    Write-Host "  OK: DEBUG is False" -ForegroundColor Green
} else {
    Write-Host "  WARN: DEBUG should be False" -ForegroundColor Yellow
}

if ($null -ne $vars.ALLOWED_ORIGINS -and $vars.ALLOWED_ORIGINS -ne "") {
    Write-Host "  OK: ALLOWED_ORIGINS is set" -ForegroundColor Green
} else {
    Write-Host "  FAIL: ALLOWED_ORIGINS not set" -ForegroundColor Red
}

# Test health endpoints
Write-Host ""
Write-Host "[4] Testing health endpoints..." -ForegroundColor Yellow

$url = "https://m2n-serviciess-production.up.railway.app"

try {
    $health = Invoke-RestMethod -Uri "$url/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  OK: /health responding" -ForegroundColor Green
    Write-Host "    Status: $($health.status)" -ForegroundColor Gray
} catch {
    Write-Host "  Cannot reach /health (might be starting)" -ForegroundColor Yellow
}

try {
    $ready = Invoke-RestMethod -Uri "$url/health/ready" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  OK: /health/ready - Database is connected" -ForegroundColor Green
} catch {
    Write-Host "  Cannot reach /health/ready (database issue?)" -ForegroundColor Yellow
}

# Show backend logs (last 10 lines)
Write-Host ""
Write-Host "[5] Last backend logs:" -ForegroundColor Yellow
try {
    $logs = railway logs --service backend --lines 10 2>&1
    $logs | ForEach-Object {
        if ($_ -match "ERROR|CRITICAL|FAIL") {
            Write-Host "  [ERROR] $_" -ForegroundColor Red
        } else {
            Write-Host "  $_" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "  Could not fetch logs" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== SUMMARY ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. If services are not RUNNING: railway service restart --service backend"
Write-Host "2. If health check failed: railway logs --service backend --follow"
Write-Host "3. Test API: Open browser to frontend domain"
Write-Host ""
