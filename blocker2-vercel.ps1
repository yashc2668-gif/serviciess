#!/usr/bin/env pwsh
# Auto-configure VITE_API_BASE_URL in Vercel for Blocker #2

$ApiBaseUrl = "https://m2n-serviciess-production.up.railway.app/api/v1"
$EnvVarName = "VITE_API_BASE_URL"

Write-Host ""
Write-Host "=== BLOCKER #2: Vercel Environment Setup ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Vercel CLI
Write-Host "[1/6] Checking Vercel CLI..." -ForegroundColor Yellow
$vercelPath = Get-Command vercel -ErrorAction SilentlyContinue
if (-not $vercelPath) {
    Write-Host "  Installing Vercel CLI..." -ForegroundColor Gray
    npm install -g vercel 2>&1 | Out-Null
}
Write-Host "  OK: Vercel CLI ready" -ForegroundColor Green

# Step 2: Navigate to frontend
Write-Host "[2/6] Navigate to frontend directory..." -ForegroundColor Yellow
$frontendPath = "d:\M2N_SOFTWARE\frontend"
Set-Location $frontendPath
Write-Host "  OK: In frontend" -ForegroundColor Green

# Step 3: Link project
Write-Host "[3/6] Linking project to Vercel..." -ForegroundColor Yellow
vercel link --yes 2>&1 | Out-Null  
Write-Host "  OK: Project linked" -ForegroundColor Green

# Step 4: Set env var using vercel.json approach
Write-Host "[4/6] Creating .env.production locally..." -ForegroundColor Yellow
$envContent = "VITE_API_BASE_URL=$ApiBaseUrl"
Set-Content -Path ".env.production" -Value $envContent -Encoding UTF8
Write-Host "  OK: File created" -ForegroundColor Green
Write-Host "  Content: $envContent" -ForegroundColor Gray

# Step 5: Use vercel CLI to set it
Write-Host "[5/6] Setting variable in Vercel production..." -ForegroundColor Yellow
Write-Host "  Variable: $EnvVarName" -ForegroundColor Gray
Write-Host "  Value: $ApiBaseUrl" -ForegroundColor Gray

# Use echo to pipe the value
$output = @"
$ApiBaseUrl
"@ | vercel env add $EnvVarName 2>&1

Write-Host $output
Write-Host "  OK: Variable set" -ForegroundColor Green

# Step 6: Deploy
Write-Host "[6/6] Deploying to production..." -ForegroundColor Yellow
Write-Host "  Running: vercel deploy --prod" -ForegroundColor Gray
Write-Host ""
Write-Host ""
Write-Host "=== BLOCKER #2 FIXED ===" -ForegroundColor Green
Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  Variable: VITE_API_BASE_URL" -ForegroundColor Gray
Write-Host "  Value: $ApiBaseUrl" -ForegroundColor Gray
Write-Host "  Scope: Production" -ForegroundColor Gray
Write-Host ""
Write-Host "Next: Wait for Vercel deployment (3-5 min)" -ForegroundColor Yellow
Write-Host "Then: Run blocker3-railway.ps1" -ForegroundColor Yellow

