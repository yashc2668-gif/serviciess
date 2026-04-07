"""Focused coverage tests for PDF generation helpers."""

import unittest
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.services import pdf_service


class PDFServiceTests(unittest.TestCase):
    def test_formatters_and_style_factory_cover_none_paths(self):
        styles = pdf_service._build_styles()

        self.assertEqual(pdf_service._fmt_currency(None), "—")
        self.assertEqual(pdf_service._fmt_currency(Decimal("1250.5")), "₹ 1,250.50")
        self.assertEqual(pdf_service._fmt_date(None), "—")
        self.assertEqual(pdf_service._fmt_date(date(2026, 3, 29)), "29 Mar 2026")
        self.assertSetEqual(
            set(styles.keys()),
            {"title", "subtitle", "heading", "normal", "bold", "small"},
        )
        self.assertEqual(pdf_service._info_grid([("Project", "Metro Line")]).__class__.__name__, "Table")

    def test_generate_ra_bill_pdf_renders_items_deductions_and_summary(self):
        ra_bill = SimpleNamespace(
            bill_no=7,
            bill_date=date(2026, 3, 29),
            period_from=date(2026, 3, 1),
            period_to=date(2026, 3, 28),
            status="approved",
            gross_amount=Decimal("120000.00"),
            total_deductions=Decimal("8000.00"),
            net_payable=Decimal("112000.00"),
            items=[
                SimpleNamespace(
                    description_snapshot="Excavation for footing",
                    unit_snapshot="cum",
                    prev_quantity=Decimal("10"),
                    curr_quantity=Decimal("15"),
                    cumulative_quantity=Decimal("25"),
                    rate=Decimal("400"),
                    amount=Decimal("6000"),
                )
            ],
            deductions=[
                SimpleNamespace(
                    deduction_type="retention",
                    description="Retention hold",
                    percentage=Decimal("5.0"),
                    amount=Decimal("8000"),
                )
            ],
        )
        contract = SimpleNamespace(contract_no="CTR-001", title="Civil Package")
        project = SimpleNamespace(name="Metro Depot")
        vendor = SimpleNamespace(name="Alpha Infra")

        rendered = pdf_service.generate_ra_bill_pdf(ra_bill, contract, project, vendor)

        self.assertTrue(rendered.startswith(b"%PDF"))
        self.assertGreater(len(rendered), 1500)

    def test_generate_payment_voucher_pdf_renders_allocations_and_remarks(self):
        payment = SimpleNamespace(
            id=14,
            payment_date=date(2026, 3, 29),
            payment_mode="neft",
            reference_no="NEFT-20260329-14",
            status="released",
            amount=Decimal("50000.00"),
            remarks="Released after finance approval.",
            allocations=[
                SimpleNamespace(ra_bill_id=3, amount=Decimal("30000")),
                SimpleNamespace(ra_bill_id=4, amount=Decimal("20000")),
            ],
        )
        contract = SimpleNamespace(contract_no="CTR-002", title="Finishing Package")
        project = SimpleNamespace(name="Airport Terminal")
        vendor = SimpleNamespace(name="Beta Works")

        rendered = pdf_service.generate_payment_voucher_pdf(payment, contract, project, vendor)

        self.assertTrue(rendered.startswith(b"%PDF"))
        self.assertGreater(len(rendered), 1400)

    def test_generate_measurement_and_labour_bill_pdfs_render_optional_sections(self):
        measurement = SimpleNamespace(
            measurement_no="MS-014",
            measurement_date=date(2026, 3, 18),
            status="approved",
            remarks="Jointly verified with site engineer.",
            items=[
                SimpleNamespace(
                    item_code="BOQ-01",
                    description="PCC bed concrete",
                    unit="cum",
                    quantity=Decimal("18.5"),
                    remarks="Foundation strip A",
                )
            ],
            work_done_entries=[
                SimpleNamespace(
                    boq_item_code="BOQ-01",
                    description="PCC bed concrete",
                    quantity=Decimal("18.5"),
                    rate=Decimal("4500"),
                    amount=Decimal("83250"),
                )
            ],
        )
        labour_bill = SimpleNamespace(
            bill_no="LB-005",
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 15),
            status="verified",
            gross_amount=Decimal("64000"),
            deductions=Decimal("4000"),
            net_payable=Decimal("60000"),
            remarks="Attendance matched with muster roll.",
            items=[
                SimpleNamespace(
                    labour_name="Rakesh",
                    trade="Bar Bender",
                    days_worked=Decimal("12"),
                    daily_rate=Decimal("700"),
                    amount=Decimal("8400"),
                )
            ],
        )
        project = SimpleNamespace(name="Residential Tower")
        contract = SimpleNamespace(contract_no="CTR-003", title="Structural Steel")
        contractor = SimpleNamespace(contractor_name="Prime Labour Supply")

        measurement_pdf = pdf_service.generate_measurement_sheet_pdf(measurement, contract, project)
        labour_pdf = pdf_service.generate_labour_bill_pdf(
            labour_bill,
            contractor,
            project,
            contract,
        )

        self.assertTrue(measurement_pdf.startswith(b"%PDF"))
        self.assertTrue(labour_pdf.startswith(b"%PDF"))
        self.assertGreater(len(measurement_pdf), 1400)
        self.assertGreater(len(labour_pdf), 1400)

    def test_generate_contract_work_order_pdf_renders_manual_sections(self):
        work_order = SimpleNamespace(
            issuer_name="Omaxe Pancham Realcon Pvt. Ltd.",
            issuer_address="Lucknow Head Office",
            issuer_gst_number="09ABCDE1234F1Z5",
            issuer_contact="accounts@omaxe.com",
            recipient_label="Issued To",
            recipient_name="MARCO Enterprises",
            recipient_address="Noida, Uttar Pradesh",
            work_order_no="OPRL/OS2/11094103917",
            work_order_date=date(2026, 4, 6),
            project_name="Omaxe Shiva Phase-2 (GH-2)",
            project_location="Sangam City, Prayagraj, Uttar Pradesh",
            title="Civil Structure Work",
            subject="Award of civil structure work",
            scope_of_work="Complete civil structure package including shuttering, reinforcement, and concrete works.",
            start_date=date(2026, 5, 1),
            end_date=date(2027, 8, 31),
            original_value=Decimal("162074375"),
            revised_value=Decimal("162074375"),
            retention_percentage=Decimal("0"),
            payment_terms="Certified RA bills to be released within agreed cycle.",
            special_conditions="All work must follow issued drawings and QA checks.",
            signatory_name="Authorised Signatory",
            signatory_designation="Project Director",
        )
        contract = SimpleNamespace(
            contract_no="OPRL/OS2/11094103917",
            title="Civil Structure Work",
            contract_type="client_contract",
            scope_of_work="Civil structure work",
        )
        project = SimpleNamespace(
            name="Omaxe Shiva Phase-2 (GH-2)",
            location="Sangam City, Prayagraj, Uttar Pradesh",
        )
        company = SimpleNamespace(
            name="MARCO Enterprises",
            gst_number="09BLDPK5228H1Z2",
            phone="9910041120",
        )

        rendered = pdf_service.generate_contract_work_order_pdf(
            work_order,
            contract=contract,
            project=project,
            company=company,
            vendor=None,
        )

        self.assertTrue(rendered.startswith(b"%PDF"))
        self.assertGreater(len(rendered), 1800)


if __name__ == "__main__":
    unittest.main()
