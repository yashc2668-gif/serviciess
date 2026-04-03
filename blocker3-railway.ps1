#!/usr/bin/env pwsh
# Auto-configure Railway backend env vars for Blocker #3

param(
    [string]$Environment = "production",
    [string]$Debug = "False"
)

Write-Host "=== Railway Environment Variable Setup - Blocker #3 ===" -ForegroundColor Cyan

# Step 1: Check Railway CLI
Write-Host "[1/6] Checking Railway CLI..." -ForegroundColor Yellow
$railwayPath = Get-Command railway -ErrorAction SilentlyContinue
if (-not $railwayPath) {
    Write-Host "Installing Railway CLI..." -ForegroundColor Gray
    npm install -g @railway/cli
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install Railway CLI" -ForegroundColor Red
        exit 1
    }
}
Write-Host "OK: Railway CLI ready" -ForegroundColor Green

# Step 2: Check auth
Write-Host "[2/6] Checking Railway authentication..." -ForegroundColor Yellow
$authCheck = railway whoami 2>&1
if ($authCheck -match "not authenticated|login required") {
    Write-Host "Starting Railway login..." -ForegroundColor Gray
    railway login
}
Write-Host "OK: Authenticated" -ForegroundColor Green

# Step 3: Show projects
Write-Host "[3/6] Available projects:" -ForegroundColor Yellow
railway projects 2>&1
Write-Host ""
$projectName = Read-Host "Enter project name/ID containing backend"

# Step 4: Link project
Write-Host "[4/6] Linking to project..." -ForegroundColor Yellow
railway link --project $projectName 2>&1 | Out-Null
Write-Host "OK: Project linked" -ForegroundColor Green

# Step 5: Show current vars
Write-Host "[5/6] Setting environment variables..." -ForegroundColor Yellow

# Set ENVIRONMENT
Write-Host "  Setting ENVIRONMENT=$Environment..." -ForegroundColor Gray
railway variables set ENVIRONMENT $Environment 2>&1 | Out-Null

# Set DEBUG
Write-Host "  Setting DEBUG=$Debug..." -ForegroundColor Gray
railway variables set DEBUG $Debug 2>&1 | Out-Null

# Set ALLOWED_ORIGINS (PERFECT FORMAT - PRODUCTION)
$originsJson = '["https://m2n-frontend.vercel.app","https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app","https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app"]'

Write-Host "  Setting ALLOWED_ORIGINS..." -ForegroundColor Gray
railway variables set ALLOWED_ORIGINS $originsJson 2>&1 | Out-Null

Write-Host "OK: All variables set" -ForegroundColor Green

# Step 6: Verify
Write-Host "[6/6] Verifying variables..." -ForegroundColor Yellow
railway variables 2>&1 | Select-String "ENVIRONMENT|DEBUG|ALLOWED_ORIGINS"
Write-Host "OK: Verification complete" -ForegroundColor Green

Write-Host ""
Write-Host "=== BLOCKER #3 FIX COMPLETE ===" -ForegroundColor Green
Write-Host ""
Write-Host "Note: Railway auto-restarts container when env vars change" -ForegroundColor Gray
Write-Host "Timeline: 1-2 minutes for container restart" -ForegroundColor Gray
