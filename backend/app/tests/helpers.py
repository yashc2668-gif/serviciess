"""Shared test helpers for in-memory finance scenarios."""

import unittest
from datetime import date
from decimal import Decimal

import app.db.base  # noqa: F401
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.boq import BOQItem
from app.models.company import Company
from app.models.contract import Contract
from app.models.deduction import Deduction
from app.models.labour import Labour
from app.models.labour_contractor import LabourContractor
from app.models.payment import Payment
from app.models.payment_allocation import PaymentAllocation
from app.models.project import Project
from app.models.ra_bill import RABill
from app.models.secured_advance import SecuredAdvance
from app.models.user import User
from app.models.vendor import Vendor


class FinanceDbTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.company = Company(name="Test Company")
        self.user = User(
            full_name="Finance Admin",
            email="finance-admin@example.com",
            hashed_password="not-used",
            role="admin",
            is_active=True,
        )
        self.vendor = Vendor(name="Test Vendor", code="VEN-001", vendor_type="contractor")
        self.db.add_all([self.company, self.user, self.vendor])
        self.db.flush()

        self.project = Project(
            company_id=self.company.id,
            name="Finance Test Project",
            code="PRJ-001",
            original_value=Decimal("100000.00"),
            revised_value=Decimal("100000.00"),
            status="active",
        )
        self.db.add(self.project)
        self.db.flush()

        self.contract = Contract(
            project_id=self.project.id,
            vendor_id=self.vendor.id,
            contract_no="CTR-001",
            title="Finance Test Contract",
            original_value=Decimal("100000.00"),
            revised_value=Decimal("100000.00"),
            retention_percentage=Decimal("5.00"),
            status="active",
        )
        self.db.add(self.contract)
        self.db.commit()
        self.db.refresh(self.company)
        self.db.refresh(self.user)
        self.db.refresh(self.vendor)
        self.db.refresh(self.project)
        self.db.refresh(self.contract)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def create_ra_bill(
        self,
        *,
        bill_no: int,
        status: str = "approved",
        net_payable: str | float = "0",
        gross_amount: str | float | None = None,
        total_deductions: str | float | None = None,
        bill_date: date | None = None,
        remarks: str | None = None,
    ) -> RABill:
        net_decimal = Decimal(str(net_payable))
        gross_decimal = Decimal(str(gross_amount if gross_amount is not None else net_decimal))
        deductions_decimal = Decimal(
            str(total_deductions if total_deductions is not None else gross_decimal - net_decimal)
        )
        bill = RABill(
            contract_id=self.contract.id,
            bill_no=bill_no,
            bill_date=bill_date or date(2026, 3, 24),
            gross_amount=gross_decimal,
            total_deductions=deductions_decimal,
            net_payable=net_decimal,
            status=status,
            remarks=remarks,
        )
        self.db.add(bill)
        self.db.commit()
        self.db.refresh(bill)
        return bill

    def add_deduction(
        self,
        bill: RABill,
        *,
        deduction_type: str,
        amount: str | float,
        description: str | None = None,
        reason: str | None = None,
        secured_advance_id: int | None = None,
    ) -> Deduction:
        deduction = Deduction(
            ra_bill_id=bill.id,
            deduction_type=deduction_type,
            amount=Decimal(str(amount)),
            description=description,
            reason=reason,
            secured_advance_id=secured_advance_id,
        )
        self.db.add(deduction)
        self.db.commit()
        self.db.refresh(deduction)
        self.db.refresh(bill)
        return deduction

    def create_payment_record(
        self,
        *,
        amount: str | float,
        status: str = "released",
        remarks: str | None = None,
    ) -> Payment:
        payment = Payment(
            contract_id=self.contract.id,
            payment_date=date(2026, 3, 24),
            amount=Decimal(str(amount)),
            status=status,
            remarks=remarks,
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def add_allocation(
        self,
        *,
        payment: Payment,
        bill: RABill,
        amount: str | float,
        remarks: str | None = None,
    ) -> PaymentAllocation:
        allocation = PaymentAllocation(
            payment_id=payment.id,
            ra_bill_id=bill.id,
            amount=Decimal(str(amount)),
            remarks=remarks,
        )
        self.db.add(allocation)
        self.db.commit()
        self.db.refresh(payment)
        self.db.refresh(bill)
        return allocation

    def create_secured_advance(
        self,
        *,
        advance_amount: str | float,
        balance: str | float,
        description: str = "Secured Advance",
    ) -> SecuredAdvance:
        advance_amount_decimal = Decimal(str(advance_amount))
        balance_decimal = Decimal(str(balance))
        advance = SecuredAdvance(
            contract_id=self.contract.id,
            advance_date=date(2026, 3, 24),
            description=description,
            advance_amount=advance_amount_decimal,
            recovered_amount=advance_amount_decimal - balance_decimal,
            balance=balance_decimal,
            status="active",
            issued_by=self.user.id,
        )
        self.db.add(advance)
        self.db.commit()
        self.db.refresh(advance)
        return advance


class OperationsDbTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.company = Company(name="Ops Test Company")
        self.user = User(
            full_name="Ops Admin",
            email="ops-admin@example.com",
            hashed_password="not-used",
            role="admin",
            is_active=True,
        )
        self.vendor = Vendor(name="Ops Vendor", code="OPS-VEN-001", vendor_type="supplier")
        self.db.add_all([self.company, self.user, self.vendor])
        self.db.flush()

        self.user.company_id = self.company.id
        self.vendor.company_id = self.company.id

        self.project = Project(
            company_id=self.company.id,
            name="Ops Test Project",
            code="OPS-PRJ-001",
            original_value=Decimal("50000.00"),
            revised_value=Decimal("50000.00"),
            status="active",
        )
        self.db.add(self.project)
        self.db.flush()

        self.contract = Contract(
            project_id=self.project.id,
            vendor_id=self.vendor.id,
            contract_no="OPS-CTR-001",
            title="Ops Contract",
            original_value=Decimal("50000.00"),
            revised_value=Decimal("50000.00"),
            retention_percentage=Decimal("5.00"),
            status="active",
        )
        self.db.add(self.contract)
        self.db.commit()
        self.db.refresh(self.company)
        self.db.refresh(self.user)
        self.db.refresh(self.vendor)
        self.db.refresh(self.project)
        self.db.refresh(self.contract)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def create_boq_item(
        self,
        *,
        item_code: str = "BOQ-001",
        description: str = "Excavation",
        unit: str = "cum",
        quantity: str | float = "100",
        rate: str | float = "25",
        amount: str | float | None = None,
        category: str | None = "Civil",
    ) -> BOQItem:
        boq_item = BOQItem(
            contract_id=self.contract.id,
            item_code=item_code,
            description=description,
            unit=unit,
            quantity=Decimal(str(quantity)),
            rate=Decimal(str(rate)),
            amount=Decimal(str(amount if amount is not None else Decimal(str(quantity)) * Decimal(str(rate)))),
            category=category,
        )
        self.db.add(boq_item)
        self.db.commit()
        self.db.refresh(boq_item)
        return boq_item

    def create_labour_contractor(
        self,
        *,
        contractor_code: str = "LCTR-001",
        contractor_name: str = "Alpha Labour Supplier",
    ) -> LabourContractor:
        contractor = LabourContractor(
            company_id=self.company.id,
            contractor_code=contractor_code,
            contractor_name=contractor_name,
            contact_person=f"{contractor_name} Contact",
            phone="9999999999",
        )
        self.db.add(contractor)
        self.db.commit()
        self.db.refresh(contractor)
        return contractor

    def create_labour(
        self,
        *,
        labour_code: str = "LAB-001",
        full_name: str = "Ramesh Kumar",
        trade: str = "Mason",
        contractor_id: int | None = None,
    ) -> Labour:
        labour = Labour(
            company_id=self.company.id,
            labour_code=labour_code,
            full_name=full_name,
            trade=trade,
            skill_level="Skilled",
            daily_rate=Decimal("700"),
            skill_type=trade,
            default_wage_rate=Decimal("700"),
            unit="day",
            contractor_id=contractor_id,
            is_active=True,
        )
        self.db.add(labour)
        self.db.commit()
        self.db.refresh(labour)
        return labour
