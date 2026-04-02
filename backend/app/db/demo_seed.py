"""Idempotent demo/UAT data seeding."""

from __future__ import annotations

import io
import json
from datetime import date
from decimal import Decimal

import app.db.base  # noqa: F401
from fastapi import UploadFile

from app.core.security import hash_password
from app.db.seed import run_seed
from app.db.session import SessionLocal
from app.models.boq import BOQItem
from app.models.company import Company
from app.models.contract import Contract
from app.models.measurement import Measurement
from app.models.measurement_item import MeasurementItem
from app.models.project import Project
from app.models.user import User
from app.models.vendor import Vendor
from app.models.work_done import WorkDoneItem
from app.schemas.payment import PaymentAllocationCreate, PaymentCreate
from app.schemas.ra_bill import RABillCreate
from app.services.document_service import (
    add_document_version_from_upload,
    create_document_from_upload,
)
from app.services.payment_service import (
    allocate_payment,
    approve_payment,
    create_payment,
    release_payment,
)
from app.services.ra_bill_service import (
    create_ra_bill_draft,
    generate_ra_bill_items,
    submit_ra_bill,
    transition_ra_bill_status,
)

DEMO_COMPANY_NAME = "M2N Demo Infra Pvt Ltd"
DEMO_PROJECT_CODE = "DEMO-PRJ-001"
DEMO_VENDOR_CODE = "DEMO-VEN-001"
DEMO_CONTRACT_NO = "DEMO-CTR-001"
DEMO_MEASUREMENT_NO = "DEMO-MEA-001"
DEMO_USERS = [
    ("demo-admin@example.com", "Demo Admin", "admin"),
    ("demo-pm@example.com", "Demo Project Manager", "project_manager"),
    ("demo-accounts@example.com", "Demo Accountant", "accountant"),
]
DEMO_PASSWORD = "DemoPass123!"


