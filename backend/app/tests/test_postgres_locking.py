"""Regression tests for PostgreSQL row locking on eager-loaded queries."""

import unittest

import app.db.base  # noqa: F401
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import joinedload, sessionmaker

from app.db.session import Base
from app.models.payment import Payment
from app.models.ra_bill import RABill
from app.services.concurrency_service import apply_write_lock


class _FakePostgresBind:
    class dialect:  # noqa: D106
        name = "postgresql"


class _FakePostgresSession:
    def get_bind(self):
        return _FakePostgresBind()


class PostgresLockingQueryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()
        self.pg_db = _FakePostgresSession()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_ra_bill_lock_targets_primary_table_with_joinedload(self):
        query = self.db.query(RABill).options(
            joinedload(RABill.items),
            joinedload(RABill.payment_allocations),
        )

        sql = str(
            apply_write_lock(query, self.pg_db).statement.compile(
                dialect=postgresql.dialect(),
            )
        )

        self.assertIn("LEFT OUTER JOIN", sql.upper())
        self.assertIn("FOR UPDATE OF ra_bills", sql)

    def test_payment_lock_targets_primary_table_with_joinedload(self):
        query = self.db.query(Payment).options(joinedload(Payment.allocations))

        sql = str(
            apply_write_lock(query, self.pg_db).statement.compile(
                dialect=postgresql.dialect(),
            )
        )

        self.assertIn("LEFT OUTER JOIN", sql.upper())
        self.assertIn("FOR UPDATE OF payments", sql)


if __name__ == "__main__":
    unittest.main()
