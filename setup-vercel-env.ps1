#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Automatically configure VITE_API_BASE_URL in Vercel for production deployment
    
.DESCRIPTION
    Sets the production backend URL as an environment variable in Vercel using CLI
    This fixes Blocker #2: Frontend Can't Reach Backend
    
.EXAMPLE
    .\setup-vercel-env.ps1
#>

param(
    [string]$ApiBaseUrl = "https://m2n-serviciess-production.up.railway.app/api/v1",
    [string]$EnvVarName = "VITE_API_BASE_URL"
)

Write-Host "🚀 Starting Vercel Environment Variable Setup for Blocker #2" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if Vercel CLI is installed
Write-Host "📦 Checking Vercel CLI installation..." -ForegroundColor Yellow
$vercelPath = Get-Command vercel -ErrorAction SilentlyContinue
if (-not $vercelPath) {
    Write-Host "❌ Vercel CLI not found. Installing..." -ForegroundColor Red
    npm install -g vercel
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install Vercel CLI" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Vercel CLI installed" -ForegroundColor Green
} else {
    Write-Host "✅ Vercel CLI found: $($vercelPath.Source)" -ForegroundColor Green
}

Write-Host ""

# Step 2: Navigate to frontend directory
Write-Host "📂 Navigating to frontend directory..." -ForegroundColor Yellow
$frontendPath = "d:\M2N_SOFTWARE\frontend"
if (-not (Test-Path $frontendPath)) {
    Write-Host "❌ Frontend directory not found at $frontendPath" -ForegroundColor Red
    exit 1
}
Set-Location $frontendPath
Write-Host "✅ In frontend directory: $(Get-Location)" -ForegroundColor Green

Write-Host ""

# Step 3: Check if .vercel directory exists (indicates linked project)
Write-Host "🔍 Checking Vercel project link..." -ForegroundColor Yellow
if (-not (Test-Path ".vercel")) {
    Write-Host "⚠️  .vercel directory not found. Project may not be linked." -ForegroundColor Yellow
    Write-Host "   Creating link via 'vercel link'..." -ForegroundColor Yellow
    vercel link --yes
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  'vercel link' returned exit code $($LASTEXITCODE). Continuing anyway..." -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ Project linked to Vercel" -ForegroundColor Green
}

Write-Host ""

# Step 4: List current environment variables
Write-Host "📋 Checking current environment variables..." -ForegroundColor Yellow
Write-Host ""
vercel env ls
Write-Host ""

Write-Host "🔧 Setting environment variable: $EnvVarName" -ForegroundColor Yellow
Write-Host "   Value: $ApiBaseUrl" -ForegroundColor Cyan
Write-Host "   Scope: Production" -ForegroundColor Cyan
Write-Host ""

# Step 5: Pull .env.production to local (for reference)
Write-Host "📥 Pulling current environment configuration..." -ForegroundColor Yellow
vercel env pull --environment production 2>&1
Write-Host ""

# Step 6: Create a .env.production file locally for verification
Write-Host "📝 Creating local .env.production with the variable..." -ForegroundColor Yellow
$envContent = "VITE_API_BASE_URL=$ApiBaseUrl"
$envContent | Set-Content -Path ".env.production" -Encoding UTF8
Write-Host "✅ Created .env.production locally" -ForegroundColor Green
Get-Content .env.production | Write-Host

Write-Host ""

# Step 7: Set the production environment variable
Write-Host "⚙️  Setting variable in Vercel production environment..." -ForegroundColor Yellow
Write-Host ""

# Use echo to pipe the value, environment selection
$output = @"
$ApiBaseUrl
1
"@ | vercel env add $EnvVarName --environment production 2>&1

Write-Host $output
Write-Host ""

# Step 8: Verify the variable was set
Write-Host "✅ Verifying environment variable was set..." -ForegroundColor Green
Write-Host ""
vercel env ls --environment production | Select-String $EnvVarName
Write-Host ""

# Step 9: Trigger production deployment
Write-Host "🚀 Triggering production deployment with new environment variable..." -ForegroundColor Yellow
Write-Host ""
vercel deploy --prod

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ BLOCKER #2 FIXED!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Summary:" -ForegroundColor Cyan
    Write-Host "   ✅ Set VITE_API_BASE_URL to: $ApiBaseUrl" -ForegroundColor Green
    Write-Host "   ✅ Applied to: Production environment" -ForegroundColor Green
    Write-Host "   ✅ Deployed: vercel deploy --prod" -ForegroundColor Green
    Write-Host ""
    Write-Host "⏱️  Frontend will be live in 2-3 minutes with correct backend URL" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "⚠️  Deployment may require additional steps" -ForegroundColor Yellow
    Write-Host "   Run: vercel deploy --prod" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "💡 Next: Run Blocker #3 script to configure Railway backend env vars" -ForegroundColor Cyan
