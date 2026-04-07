"""Service coverage for the BBS register."""

import unittest

from fastapi import HTTPException

from app.models.contract import Contract
from app.models.project import Project
from app.schemas.bbs import BBSCreate, BBSUpdate
from app.services.bbs_service import (
    create_bbs_entry,
    delete_bbs_entry,
    get_bbs_or_404,
    list_bbs_entries,
    update_bbs_entry,
)
from app.tests.helpers import OperationsDbTestCase
from app.utils.pagination import PaginationParams


class BBSServiceTests(OperationsDbTestCase):
    def test_create_update_delete_and_list_bbs_entry(self):
        created = create_bbs_entry(
            self.db,
            BBSCreate(
                contract_id=self.contract.id,
                drawing_no="T-E-BBS-001",
                member_location="Core wall level 1",
                bar_mark="CW-01",
                dia_mm=12,
                cut_length_mm=2450,
                shape_code="21",
                nos=8,
                unit_weight=2.178,
                remarks="Initial BBS row",
            ),
        )
        listed = list_bbs_entries(
            self.db,
            contract_id=self.contract.id,
            pagination=PaginationParams(page=1, limit=20, skip=0),
        )
        created_total_weight = float(created.total_weight)
        updated = update_bbs_entry(
            self.db,
            created.id,
            BBSUpdate(
                member_location="Core wall level 2",
                nos=10,
                unit_weight=2.500,
                remarks="Updated BBS row",
                lock_version=created.lock_version,
            ),
        )

        self.assertEqual(created.drawing_no, "T-E-BBS-001")
        self.assertEqual(created_total_weight, 17.424)
        self.assertEqual(listed["total"], 1)
        self.assertEqual(updated.member_location, "Core wall level 2")
        self.assertEqual(float(updated.total_weight), 25.0)
        self.assertEqual(updated.lock_version, 2)

        delete_bbs_entry(self.db, created.id)

        with self.assertRaises(HTTPException) as missing_bbs:
            get_bbs_or_404(self.db, created.id)

        self.assertEqual(missing_bbs.exception.status_code, 404)

    def test_list_bbs_supports_project_and_search_filters(self):
        create_bbs_entry(
            self.db,
            BBSCreate(
                contract_id=self.contract.id,
                drawing_no="TOWER-E-BBS",
                member_location="Tower-E core",
                bar_mark="TE-01",
                dia_mm=10,
                cut_length_mm=2000,
                shape_code="11",
                nos=4,
                unit_weight=1.25,
            ),
        )

        other_project = Project(
            company_id=self.company.id,
            name="Other Project",
            code="OPS-PRJ-002",
            original_value=1000,
            revised_value=1000,
            status="active",
        )
        self.db.add(other_project)
        self.db.flush()
        other_contract = Contract(
            project_id=other_project.id,
            vendor_id=self.vendor.id,
            contract_no="OPS-CTR-002",
            title="Other Contract",
            original_value=1000,
            revised_value=1000,
            retention_percentage=5,
            status="active",
        )
        self.db.add(other_contract)
        self.db.commit()
        self.db.refresh(other_contract)

        create_bbs_entry(
            self.db,
            BBSCreate(
                contract_id=other_contract.id,
                drawing_no="OTHER-BBS",
                member_location="Other member",
                bar_mark="OT-01",
                dia_mm=8,
                cut_length_mm=1800,
                shape_code="12",
                nos=6,
                unit_weight=0.95,
            ),
        )

        by_project = list_bbs_entries(
            self.db,
            project_id=self.project.id,
            pagination=PaginationParams(page=1, limit=20, skip=0),
        )
        by_search = list_bbs_entries(
            self.db,
            search="core",
            pagination=PaginationParams(page=1, limit=20, skip=0),
        )

        self.assertEqual(by_project["total"], 1)
        self.assertEqual(by_search["total"], 1)
        self.assertEqual(by_search["items"][0].bar_mark, "TE-01")


if __name__ == "__main__":
    unittest.main()
