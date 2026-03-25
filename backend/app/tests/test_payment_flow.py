"""Payment flow integration tests."""

import unittest

from app.models.audit_log import AuditLog
from app.models.payment import Payment
from app.models.ra_bill import RABill
from app.schemas.payment import PaymentAllocationCreate, PaymentCreate
from app.services.payment_service import (
    allocate_payment,
    approve_payment,
    create_payment,
    release_payment,
)
from app.tests.helpers import FinanceDbTestCase


class PaymentFlowTests(FinanceDbTestCase):
    def test_payment_partial_and_full_settlement_with_multiple_allocations(self):
        first_bill = self.create_ra_bill(bill_no=1, net_payable="1000.00")
        second_bill = self.create_ra_bill(bill_no=2, net_payable="1500.00")

        first_payment = create_payment(
            self.db,
            PaymentCreate(
                contract_id=self.contract.id,
                payment_date=first_bill.bill_date,
                amount=1000,
                remarks="First payment",
            ),
            self.user,
        )
        approve_payment(self.db, first_payment.id, self.user)
        release_payment(self.db, first_payment.id, self.user)
        allocate_payment(
            self.db,
            first_payment.id,
            [
                PaymentAllocationCreate(ra_bill_id=first_bill.id, amount=400),
                PaymentAllocationCreate(ra_bill_id=second_bill.id, amount=600),
            ],
            self.user,
        )

        first_payment = self.db.query(Payment).filter(Payment.id == first_payment.id).first()
        first_bill = self.db.query(RABill).filter(RABill.id == first_bill.id).first()
        second_bill = self.db.query(RABill).filter(RABill.id == second_bill.id).first()
        self.assertEqual(len(first_payment.allocations), 2)
        self.assertEqual(float(first_payment.allocated_amount), 1000.0)
        self.assertEqual(float(first_payment.available_amount), 0.0)
        self.assertEqual(first_bill.status, "partially_paid")
        self.assertEqual(second_bill.status, "partially_paid")
        self.assertEqual(float(first_bill.outstanding_amount), 600.0)
        self.assertEqual(float(second_bill.outstanding_amount), 900.0)

        second_payment = create_payment(
            self.db,
            PaymentCreate(
                contract_id=self.contract.id,
                payment_date=first_bill.bill_date,
                amount=1500,
                remarks="Second payment",
            ),
            self.user,
        )
        approve_payment(self.db, second_payment.id, self.user)
        release_payment(self.db, second_payment.id, self.user)
        allocate_payment(
            self.db,
            second_payment.id,
            [
                PaymentAllocationCreate(ra_bill_id=first_bill.id, amount=600),
                PaymentAllocationCreate(ra_bill_id=second_bill.id, amount=900),
            ],
            self.user,
        )

        second_payment = self.db.query(Payment).filter(Payment.id == second_payment.id).first()
        first_bill = self.db.query(RABill).filter(RABill.id == first_bill.id).first()
        second_bill = self.db.query(RABill).filter(RABill.id == second_bill.id).first()
        self.assertEqual(len(second_payment.allocations), 2)
        self.assertEqual(float(second_payment.allocated_amount), 1500.0)
        self.assertEqual(float(second_payment.available_amount), 0.0)
        self.assertEqual(first_bill.status, "paid")
        self.assertEqual(second_bill.status, "paid")
        self.assertEqual(float(first_bill.outstanding_amount), 0.0)
        self.assertEqual(float(second_bill.outstanding_amount), 0.0)

    def test_payment_create_writes_audit_log(self):
        payment = create_payment(
            self.db,
            PaymentCreate(
                contract_id=self.contract.id,
                payment_date=self.create_ra_bill(bill_no=11).bill_date,
                amount=750,
                remarks="Audit payment create",
            ),
            self.user,
        )

        audit_log = (
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "payment",
                AuditLog.entity_id == payment.id,
                AuditLog.action == "create",
            )
            .first()
        )

        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.performed_by, self.user.id)
        self.assertIsNone(audit_log.before_data)
        self.assertEqual(audit_log.after_data["status"], "draft")
        self.assertEqual(audit_log.after_data["contract_id"], self.contract.id)


if __name__ == "__main__":
    unittest.main()
