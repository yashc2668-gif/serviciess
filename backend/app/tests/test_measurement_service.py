"""Targeted service coverage for measurement and work-done flows."""

import unittest
from datetime import date
from decimal import Decimal

from fastapi import HTTPException

from app.models.audit_log import AuditLog
from app.models.boq import BOQItem
from app.models.contract import Contract
from app.models.project import Project
from app.models.work_done import WorkDoneItem
from app.schemas.measurement import MeasurementCreate, MeasurementItemCreate, MeasurementUpdate
from app.services.measurement_service import (
    approve_measurement,
    create_measurement,
    delete_measurement,
    get_measurement_or_404,
    list_measurements,
    submit_measurement,
    update_measurement,
)
from app.services.work_done_service import list_work_done
from app.tests.helpers import OperationsDbTestCase
from app.utils.pagination import PaginationParams


class MeasurementServiceTests(OperationsDbTestCase):
    def test_create_update_delete_and_list_draft_measurement(self):
        boq_item = self.create_boq_item(quantity=100, rate=25)

        created = create_measurement(
            self.db,
            MeasurementCreate(
                contract_id=self.contract.id,
                measurement_no="MS-001",
                measurement_date=date(2026, 3, 20),
                remarks="Initial draft",
                items=[
                    MeasurementItemCreate(
                        boq_item_id=boq_item.id,
                        current_quantity=10,
                        amount=0,
                        remarks="Foundation segment A",
                    )
                ],
            ),
            self.user,
        )
        fetched = get_measurement_or_404(self.db, created.id)
        listed = list_measurements(
            self.db,
            contract_id=self.contract.id,
            status_filter="draft",
            pagination=PaginationParams(page=1, limit=20, skip=0),
        )
        created_amount = float(created.items[0].amount)
        updated = update_measurement(
            self.db,
            created.id,
            MeasurementUpdate(
                measurement_date=date(2026, 3, 21),
                remarks="Updated draft",
                items=[
                    MeasurementItemCreate(
                        boq_item_id=boq_item.id,
                        current_quantity=12,
                        rate=30,
                        amount=0,
                        remarks="Foundation segment B",
                    )
                ],
            ),
        )

        self.assertEqual(created.status, "draft")
        self.assertEqual(created.created_by, self.user.id)
        self.assertEqual(float(created.items[0].previous_quantity), 0.0)
        self.assertEqual(created_amount, 250.0)
        self.assertEqual(fetched.id, created.id)
        self.assertEqual(listed["total"], 1)
        self.assertEqual(float(updated.items[0].current_quantity), 12.0)
        self.assertEqual(float(updated.items[0].rate), 30.0)
        self.assertEqual(float(updated.items[0].amount), 360.0)
        self.assertEqual(updated.remarks, "Updated draft")

        delete_measurement(self.db, created.id)

        with self.assertRaises(HTTPException) as missing_measurement:
            get_measurement_or_404(self.db, created.id)

        self.assertEqual(missing_measurement.exception.status_code, 404)

    def test_measurement_rejects_duplicate_numbers_and_boq_scope_mismatch(self):
        boq_item = self.create_boq_item(quantity=50, rate=20)
        create_measurement(
            self.db,
            MeasurementCreate(
                contract_id=self.contract.id,
                measurement_no="MS-DUP",
                measurement_date=date(2026, 3, 20),
                items=[MeasurementItemCreate(boq_item_id=boq_item.id, current_quantity=5, amount=0)],
            ),
            self.user,
        )

        other_project = Project(
            company_id=self.company.id,
            name="Mismatch Project",
            code="MIS-PRJ-001",
            original_value=Decimal("10000"),
            revised_value=Decimal("10000"),
            status="active",
        )
        self.db.add(other_project)
        self.db.flush()
        other_contract = Contract(
            project_id=other_project.id,
            vendor_id=self.vendor.id,
            contract_no="MIS-CTR-001",
            title="Mismatch Contract",
            original_value=Decimal("10000"),
            revised_value=Decimal("10000"),
            retention_percentage=Decimal("5.00"),
            status="active",
        )
        self.db.add(other_contract)
        self.db.flush()
        other_boq = BOQItem(
            contract_id=other_contract.id,
            item_code="OTHER-BOQ",
            description="Other BOQ Row",
            unit="cum",
            quantity=Decimal("10"),
            rate=Decimal("10"),
            amount=Decimal("100"),
            category="Civil",
        )
        self.db.add(other_boq)
        self.db.commit()

        with self.assertRaises(HTTPException) as duplicate_number:
            create_measurement(
                self.db,
                MeasurementCreate(
                    contract_id=self.contract.id,
                    measurement_no="MS-DUP",
                    measurement_date=date(2026, 3, 21),
                    items=[MeasurementItemCreate(boq_item_id=boq_item.id, current_quantity=2, amount=0)],
                ),
                self.user,
            )

        with self.assertRaises(HTTPException) as boq_scope_mismatch:
            create_measurement(
                self.db,
                MeasurementCreate(
                    contract_id=self.contract.id,
                    measurement_no="MS-MISMATCH",
                    measurement_date=date(2026, 3, 21),
                    items=[MeasurementItemCreate(boq_item_id=other_boq.id, current_quantity=2, amount=0)],
                ),
                self.user,
            )

        self.assertEqual(duplicate_number.exception.status_code, 400)
        self.assertEqual(boq_scope_mismatch.exception.status_code, 400)

    def test_submit_and_approve_measurement_create_work_done_entries_and_audits(self):
        boq_item = self.create_boq_item(quantity=100, rate=50)
        measurement = create_measurement(
            self.db,
            MeasurementCreate(
                contract_id=self.contract.id,
                measurement_no="MS-APPROVE",
                measurement_date=date(2026, 3, 22),
                remarks="Ready for approval",
                items=[MeasurementItemCreate(boq_item_id=boq_item.id, current_quantity=20, amount=0)],
            ),
            self.user,
        )

        submitted = submit_measurement(self.db, measurement.id, self.user)
        self.assertEqual(submitted.status, "submitted")
        self.assertEqual(submitted.submitted_by, self.user.id)
        approved = approve_measurement(self.db, measurement.id, self.user)
        work_done_rows = (
            self.db.query(WorkDoneItem)
            .filter(WorkDoneItem.measurement_id == measurement.id)
            .all()
        )
        submit_audit = (
            self.db.query(AuditLog)
            .filter(AuditLog.entity_type == "measurement", AuditLog.entity_id == measurement.id, AuditLog.action == "submit")
            .one()
        )
        approve_audit = (
            self.db.query(AuditLog)
            .filter(AuditLog.entity_type == "measurement", AuditLog.entity_id == measurement.id, AuditLog.action == "approve")
            .one()
        )
        by_contract = list_work_done(
            self.db,
            contract_id=self.contract.id,
            pagination=PaginationParams(page=1, limit=20, skip=0),
        )
        by_measurement = list_work_done(
            self.db,
            measurement_id=measurement.id,
            pagination=PaginationParams(page=1, limit=20, skip=0),
        )

        self.assertEqual(approved.status, "approved")
        self.assertEqual(approved.approved_by, self.user.id)
        self.assertEqual(len(work_done_rows), 1)
        self.assertEqual(float(work_done_rows[0].current_quantity), 20.0)
        self.assertEqual(by_contract["total"], 1)
        self.assertEqual(by_measurement["total"], 1)
        self.assertEqual(submit_audit.after_data["status"], "submitted")
        self.assertEqual(approve_audit.after_data["work_done_count"], 1)

    def test_measurement_submission_and_transition_guards(self):
        empty_measurement = create_measurement(
            self.db,
            MeasurementCreate(
                contract_id=self.contract.id,
                measurement_no="MS-EMPTY",
                measurement_date=date(2026, 3, 23),
                items=[],
            ),
            self.user,
        )
        boq_item = self.create_boq_item(quantity=40, rate=10)
        ready_measurement = create_measurement(
            self.db,
            MeasurementCreate(
                contract_id=self.contract.id,
                measurement_no="MS-SUBMIT",
                measurement_date=date(2026, 3, 23),
                items=[MeasurementItemCreate(boq_item_id=boq_item.id, current_quantity=5, amount=0)],
            ),
            self.user,
        )

        with self.assertRaises(HTTPException) as no_items:
            submit_measurement(self.db, empty_measurement.id, self.user)

        submit_measurement(self.db, ready_measurement.id, self.user)

        with self.assertRaises(HTTPException) as non_draft_update:
            update_measurement(
                self.db,
                ready_measurement.id,
                MeasurementUpdate(remarks="Should fail"),
            )

        with self.assertRaises(HTTPException) as non_draft_delete:
            delete_measurement(self.db, ready_measurement.id)

        with self.assertRaises(HTTPException) as second_submit:
            submit_measurement(self.db, ready_measurement.id, self.user)

        self.assertEqual(no_items.exception.status_code, 400)
        self.assertEqual(non_draft_update.exception.status_code, 400)
        self.assertEqual(non_draft_delete.exception.status_code, 400)
        self.assertEqual(second_submit.exception.status_code, 400)

    def test_measurement_excess_rules_cover_warning_and_threshold_validation(self):
        boq_item = self.create_boq_item(quantity=100, rate=15)

        baseline = create_measurement(
            self.db,
            MeasurementCreate(
                contract_id=self.contract.id,
                measurement_no="MS-BASE",
                measurement_date=date(2026, 3, 24),
                items=[MeasurementItemCreate(boq_item_id=boq_item.id, current_quantity=95, amount=0)],
            ),
            self.user,
        )
        submit_measurement(self.db, baseline.id, self.user)
        approve_measurement(self.db, baseline.id, self.user)

        warning_measurement = create_measurement(
            self.db,
            MeasurementCreate(
                contract_id=self.contract.id,
                measurement_no="MS-WARN",
                measurement_date=date(2026, 3, 25),
                items=[
                    MeasurementItemCreate(
                        boq_item_id=boq_item.id,
                        current_quantity=10,
                        amount=0,
                        allow_excess=True,
                    )
                ],
            ),
            self.user,
        )

        with self.assertRaises(HTTPException) as missing_allow_excess:
            create_measurement(
                self.db,
                MeasurementCreate(
                    contract_id=self.contract.id,
                    measurement_no="MS-BLOCK",
                    measurement_date=date(2026, 3, 25),
                    items=[MeasurementItemCreate(boq_item_id=boq_item.id, current_quantity=6, amount=0)],
                ),
                self.user,
            )

        submit_measurement(self.db, warning_measurement.id, self.user)
        approve_measurement(self.db, warning_measurement.id, self.user)

        with self.assertRaises(HTTPException) as absurd_excess:
            create_measurement(
                self.db,
                MeasurementCreate(
                    contract_id=self.contract.id,
                    measurement_no="MS-THRESHOLD",
                    measurement_date=date(2026, 3, 26),
                    items=[
                        MeasurementItemCreate(
                            boq_item_id=boq_item.id,
                            current_quantity=21,
                            amount=0,
                            allow_excess=True,
                        )
                    ],
                ),
                self.user,
            )

        self.assertIn("exceeds BOQ quantity", warning_measurement.items[0].warning_message)
        self.assertEqual(missing_allow_excess.exception.status_code, 400)
        self.assertEqual(absurd_excess.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
