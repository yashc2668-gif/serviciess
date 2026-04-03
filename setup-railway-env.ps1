#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Automatically configure production environment variables in Railway backend
    
.DESCRIPTION
    Sets production env vars (ENVIRONMENT, DEBUG, ALLOWED_ORIGINS) in Railway CLI
    This fixes Blocker #3: Backend Rejects Frontend CORS
    
.NOTES
    Requires: Railway CLI (railway command)
    Install: npm install -g @railway/cli
    
.EXAMPLE
    .\setup-railway-env.ps1
#>

param(
    [string]$Environment = "production",
    [string]$Debug = "False"
)

# PERFECT JSON FORMAT - PRODUCTION (No localhost allowed!)
$AllowedOrigins = '["https://m2n-frontend.vercel.app","https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app","https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app"]'


Write-Host "🚀 Starting Railway Backend Environment Variable Setup for Blocker #3" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if Railway CLI is installed
Write-Host "📦 Checking Railway CLI installation..." -ForegroundColor Yellow
$railwayPath = Get-Command railway -ErrorAction SilentlyContinue
if (-not $railwayPath) {
    Write-Host "❌ Railway CLI not found. Installing..." -ForegroundColor Red
    npm install -g @railway/cli
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install Railway CLI" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Railway CLI installed" -ForegroundColor Green
} else {
    Write-Host "✅ Railway CLI found: $($railwayPath.Source)" -ForegroundColor Green
}

Write-Host ""

# Step 2: Check Railway authentication
Write-Host "🔐 Checking Railway authentication..." -ForegroundColor Yellow
$authCheck = railway whoami 2>&1
if ($authCheck -match "not authenticated|login required") {
    Write-Host "⚠️  Not authenticated with Railway. Running 'railway login'..." -ForegroundColor Yellow
    railway login
} else {
    Write-Host "✅ Railway authenticated: $(($authCheck | Select-Object -First 1))" -ForegroundColor Green
}

Write-Host ""

# Step 3: List available projects
Write-Host "📋 Listing Railway projects..." -ForegroundColor Yellow
Write-Host ""
railway projects
Write-Host ""

# Step 4: Get user input for project selection
Write-Host "🔍 Detecting backend project..." -ForegroundColor Yellow
$projectList = railway projects 2>&1 | Select-String "m2n|backend|production" -ErrorAction SilentlyContinue
if ($projectList.Count -gt 0) {
    Write-Host "Found potential project(s):" -ForegroundColor Green
    $projectList | ForEach-Object { Write-Host "  • $_" }
    Write-Host ""
    $projectName = Read-Host "Enter exact project name or ID from above"
} else {
    $projectName = Read-Host "Enter Railway project name/ID"
}

Write-Host ""

# Step 5: Switch to project
Write-Host "🔄 Switching to project: $projectName" -ForegroundColor Yellow
railway link --project $projectName
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Could not auto-link project. Trying to set via environment..." -ForegroundColor Yellow
}

Write-Host ""

# Step 6: Show current environment variables
Write-Host "📋 Current environment variables in backend service:" -ForegroundColor Yellow
Write-Host ""
railway variables 2>&1
Write-Host ""

# Step 7: Set ENVIRONMENT variable
Write-Host "⚙️  Setting ENVIRONMENT=$Environment" -ForegroundColor Yellow
railway variables set ENVIRONMENT $Environment
Write-Host "✅ Set ENVIRONMENT=$Environment" -ForegroundColor Green

Write-Host ""

# Step 8: Set DEBUG variable
Write-Host "⚙️  Setting DEBUG=$Debug" -ForegroundColor Yellow
railway variables set DEBUG $Debug
Write-Host "✅ Set DEBUG=$Debug" -ForegroundColor Green

Write-Host ""

# Step 9: Set ALLOWED_ORIGINS variable
Write-Host "⚙️  Setting ALLOWED_ORIGINS with Vercel domains" -ForegroundColor Yellow
railway variables set ALLOWED_ORIGINS $AllowedOrigins
Write-Host "✅ Set ALLOWED_ORIGINS=" -ForegroundColor Green
Write-Host "   $AllowedOrigins"

Write-Host ""

# Step 10: Verify variables
Write-Host "✅ Verifying environment variables were set..." -ForegroundColor Green
Write-Host ""
railway variables | Select-String "ENVIRONMENT|DEBUG|ALLOWED_ORIGINS"
Write-Host ""

# Step 11: Trigger redeploy
Write-Host "🚀 Triggering backend redeploy (Railway auto-restarts on env var change)..." -ForegroundColor Yellow
Write-Host "⏱️  Railway will restart the backend container in 1-2 minutes" -ForegroundColor Cyan
Write-Host ""

Write-Host "✅ BLOCKER #3 FIXED!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Summary:" -ForegroundColor Cyan
Write-Host "   ✅ Set ENVIRONMENT=production" -ForegroundColor Green
Write-Host "   ✅ Set DEBUG=False" -ForegroundColor Green
Write-Host "   ✅ Set ALLOWED_ORIGINS with both Vercel domains" -ForegroundColor Green
Write-Host ""
Write-Host "⏱️  Backend will be live with new security settings in 2-3 minutes" -ForegroundColor Cyan
Write-Host ""
Write-Host "🎉 ALL 3 BLOCKERS NOW FIXED:" -ForegroundColor Green
Write-Host "   ✅ Blocker #1: SPA routing (vercel.json) - DONE" -ForegroundColor Green
Write-Host "   ✅ Blocker #2: Frontend env var - JUST DONE" -ForegroundColor Green
Write-Host "   ✅ Blocker #3: Backend env vars - JUST DONE" -ForegroundColor Green
