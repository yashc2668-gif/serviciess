# ============================================================
# M2N SOFTWARE - DEPLOY FOR BOSS (RAILWAY SETUP)
# Run this script to set all environment variables correctly
# ============================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  M2N SOFTWARE - DEPLOY FOR BOSS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if railway CLI is available
try {
    $railwayVersion = railway --version 2>$null
    Write-Host "[OK] Railway CLI found" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Railway CLI not found. Install with: npm install -g @railway/cli" -ForegroundColor Red
    exit 1
}

# Step 2: Set ENVIRONMENT
Write-Host ""
Write-Host "[1/4] Setting ENVIRONMENT=production..." -ForegroundColor Yellow
railway variables set ENVIRONMENT=production
Write-Host "[OK] ENVIRONMENT set" -ForegroundColor Green

# Step 3: Set DEBUG
Write-Host ""
Write-Host "[2/4] Setting DEBUG=False..." -ForegroundColor Yellow
railway variables set DEBUG=False
Write-Host "[OK] DEBUG set" -ForegroundColor Green

# Step 4: Set ALLOWED_ORIGINS (PERFECT FORMAT - NO SPACES)
Write-Host ""
Write-Host "[3/4] Setting ALLOWED_ORIGINS..." -ForegroundColor Yellow

# CORRECT JSON FORMAT - PRODUCTION (No localhost allowed!)
$allowedOrigins = '["https://m2n-frontend.vercel.app","https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app","https://m2n-frontend-jel4ixehf-yashs-projects-8e52d41e.vercel.app"]'

railway variables set ALLOWED_ORIGINS=$allowedOrigins
Write-Host "[OK] ALLOWED_ORIGINS set" -ForegroundColor Green
Write-Host "      Value: $allowedOrigins" -ForegroundColor Gray

# Step 5: Verify all variables
Write-Host ""
Write-Host "[4/4] Verifying all variables..." -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Gray
railway variables | Select-String "ENVIRONMENT|DEBUG|ALLOWED_ORIGINS"
Write-Host "----------------------------------------" -ForegroundColor Gray

# Step 6: Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  DEPLOY READY FOR BOSS!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Railway will auto-restart in 1-2 minutes" -ForegroundColor Cyan
Write-Host ""
Write-Host "Check status at: https://railway.app/dashboard" -ForegroundColor Cyan
Write-Host ""
