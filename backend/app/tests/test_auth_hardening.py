"""Tests for Phase-1 security hardening additions.

Covers:
- Password policy: common-password rejection, email-in-password rejection
- Rate limiting on all auth endpoints (register, forgot-password, reset-password, refresh)
- Security headers (new additions: X-Permitted-Cross-Domain-Policies, Cache-Control, etc.)
- Audit log entries for auth events
- Constant-time comparisons (indirectly — functional correctness)
"""

import unittest
from unittest.mock import patch

import app.db.base  # noqa: F401
import main
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import hash_password, utc_now
from app.db.session import Base, get_db
from app.models.audit_log import AuditLog
from app.models.user import User


class PasswordPolicyHardeningTests(unittest.TestCase):
    """Tests for enhanced password policy (common passwords, email-in-password)."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=self.engine)

        session = self.SessionLocal()
        session.add(
            User(
                full_name="Test Admin",
                email="admin@example.com",
                hashed_password=hash_password("StrongPass1!"),
                role="admin",
                is_active=True,
                password_changed_at=utc_now(),
            )
        )
        session.commit()
        session.close()

        self.seed_patch = patch("main.run_seed", lambda: None)
        self.seed_patch.start()
        self.health_patch = patch(
            "main._database_health_payload",
            lambda: {"status": "ok", "database": "test", "user": "test", "ping": 1},
        )
        self.health_patch.start()

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        main.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        main.app.dependency_overrides.clear()
        self.health_patch.stop()
        self.seed_patch.stop()
        self.engine.dispose()

    def test_common_password_is_rejected_on_register(self):
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Common Pwd",
                "email": "common@example.com",
                "password": "P@ssw0rd",
                "role": "viewer",
            },
        )
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("too common", response.json()["error"]["message"].lower())

    def test_password_containing_email_local_part_is_rejected(self):
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Email Pwd",
                "email": "johndoe@example.com",
                "password": "Johndoe99!X",
                "role": "viewer",
            },
        )
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("email", response.json()["error"]["message"].lower())

    def test_strong_unique_password_passes_all_checks(self):
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Strong Pwd",
                "email": "strong@example.com",
                "password": "X7!kqm#Rz2Lp",
                "role": "viewer",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)

    def test_common_password_rejected_on_password_reset(self):
        with patch("app.services.auth_service.send_password_reset_otp_email") as send_email:
            self.client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "admin@example.com"},
            )
            send_email.assert_called_once()
            otp_code = send_email.call_args.kwargs["otp_code"]

        response = self.client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "admin@example.com",
                "otp_code": otp_code,
                "new_password": "Passw0rd!",
            },
        )
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("too common", response.json()["error"]["message"].lower())

    def test_email_in_password_rejected_on_admin_user_create(self):
        headers = self._admin_headers()
        response = self.client.post(
            "/api/v1/users/",
            headers=headers,
            json={
                "full_name": "New User",
                "email": "newuser@example.com",
                "password": "Newuser99!X",
                "role": "viewer",
            },
        )
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("email", response.json()["error"]["message"].lower())

    def _admin_headers(self) -> dict[str, str]:
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "StrongPass1!"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}


class SecurityHeadersHardeningTests(unittest.TestCase):
    """Tests for new security headers."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=self.engine)

        session = self.SessionLocal()
        session.add(
            User(
                full_name="Header Admin",
                email="header-admin@example.com",
                hashed_password=hash_password("StrongPass1!"),
                role="admin",
                is_active=True,
            )
        )
        session.commit()
        session.close()

        self.seed_patch = patch("main.run_seed", lambda: None)
        self.seed_patch.start()
        self.health_patch = patch(
            "main._database_health_payload",
            lambda: {"status": "ok", "database": "test", "user": "test", "ping": 1},
        )
        self.health_patch.start()

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        main.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        main.app.dependency_overrides.clear()
        self.health_patch.stop()
        self.seed_patch.stop()
        self.engine.dispose()

    def test_new_security_headers_are_present(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.headers.get("X-Permitted-Cross-Domain-Policies"),
            "none",
        )
        self.assertEqual(response.headers.get("X-DNS-Prefetch-Control"), "off")
        self.assertEqual(
            response.headers.get("Cross-Origin-Opener-Policy"),
            "same-origin",
        )

    def test_auth_responses_have_cache_control_no_store(self):
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "header-admin@example.com",
                "password": "StrongPass1!",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        cache_control = response.headers.get("Cache-Control", "")
        self.assertIn("no-store", cache_control)
        self.assertIn("no-cache", cache_control)
        self.assertEqual(response.headers.get("Pragma"), "no-cache")

    def test_non_auth_responses_do_not_have_cache_control_no_store(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200, response.text)
        cache_control = response.headers.get("Cache-Control", "")
        self.assertNotIn("no-store", cache_control)


