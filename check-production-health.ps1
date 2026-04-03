#!/usr/bin/env pwsh
<#
.SYNOPSIS
M2N Production Health Check & AutoFix Script
.DESCRIPTION
Automatically diagnoses and fixes common production issues
.EXAMPLE
powershell -File check-production-health.ps1
#>

Write-Host "🔍 M2N PRODUCTION HEALTH CHECK" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Login Check
Write-Host "[1] Checking Railway Login..." -ForegroundColor Yellow
try {
    $whoami = railway whoami 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK Logged in to Railway" -ForegroundColor Green
    } else {
        Write-Host "FAIL Not logged in. Running: railway login" -ForegroundColor Red
        railway login
    }
} catch {
    Write-Host "FAIL Railway CLI not found. Install from https://railway.app" -ForegroundColor Red
    exit 1
}

# Step 2: Project Link Check
Write-Host ""
Write-Host "[2] Checking Project Link..." -ForegroundColor Yellow
try {
    $project = railway project get-current 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK Project linked: $project" -ForegroundColor Green
    } else {
        Write-Host "FAIL Project not linked. Running: railway link" -ForegroundColor Red
        railway link
    }
} catch {
    Write-Host "FAIL Could not get project" -ForegroundColor Red
}

# Step 3: Service Status
Write-Host ""
Write-Host "[3] Service Status..." -ForegroundColor Yellow
Write-Host ""

$services = railway service list --json 2>&1 | ConvertFrom-Json

foreach ($service in $services) {
    $name = $service.name
    $status = $service.status
    
    if ($status -eq "RUNNING" -or $status -eq "DEPLOYED") {
        Write-Host "  OK $name : $status" -ForegroundColor Green
    } elseif ($status -eq "BUILDING" -or $status -eq "DEPLOYING") {
        Write-Host "  WAIT $name : $status (in progress...)" -ForegroundColor Yellow
    } else {
        Write-Host "  FAIL $name : $status" -ForegroundColor Red
    }
}

# Step 4: Environment Variables Check
Write-Host ""
Write-Host "[4] Checking Critical Variables..." -ForegroundColor Yellow
Write-Host ""

$requiredVars = @(
    "SECRET_KEY",
    "ENVIRONMENT",
    "DEBUG",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "ALLOWED_ORIGINS"
)

$vars = railway variables get --json 2>&1 | ConvertFrom-Json

foreach ($varName in $requiredVars) {
    $value = $vars.$varName
    
    if ($null -ne $value -and $value -ne "") {
        if ($varName -eq "SECRET_KEY" -and $value -eq "CHANGE-ME") {
            Write-Host "  WARN $varName = INSECURE DEFAULT" -ForegroundColor Red
        } elseif ($varName -eq "DEBUG" -and $value -eq "True") {
            Write-Host "  WARN $varName = True (should be False in production)" -ForegroundColor Yellow
        } elseif ($varName -eq "ALLOWED_ORIGINS") {
            $len = $value.Length
            Write-Host "  OK $varName = set ($len chars)" -ForegroundColor Green
        } else {
            Write-Host "  OK $varName = set" -ForegroundColor Green
        }
    } else {
        Write-Host "  FAIL $varName = NOT SET" -ForegroundColor Red
    }
}

# Step 5: Backend Logs (Last 20 lines)
Write-Host ""
Write-Host "[5] Recent Backend Logs..." -ForegroundColor Yellow
Write-Host ""

try {
    $logs = railway logs --service backend --lines 20 2>&1
    if ($logs) {
        $logs | ForEach-Object {
            if ($_ -match "ERROR|CRITICAL|FAILED") {
                Write-Host "  ❌ $_" -ForegroundColor Red
            } elseif ($_ -match "WARNING") {
                Write-Host "  ⚠️  $_" -ForegroundColor Yellow
            } else {
                Write-Host "  $_" -ForegroundColor Gray
            }
        }
    }
} catch {
    Write-Host "  Could not fetch logs" -ForegroundColor Gray
}

# Step 6: Health Check
Write-Host ""
Write-Host "[6] Testing Backend Health..." -ForegroundColor Yellow
Write-Host ""

$baseUrl = "https://m2n-serviciess-production.up.railway.app"

try {
    $health = Invoke-RestMethod -Uri "$baseUrl/health" -UseBasicParsing -ErrorAction SilentlyContinue
    if ($health.status -eq "ok") {
        Write-Host "  ✅ /health - OK" -ForegroundColor Green
    } else {
        Write-Host "  ❌ /health - Unexpected response: $health" -ForegroundColor Red
    }
} catch {
    Write-Host "  ❌ /health - Request failed" -ForegroundColor Red
}

try {
    $ready = Invoke-RestMethod -Uri "$baseUrl/health/ready" -UseBasicParsing -ErrorAction SilentlyContinue
    if ($ready.status -eq "ok") {
        Write-Host "  ✅ /health/ready - OK (Database connected)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ /health/ready - Database might not be connected" -ForegroundColor Red
    }
} catch {
    Write-Host "  ❌ /health/ready - Request failed (DB issue?)" -ForegroundColor Red
}

# Step 7: CORS Check
Write-Host ""
Write-Host "[7] CORS Configuration..." -ForegroundColor Yellow
Write-Host ""

$corsVar = $vars.ALLOWED_ORIGINS
if ($corsVar -match 'https://m2n-frontend') {
    Write-Host "  OK ALLOWED_ORIGINS configured for Vercel" -ForegroundColor Green
} else {
    Write-Host "  FAIL ALLOWED_ORIGINS missing Vercel domains" -ForegroundColor Red
}

# Summary
Write-Host ""
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "📋 SUMMARY" -ForegroundColor Cyan
Write-Host ""
Write-Host "If you see ❌ issues above, check:" -ForegroundColor Yellow
Write-Host "  1. FIX_PRODUCTION_POSTGRESQL.md    (Database issues)"
Write-Host "  2. PRODUCTION_BACKEND_TROUBLESHOOTING.md (All backend issues)"
Write-Host ""
Write-Host "Common fixes:" -ForegroundColor Yellow
Write-Host "  • Restart backend: railway service restart --service backend"
Write-Host "  • Restart postgres: railway service restart --service postgres"
Write-Host "  • Check logs: railway logs --service backend --follow"
Write-Host "  • Update variables: railway variables set KEY=VALUE"
Write-Host ""
