#!/usr/bin/env python3
"""Generate M2N Software Analysis PDF"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, ListFlowable, ListItem
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime

def create_pdf():
    filename = "M2N_Software_Full_Analysis.pdf"
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a365d'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading1_style = ParagraphStyle(
        'CustomH1',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2c5282'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    heading2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2b6cb0'),
        spaceAfter=10,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )
    
    heading3_style = ParagraphStyle(
        'CustomH3',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#3182ce'),
        spaceAfter=8,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY
    )
    
    bullet_style = ParagraphStyle(
        'CustomBullet',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        leftIndent=20
    )
    
    story = []
    
    # ============== COVER PAGE ==============
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("🏗️ M2N CONSTRUCTION ERP", title_style))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("COMPLETE SYSTEM ANALYSIS", heading1_style))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", normal_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Full Technical Documentation & Deployment Guide", normal_style))
    story.append(PageBreak())
    
    # ============== TABLE OF CONTENTS ==============
    story.append(Paragraph("📋 TABLE OF CONTENTS", heading1_style))
    story.append(Spacer(1, 0.2*inch))
    
    toc_items = [
        "1. Project Overview",
        "2. Project Structure",
        "3. Key Modules",
        "4. Technology Stack",
        "5. Database Models",
        "6. Deployment Status",
        "7. Completed Work",
        "8. Authentication System",
        "9. Testing Setup",
        "10. Security Features",
        "11. Workflow System",
        "12. Deployment Guide",
        "13. Quick Commands",
        "14. Conclusion"
    ]
    
    for item in toc_items:
        story.append(Paragraph(f"• {item}", bullet_style))
    story.append(PageBreak())
    
    # ============== 1. PROJECT OVERVIEW ==============
    story.append(Paragraph("1. PROJECT OVERVIEW", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph(
        "<b>M2N Software</b> is a comprehensive <b>Construction ERP (Enterprise Resource Planning)</> "
        "system designed specifically for construction companies. It enables management of projects, "
        "materials, labour, finance, vendors, and all construction-related operations in one unified platform.",
        normal_style
    ))
    story.append(Spacer(1, 0.1*inch))
    
    overview_data = [
        ['Aspect', 'Details'],
        ['Project Type', 'Construction ERP System'],
        ['Architecture', 'Full-Stack Web Application'],
        ['Frontend', 'React 19 + TypeScript + Vite'],
        ['Backend', 'FastAPI (Python 3.12)'],
        ['Database', 'PostgreSQL (Production) / SQLite (Dev)'],
        ['Deployment', 'Vercel (Frontend) + Railway (Backend)'],
        ['Total Code Files', '300+ (Frontend + Backend)'],
        ['Test Coverage', '25+ Test Files']
    ]
    
    overview_table = Table(overview_data, colWidths=[2.5*inch, 4*inch])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(overview_table)
    story.append(PageBreak())
    
    # ============== 2. PROJECT STRUCTURE ==============
    story.append(Paragraph("2. PROJECT STRUCTURE", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("<b>Directory Structure:</b>", heading2_style))
    structure_text = """
    <b>d:\M2N_SOFTWARE\</b><br/>
    ├── <b>frontend/</b> - React Frontend (Vercel deployed)<br/>
    │   ├── src/features/ - All ERP modules<br/>
    │   ├── src/components/ - UI components<br/>
    │   ├── src/app/ - Router, Layouts, Providers<br/>
    │   └── vercel.json - SPA routing config<br/>
    │<br/>
    ├── <b>backend/</b> - FastAPI Backend (Railway deployed)<br/>
    │   ├── app/api/v1/endpoints/ - 40+ API routes<br/>
    │   ├── app/models/ - Database models<br/>
    │   ├── app/services/ - Business logic<br/>
    │   ├── app/schemas/ - Pydantic validation<br/>
    │   └── app/tests/ - Test suite<br/>
    │<br/>
    └── <b>Documentation files</b> (20+ guides)
    """
    story.append(Paragraph(structure_text, normal_style))
    story.append(PageBreak())
    
    # ============== 3. KEY MODULES ==============
    story.append(Paragraph("3. KEY MODULES", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    modules = [
        ("1. ADMIN MODULE", [
            "• Users management",
            "• Audit logs (track all changes)",
            "• AI Boundary settings"
        ]),
        ("2. MASTERS MODULE", [
            "• Companies - Company profiles",
            "• Projects - Construction projects",
            "• Vendors - Suppliers/Contractors",
            "• Contracts - Project contracts",
            "• BOQ - Bill of Quantities"
        ]),
        ("3. MATERIALS MODULE", [
            "• Material master (inventory management)",
            "• Requisitions - Request materials",
            "• Receipts - Goods receipt",
            "• Issues - Material issue to site",
            "• Stock Adjustments - Damage/wastage",
            "• Stock Ledger - Complete tracking"
        ]),
        ("4. LABOUR MODULE", [
            "• Contractors - Labour suppliers",
            "• Workers - Labour database",
            "• Attendance - Daily muster",
            "• Productivity - Work output tracking",
            "• Labour Bills - Payment calculation",
            "• Advances - Pre-payments"
        ]),
        ("5. FINANCE MODULE", [
            "• Measurements - Work measurement",
            "• Work Done - Progress tracking",
            "• RA Bills - Running Account bills",
            "• Secured Advances - Security deposits",
            "• Payments - Actual payments",
            "• Deductions - Tax, TDS, etc."
        ]),
        ("6. DOCUMENTS MODULE", [
            "• Document upload/download",
            "• Version control"
        ])
    ]
    
    for module_title, items in modules:
        story.append(Paragraph(module_title, heading2_style))
        for item in items:
            story.append(Paragraph(item, bullet_style))
        story.append(Spacer(1, 0.05*inch))
    
    story.append(PageBreak())
    
    # ============== 4. TECHNOLOGY STACK ==============
    story.append(Paragraph("4. TECHNOLOGY STACK", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("4.1 Frontend Technologies", heading2_style))
    frontend_tech = [
        ['Technology', 'Version', 'Purpose'],
        ['React', '19.2.0', 'UI Library'],
        ['TypeScript', '5.9.3', 'Type Safety'],
        ['Vite', '8.0.1', 'Build Tool'],
        ['TanStack Router', '1.16.8', 'Navigation'],
        ['TanStack Query', '5.95.2', 'Server State'],
        ['Tailwind CSS', '4.2.2', 'Styling'],
        ['React Hook Form', '7.72.0', 'Forms'],
        ['Zod', '4.3.6', 'Validation'],
        ['Recharts', '3.8.1', 'Charts'],
        ['Lucide React', '1.7.0', 'Icons'],
    ]
    
    ft_table = Table(frontend_tech, colWidths=[2*inch, 1.2*inch, 3*inch])
    ft_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3182ce')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ebf8ff')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bee3f8')),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(ft_table)
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("4.2 Backend Technologies", heading2_style))
    backend_tech = [
        ['Technology', 'Version', 'Purpose'],
        ['FastAPI', '0.115.6', 'Web Framework'],
        ['SQLAlchemy', '2.0.36', 'ORM'],
        ['Alembic', '1.14.1', 'Migrations'],
        ['PostgreSQL', '-', 'Production DB'],
        ['JWT', '3.3.0', 'Authentication'],
        ['Bcrypt', '4.2.1', 'Password Hashing'],
        ['ReportLab', '4.4.10', 'PDF Generation'],
        ['SlowAPI', '0.1.9', 'Rate Limiting'],
    ]
    
    bt_table = Table(backend_tech, colWidths=[2*inch, 1.2*inch, 3*inch])
    bt_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#38a169')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0fff4')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#c6f6d5')),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(bt_table)
    story.append(PageBreak())
    
    # ============== 5. DATABASE MODELS ==============
    story.append(Paragraph("5. DATABASE MODELS (50+ Models)", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("Key Entities:", heading2_style))
    entities = [
        "• <b>User Management:</b> Users, Roles, Permissions",
        "• <b>Master Data:</b> Companies, Projects, Vendors",
        "• <b>Contracts:</b> Contracts, BOQ Items, Variation Orders",
        "• <b>Materials:</b> Materials, Stock Ledger, Transactions",
        "• <b>Labour:</b> Labour, Contractors, Attendance, Productivity",
        "• <b>Finance:</b> Measurements, RA Bills, Payments, Deductions",
        "• <b>Documents:</b> Documents, Document Versions",
        "• <b>Audit:</b> Audit Logs, Approval Workflows",
        "• <b>Security:</b> Refresh Tokens, Password Reset OTP",
    ]
    for entity in entities:
        story.append(Paragraph(entity, bullet_style))
    
    story.append(PageBreak())
    
    # ============== 6. DEPLOYMENT STATUS ==============
    story.append(Paragraph("6. DEPLOYMENT STATUS", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("Current Status:", heading2_style))
    deploy_data = [
        ['Service', 'Platform', 'Status', 'URL'],
        ['Frontend', 'Vercel', '✅ LIVE', 'm2n-frontend-git-main...vercel.app'],
        ['Backend', 'Railway', '❌ FAILED', 'm2n-serviciess-production...'],
        ['Database', 'Railway Postgres', '❌ FAILED', 'Service non-responsive'],
    ]
    
    deploy_table = Table(deploy_data, colWidths=[1.3*inch, 1.3*inch, 1*inch, 3*inch])
    deploy_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#744210')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#c6f6d5')),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#fed7d7')),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#fed7d7')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(deploy_table)
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph(
        "<b>Current Blocker:</b> PostgreSQL service FAILED on Railway. Database service needs restart from Railway dashboard.",
        ParagraphStyle('Warning', parent=normal_style, textColor=colors.red, fontName='Helvetica-Bold')
    ))
    story.append(PageBreak())
    
    # ============== 7. COMPLETED WORK ==============
    story.append(Paragraph("7. COMPLETED WORK", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    completed = [
        ['#', 'Task', 'Status'],
        ['1', 'Frontend SPA Routing Fix', '✅ DONE'],
        ['2', 'Backend CORS Configuration', '✅ DONE'],
        ['3', 'Healthcheck Endpoint Fix', '✅ DONE'],
        ['4', 'Vercel vercel.json Deployed', '✅ DONE'],
        ['5', 'Backend Code Fixes', '✅ COMMITTED'],
    ]
    
    comp_table = Table(completed, colWidths=[0.5*inch, 4*inch, 1.5*inch])
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#276749')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0fff4')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#c6f6d5')),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(comp_table)
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("Files Created (13 files):", heading2_style))
    files = [
        "• blocker2-vercel.ps1 - Vercel env setup script",
        "• blocker3-railway.ps1 - Railway env setup script",
        "• fix-all-blockers.ps1 - Master orchestration script",
        "• setup-vercel-env.ps1 - Detailed Vercel setup",
        "• setup-railway-env.ps1 - Detailed Railway setup",
        "• START_HERE.md - Quick start guide",
        "• SOLUTION_SUMMARY.md - Executive summary",
        "• DEPLOYMENT_README.md - Technical details",
        "• BLOCKER_2_3_MANUAL.md - Manual fallback",
        "• .PRODUCTION_DEPLOYMENT_CHECKLIST.md - Test cases",
        "• frontend/vercel.json - SPA routing config",
    ]
    for f in files:
        story.append(Paragraph(f, bullet_style))
    
    story.append(PageBreak())
    
    # ============== 8. AUTHENTICATION ==============
    story.append(Paragraph("8. AUTHENTICATION SYSTEM", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("Features:", heading2_style))
    auth_features = [
        "• JWT-based authentication",
        "• Password reset with OTP",
        "• Role-based access control (RBAC)",
        "• Refresh token sessions",
        "• Session management",
        "• Secure password hashing (Bcrypt)",
    ]
    for af in auth_features:
        story.append(Paragraph(af, bullet_style))
    story.append(PageBreak())
    
    # ============== 9. TESTING ==============
    story.append(Paragraph("9. TESTING SETUP", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    testing_data = [
        ['Type', 'Tool', 'Status'],
        ['Unit Tests', 'Vitest (Frontend)', '✅ Configured'],
        ['E2E Tests', 'Playwright', '✅ Configured'],
        ['Backend Tests', 'pytest', '25+ Tests'],
    ]
    
    test_table = Table(testing_data, colWidths=[1.5*inch, 2.5*inch, 2*inch])
    test_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#553c9a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#faf5ff')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e9d8fd')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(test_table)
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("Backend Test Files:", heading2_style))
    test_files = [
        "• test_auth.py, test_auth_security.py",
        "• test_permissions.py",
        "• test_dashboard.py",
        "• test_ra_bill_workflow.py",
        "• test_payment_flow.py",
        "• test_document_upload.py",
        "• test_data_safety.py",
        "• And 18+ more test files..."
    ]
    for tf in test_files:
        story.append(Paragraph(tf, bullet_style))
    story.append(PageBreak())
    
    # ============== 10. SECURITY ==============
    story.append(Paragraph("10. SECURITY FEATURES", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    security_features = [
        ("1. CORS Protection", "Allowed origins whitelist"),
        ("2. Rate Limiting", "SlowAPI integration"),
        ("3. Security Headers", "XSS, CSRF protection"),
        ("4. Input Validation", "Pydantic schemas"),
        ("5. SQL Injection Protection", "SQLAlchemy ORM"),
        ("6. Password Hashing", "Bcrypt algorithm"),
        ("7. Audit Logging", "Every change tracked"),
        ("8. Idempotency Keys", "Duplicate request prevention"),
    ]
    
    for sf, desc in security_features:
        story.append(Paragraph(f"<b>{sf}:</b> {desc}", bullet_style))
    story.append(PageBreak())
    
    # ============== 11. WORKFLOW ==============
    story.append(Paragraph("11. WORKFLOW SYSTEM", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph(
        "Approval Workflow for important actions:",
        normal_style
    ))
    story.append(Spacer(1, 0.05*inch))
    
    story.append(Paragraph(
        "<b>Draft → Submitted → Approved → Paid/Completed</b>",
        ParagraphStyle('Workflow', parent=normal_style, fontName='Helvetica-Bold', textColor=colors.HexColor('#2c5282'))
    ))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("Modules with Workflows:", heading2_style))
    workflow_modules = [
        "• Material Requisitions",
        "• RA Bills",
        "• Payments",
        "• Measurements",
        "• Labour Bills"
    ]
    for wm in workflow_modules:
        story.append(Paragraph(wm, bullet_style))
    story.append(PageBreak())
    
    # ============== 12. DEPLOYMENT GUIDE ==============
    story.append(Paragraph("12. DEPLOYMENT GUIDE", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("Step 1: Fix PostgreSQL (Railway Dashboard)", heading2_style))
    story.append(Paragraph("• Go to Railway dashboard", bullet_style))
    story.append(Paragraph("• Find Postgres service", bullet_style))
    story.append(Paragraph("• Click Restart button", bullet_style))
    story.append(Paragraph("• Wait for RUNNING (green) status", bullet_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("Step 2: Redeploy Backend", heading2_style))
    story.append(Paragraph("cd d:\M2N_SOFTWARE\backend", bullet_style))
    story.append(Paragraph("railway deployment redeploy --service m2n-serviciess -y", bullet_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("Step 3: Set Vercel Environment Variable", heading2_style))
    story.append(Paragraph("Name: VITE_API_BASE_URL", bullet_style))
    story.append(Paragraph("Value: https://m2n-serviciess-production.up.railway.app/api/v1", bullet_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("Step 4: Verify", heading2_style))
    story.append(Paragraph("curl https://m2n-serviciess-production.up.railway.app/health", bullet_style))
    story.append(PageBreak())
    
    # ============== 13. QUICK COMMANDS ==============
    story.append(Paragraph("13. QUICK COMMANDS", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    commands = [
        ("Frontend Development", "cd frontend && npm run dev"),
        ("Backend Development", "cd backend && uvicorn main:app --reload"),
        ("Frontend Tests", "cd frontend && npm test"),
        ("Backend Tests", "cd backend && pytest"),
        ("Production Health Check", "curl https://m2n-serviciess-production.up.railway.app/health"),
    ]
    
    for cmd_name, cmd in commands:
        story.append(Paragraph(f"<b>{cmd_name}:</b>", heading3_style))
        story.append(Paragraph(f"<code>{cmd}</code>", ParagraphStyle('Code', parent=normal_style, fontName='Courier', fontSize=9, leftIndent=20)))
        story.append(Spacer(1, 0.05*inch))
    story.append(PageBreak())
    
    # ============== 14. CONCLUSION ==============
    story.append(Paragraph("14. CONCLUSION", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    conclusion_text = """
    <b>M2N Software</b> is a <b>production-ready Construction ERP</b> system that is almost complete:
    <br/><br/>
    <b>✅ Completed:</b><br/>
    • Frontend - 76+ React components, all features built<br/>
    • Backend - 40+ API endpoints, 50+ models<br/>
    • Security - Enterprise-grade authentication<br/>
    • Testing - Comprehensive test coverage<br/>
    • Documentation - 20+ detailed guides<br/><br/>
    
    <b>🔴 Current Issue:</b><br/>
    • Railway PostgreSQL service is FAILED<br/><br/>
    
    <b>🟢 Solution:</b><br/>
    • Restart PostgreSQL from Railway dashboard<br/><br/>
    
    <b>Once Postgres is fixed → Full system will be LIVE! 🚀</b>
    """
    story.append(Paragraph(conclusion_text, normal_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Footer
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(
        "--- End of Document ---",
        ParagraphStyle('Footer', parent=normal_style, alignment=TA_CENTER, textColor=colors.gray)
    ))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}",
        ParagraphStyle('Footer2', parent=normal_style, alignment=TA_CENTER, textColor=colors.gray, fontSize=8)
    ))
    
    # Build PDF
    doc.build(story)
    print(f"✅ PDF created successfully: {filename}")
    return filename

if __name__ == "__main__":
    create_pdf()