class AuthAuditLogTests(unittest.TestCase):
    """Tests that auth events are persisted to the audit_logs table."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=self.engine)

        session = self.SessionLocal()
        session.add(
            User(
                full_name="Audit User",
                email="audit@example.com",
                hashed_password=hash_password("StrongPass1!"),
                role="viewer",
                is_active=True,
                password_changed_at=utc_now(),
            )
        )
        session.commit()
        session.close()

        self.seed_patch = patch("main.run_seed", lambda: None)
        self.seed_patch.start()
        self.health_patch = patch(
            "main._database_health_payload",
            lambda: {"status": "ok", "database": "test", "user": "test", "ping": 1},
        )
        self.health_patch.start()

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        main.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        main.app.dependency_overrides.clear()
        self.health_patch.stop()
        self.seed_patch.stop()
        self.engine.dispose()

    def _count_audit_events(self, action: str) -> int:
        session = self.SessionLocal()
        count = (
            session.query(AuditLog)
            .filter(AuditLog.entity_type == "auth", AuditLog.action == action)
            .count()
        )
        session.close()
        return count

    def test_successful_login_creates_audit_entry(self):
        self.assertEqual(self._count_audit_events("login_success"), 0)
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "audit@example.com", "password": "StrongPass1!"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertGreaterEqual(self._count_audit_events("login_success"), 1)

    def test_failed_login_creates_audit_entry(self):
        self.assertEqual(self._count_audit_events("login_failed"), 0)
        self.client.post(
            "/api/v1/auth/login",
            json={"email": "audit@example.com", "password": "WrongPass1!"},
        )
        self.assertGreaterEqual(self._count_audit_events("login_failed"), 1)

    def test_account_lockout_creates_audit_entry(self):
        for _ in range(settings.LOGIN_LOCKOUT_THRESHOLD):
            self.client.post(
                "/api/v1/auth/login",
                json={"email": "audit@example.com", "password": "WrongPass1!"},
            )
        self.assertGreaterEqual(self._count_audit_events("account_locked"), 1)

    def test_password_reset_creates_audit_entry(self):
        with patch("app.services.auth_service.send_password_reset_otp_email") as send_email:
            self.client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "audit@example.com"},
            )
            send_email.assert_called_once()
            otp_code = send_email.call_args.kwargs["otp_code"]

        response = self.client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "audit@example.com",
                "otp_code": otp_code,
                "new_password": "NewStr0ng!Pass",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertGreaterEqual(self._count_audit_events("password_reset"), 1)


class RateLimitAllEndpointsTests(unittest.TestCase):
    """Verify rate limiting is active on all auth endpoints."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=self.engine)

        session = self.SessionLocal()
        session.add(
            User(
                full_name="Rate Limit User",
                email="ratelimit@example.com",
                hashed_password=hash_password("StrongPass1!"),
                role="viewer",
                is_active=True,
            )
        )
        session.commit()
        session.close()

        self.seed_patch = patch("main.run_seed", lambda: None)
        self.seed_patch.start()
        self.health_patch = patch(
            "main._database_health_payload",
            lambda: {"status": "ok", "database": "test", "user": "test", "ping": 1},
        )
        self.health_patch.start()

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        main.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        main.app.dependency_overrides.clear()
        self.health_patch.stop()
        self.seed_patch.stop()
        self.engine.dispose()

    def _rate_limit_headers(self, unique_ip: str) -> dict[str, str]:
        return {
            "X-RateLimit-Test": "1",
            "X-Forwarded-For": unique_ip,
        }

    def test_register_is_rate_limited(self):
        headers = self._rate_limit_headers("10.0.0.1")
        last_response = None
        for i in range(5):
            last_response = self.client.post(
                "/api/v1/auth/register",
                headers=headers,
                json={
                    "full_name": f"Rate User {i}",
                    "email": f"rate-reg-{i}@example.com",
                    "password": "StrongPass1!",
                    "role": "viewer",
                },
            )
        self.assertIsNotNone(last_response)
        self.assertEqual(last_response.status_code, 429, last_response.text)

    def test_forgot_password_is_rate_limited(self):
        headers = self._rate_limit_headers("10.0.0.2")
        last_response = None
        for _ in range(5):
            last_response = self.client.post(
                "/api/v1/auth/forgot-password",
                headers=headers,
                json={"email": "ratelimit@example.com"},
            )
        self.assertIsNotNone(last_response)
        self.assertEqual(last_response.status_code, 429, last_response.text)

    def test_reset_password_is_rate_limited(self):
        headers = self._rate_limit_headers("10.0.0.3")
        last_response = None
        for _ in range(7):
            last_response = self.client.post(
                "/api/v1/auth/reset-password",
                headers=headers,
                json={
                    "email": "ratelimit@example.com",
                    "otp_code": "000000",
                    "new_password": "StrongPass1!",
                },
            )
        self.assertIsNotNone(last_response)
        self.assertEqual(last_response.status_code, 429, last_response.text)

    def test_refresh_is_rate_limited(self):
        headers = self._rate_limit_headers("10.0.0.4")
        last_response = None
        for _ in range(12):
            last_response = self.client.post(
                "/api/v1/auth/refresh",
                headers=headers,
            )
        self.assertIsNotNone(last_response)
        self.assertEqual(last_response.status_code, 429, last_response.text)


if __name__ == "__main__":
    unittest.main()