def _get_or_create_user(db, *, email: str, full_name: str, role: str, company_id: int) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(
        company_id=company_id,
        full_name=full_name,
        email=email,
        hashed_password=hash_password(DEMO_PASSWORD),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _get_or_create_company(db) -> Company:
    company = db.query(Company).filter(Company.name == DEMO_COMPANY_NAME).first()
    if company:
        return company
    company = Company(
        name=DEMO_COMPANY_NAME,
        address="Sector 21, Demo City",
        phone="+91-9000000000",
        email="info-demo@m2n.local",
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def _get_or_create_vendor(db) -> Vendor:
    vendor = db.query(Vendor).filter(Vendor.code == DEMO_VENDOR_CODE).first()
    if vendor:
        return vendor
    vendor = Vendor(
        name="Demo Build Partners",
        code=DEMO_VENDOR_CODE,
        vendor_type="contractor",
        contact_person="Rohit Demo",
        phone="+91-9555555555",
        email="vendor-demo@m2n.local",
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


def _get_or_create_project(db, company: Company) -> Project:
    project = db.query(Project).filter(Project.code == DEMO_PROJECT_CODE).first()
    if project:
        return project
    project = Project(
        company_id=company.id,
        name="Demo Commercial Tower",
        code=DEMO_PROJECT_CODE,
        client_name="Demo Realty",
        location="Bengaluru",
        original_value=Decimal("25000000.00"),
        revised_value=Decimal("25500000.00"),
        status="active",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def _get_or_create_contract(db, project: Project, vendor: Vendor) -> Contract:
    contract = db.query(Contract).filter(Contract.contract_no == DEMO_CONTRACT_NO).first()
    if contract:
        return contract
    contract = Contract(
        project_id=project.id,
        vendor_id=vendor.id,
        contract_no=DEMO_CONTRACT_NO,
        title="Civil + Finishing Package",
        scope_of_work="Structure, masonry, plaster, and finishing",
        original_value=Decimal("15000000.00"),
        revised_value=Decimal("15250000.00"),
        retention_percentage=Decimal("5.00"),
        status="active",
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


def _get_or_create_boq(db, contract: Contract) -> list[BOQItem]:
    existing = db.query(BOQItem).filter(BOQItem.contract_id == contract.id).order_by(BOQItem.id.asc()).all()
    if existing:
        return existing

    boq_items = [
        BOQItem(
            contract_id=contract.id,
            item_code="DEMO-BOQ-001",
            description="RCC work",
            unit="cum",
            quantity=Decimal("100.000"),
            rate=Decimal("8500.00"),
            amount=Decimal("850000.00"),
        ),
        BOQItem(
            contract_id=contract.id,
            item_code="DEMO-BOQ-002",
            description="Block work",
            unit="sqm",
            quantity=Decimal("1200.000"),
            rate=Decimal("950.00"),
            amount=Decimal("1140000.00"),
        ),
    ]
    db.add_all(boq_items)
    db.commit()
    for boq in boq_items:
        db.refresh(boq)
    return boq_items


def _get_or_create_measurement_and_work_done(db, contract: Contract, boq_items: list[BOQItem], approver: User):
    measurement = db.query(Measurement).filter(Measurement.measurement_no == DEMO_MEASUREMENT_NO).first()
    if measurement:
        return measurement

    measurement = Measurement(
        contract_id=contract.id,
        measurement_no=DEMO_MEASUREMENT_NO,
        measurement_date=date(2026, 3, 20),
        status="approved",
        created_by=approver.id,
        approved_by=approver.id,
    )
    db.add(measurement)
    db.flush()

    items = [
        MeasurementItem(
            measurement_id=measurement.id,
            boq_item_id=boq_items[0].id,
            description_snapshot=boq_items[0].description,
            unit_snapshot=boq_items[0].unit,
            previous_quantity=Decimal("0.000"),
            current_quantity=Decimal("18.000"),
            cumulative_quantity=Decimal("18.000"),
            rate=boq_items[0].rate,
            amount=Decimal("153000.00"),
            allow_excess=False,
        ),
        MeasurementItem(
            measurement_id=measurement.id,
            boq_item_id=boq_items[1].id,
            description_snapshot=boq_items[1].description,
            unit_snapshot=boq_items[1].unit,
            previous_quantity=Decimal("0.000"),
            current_quantity=Decimal("220.000"),
            cumulative_quantity=Decimal("220.000"),
            rate=boq_items[1].rate,
            amount=Decimal("209000.00"),
            allow_excess=False,
        ),
    ]
    db.add_all(items)
    db.flush()

    work_done_entries = [
        WorkDoneItem(
            contract_id=contract.id,
            measurement_id=measurement.id,
            measurement_item_id=items[0].id,
            boq_item_id=boq_items[0].id,
            recorded_date=measurement.measurement_date,
            previous_quantity=items[0].previous_quantity,
            current_quantity=items[0].current_quantity,
            cumulative_quantity=items[0].cumulative_quantity,
            rate=items[0].rate,
            amount=items[0].amount,
            approved_by=approver.id,
        ),
        WorkDoneItem(
            contract_id=contract.id,
            measurement_id=measurement.id,
            measurement_item_id=items[1].id,
            boq_item_id=boq_items[1].id,
            recorded_date=measurement.measurement_date,
            previous_quantity=items[1].previous_quantity,
            current_quantity=items[1].current_quantity,
            cumulative_quantity=items[1].cumulative_quantity,
            rate=items[1].rate,
            amount=items[1].amount,
            approved_by=approver.id,
        ),
    ]
    db.add_all(work_done_entries)
    db.commit()
    db.refresh(measurement)
    return measurement


def _get_or_create_finance_flow(db, contract: Contract, actor: User):
    existing_bill = db.query(Contract).filter(Contract.id == contract.id).first()
    bill = existing_bill.ra_bills[0] if existing_bill and existing_bill.ra_bills else None
    payment = existing_bill.payments[0] if existing_bill and existing_bill.payments else None

    if bill is None:
        bill = create_ra_bill_draft(
            db,
            RABillCreate(
                contract_id=contract.id,
                bill_date=date(2026, 3, 24),
                remarks="Demo RA bill",
            ),
            actor,
        )

    if bill.status == "draft":
        bill = generate_ra_bill_items(db, bill.id, actor)
        bill = submit_ra_bill(db, bill.id, actor, remarks="Demo submit")
    if bill.status in {"submitted", "finance_hold"}:
        bill = transition_ra_bill_status(db, bill.id, "verified", actor, remarks="Demo verify")
    if bill.status == "verified":
        bill = transition_ra_bill_status(db, bill.id, "approved", actor, remarks="Demo approve")

    if payment is None:
        payment = create_payment(
            db,
            PaymentCreate(
                contract_id=contract.id,
                payment_date=date(2026, 3, 25),
                amount=float(Decimal(str(bill.net_payable)) / 2),
                payment_mode="bank_transfer",
                reference_no="DEMO-PAY-001",
                remarks="Partial demo payment",
            ),
            actor,
        )

    if payment.status == "draft":
        payment = approve_payment(db, payment.id, actor, remarks="Demo payment approve")
    if payment.status == "approved":
        payment = release_payment(db, payment.id, actor, remarks="Demo payment release")
    if payment.status == "released" and not payment.allocations:
        allocation_amount = min(
            Decimal(str(payment.available_amount)),
            Decimal(str(bill.outstanding_amount)),
        )
        if allocation_amount > 0:
            payment = allocate_payment(
                db,
                payment.id,
                [PaymentAllocationCreate(ra_bill_id=bill.id, amount=float(allocation_amount))],
                actor,
            )
    return bill, payment


def _get_or_create_demo_documents(db, contract: Contract, payment, actor: User):
    existing = db.query(contract.__class__).filter(contract.__class__.id == contract.id).first()
    if existing is None:
        return None
    contract_doc = db.query(Contract).filter(Contract.id == contract.id).first()
    if contract_doc is None:
        return None

    from app.models.document import Document

    existing_document = (
        db.query(Document)
        .filter(Document.entity_type == "contract", Document.entity_id == contract.id)
        .first()
    )
    if existing_document:
        return existing_document

    document = create_document_from_upload(
        db,
        entity_type="contract",
        entity_id=contract.id,
        title="Signed Contract Copy",
        document_type="contract_scan",
        remarks="Demo seeded contract document",
        upload=UploadFile(filename="signed-contract.pdf", file=io.BytesIO(b"demo contract v1")),
        current_user=actor,
    )
    add_document_version_from_upload(
        db,
        document_id=document.id,
        remarks="Updated scan for demo",
        upload=UploadFile(filename="signed-contract-v2.pdf", file=io.BytesIO(b"demo contract v2")),
        current_user=actor,
    )
    return document


def run_demo_seed() -> dict:
    run_seed()
    db = SessionLocal()
    try:
        company = _get_or_create_company(db)
        users = {
            role: _get_or_create_user(
                db,
                email=email,
                full_name=full_name,
                role=role,
                company_id=company.id,
            )
            for email, full_name, role in DEMO_USERS
        }
        vendor = _get_or_create_vendor(db)
        project = _get_or_create_project(db, company)
        contract = _get_or_create_contract(db, project, vendor)
        boq_items = _get_or_create_boq(db, contract)
        measurement = _get_or_create_measurement_and_work_done(db, contract, boq_items, users["admin"])
        bill, payment = _get_or_create_finance_flow(db, contract, users["admin"])
        document = _get_or_create_demo_documents(db, contract, payment, users["admin"])

        return {
            "company_id": company.id,
            "project_id": project.id,
            "contract_id": contract.id,
            "measurement_id": measurement.id,
            "ra_bill_id": bill.id,
            "payment_id": payment.id if payment else None,
            "document_id": document.id if document else None,
            "demo_users": {
                email: {
                    "role": role,
                    "password": DEMO_PASSWORD,
                }
                for email, _, role in DEMO_USERS
            },
        }
    finally:
        db.close()


if __name__ == "__main__":
    print(json.dumps(run_demo_seed(), indent=2))
