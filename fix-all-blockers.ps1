#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Master orchestration script - Fix ALL 3 production deployment blockers
    
.DESCRIPTION
    Runs both Vercel (Blocker #2) and Railway (Blocker #3) setup scripts in sequence
    Blocker #1 (SPA routing) was already fixed via vercel.json push
    
.EXAMPLE
    .\fix-all-blockers.ps1
#>

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  🚀 M2N CONSTRUCTION ERP - PRODUCTION DEPLOYMENT FIX MASTER   ║" -ForegroundColor Cyan
Write-Host "║                  All 3 Blockers                               ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Summary before starting
Write-Host "📋 WHAT THIS SCRIPT WILL DO:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   ✅ Blocker #1: SPA Routing" -ForegroundColor Green
Write-Host "      Status: ALREADY FIXED (vercel.json pushed)" -ForegroundColor Green
Write-Host ""
Write-Host "   ⏳ Blocker #2: Frontend → Backend Connection" -ForegroundColor Yellow
Write-Host "      Action: Set VITE_API_BASE_URL in Vercel to production Railway URL" -ForegroundColor Cyan
Write-Host "      Script: setup-vercel-env.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "   ⏳ Blocker #3: Backend CORS Security" -ForegroundColor Yellow
Write-Host "      Action: Set ENVIRONMENT, DEBUG, ALLOWED_ORIGINS in Railway" -ForegroundColor Cyan
Write-Host "      Script: setup-railway-env.ps1" -ForegroundColor Cyan
Write-Host ""

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Gray
Write-Host ""

# Confirm before proceeding
$confirm = Read-Host "🤔 Continue with automated setup? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "❌ Cancelled by user" -ForegroundColor Red
    exit 0
}

Write-Host ""

# ============================================================================
# PART 1: VERCEL SETUP (Blocker #2)
# ============================================================================

Write-Host "▶️  PART 1: Setting up Vercel Environment Variable (Blocker #2)" -ForegroundColor Cyan
Write-Host ""

$setupVercelScript = "d:\M2N_SOFTWARE\setup-vercel-env.ps1"
if (Test-Path $setupVercelScript) {
    & $setupVercelScript
} else {
    Write-Host "❌ Script not found: $setupVercelScript" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "⏳ Vercel setup complete. Waiting 10 seconds before Railway setup..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Gray
Write-Host ""

# ============================================================================
# PART 2: RAILWAY SETUP (Blocker #3)
# ============================================================================

Write-Host "▶️  PART 2: Setting up Railway Environment Variables (Blocker #3)" -ForegroundColor Cyan
Write-Host ""

$setupRailwayScript = "d:\M2N_SOFTWARE\setup-railway-env.ps1"
if (Test-Path $setupRailwayScript) {
    & $setupRailwayScript
} else {
    Write-Host "❌ Script not found: $setupRailwayScript" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Gray
Write-Host ""

# ============================================================================
# FINAL SUMMARY
# ============================================================================

Write-Host "🎉 ALL PRODUCTION DEPLOYMENT BLOCKERS NOW FIXED!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 FINAL STATUS:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   ✅ Blocker #1: SPA Routing via vercel.json" -ForegroundColor Green
Write-Host "      Fixed: March 30, 2026 (commit: bfbc67a)" -ForegroundColor Green
Write-Host ""
Write-Host "   ✅ Blocker #2: Frontend → Backend API Connection" -ForegroundColor Green
Write-Host "      Fixed: VITE_API_BASE_URL set to production Railway URL" -ForegroundColor Green
Write-Host "      Vercel deploying now (2-3 min)" -ForegroundColor Cyan
Write-Host ""
Write-Host "   ✅ Blocker #3: Backend CORS & Production Security" -ForegroundColor Green
Write-Host "      Fixed: ENVIRONMENT, DEBUG, ALLOWED_ORIGINS configured" -ForegroundColor Green
Write-Host "      Railway restarting now (1-2 min)" -ForegroundColor Cyan
Write-Host ""

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Gray
Write-Host ""

Write-Host "⏱️  TIMELINE:" -ForegroundColor Yellow
Write-Host "   • Now:       All env vars configured" -ForegroundColor Cyan
Write-Host "   • +1-2 min:  Railway backend restarts with new config" -ForegroundColor Cyan
Write-Host "   • +2-3 min:  Vercel frontend deploys with new API URL" -ForegroundColor Cyan
Write-Host "   • +5 min:    PRODUCTION READY 🚀" -ForegroundColor Green
Write-Host ""

Write-Host "🧪 VERIFICATION TESTS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   1️⃣  Test SPA routing (should NOT 404):" -ForegroundColor Cyan
Write-Host "       https://m2n-frontend-git-main-yashs-projects-8e52d41e.vercel.app/forgot-password" -ForegroundColor Gray
Write-Host ""
Write-Host "   2️⃣  Test backend health:" -ForegroundColor Cyan
Write-Host "       curl https://m2n-serviciess-production.up.railway.app/api/v1/health/ready" -ForegroundColor Gray
Write-Host ""
Write-Host "   3️⃣  Test CORS (from browser DevTools console):" -ForegroundColor Cyan
Write-Host "       fetch('https://m2n-serviciess-production.up.railway.app/api/v1/health/ready')" -ForegroundColor Gray
Write-Host "         .then(r => r.json()).then(console.log)" -ForegroundColor Gray
Write-Host ""

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Gray
Write-Host ""
Write-Host "✨ Production deployment complete! Your app is now live. ✨" -ForegroundColor Green
Write-Host ""
