"""Extended auth security tests."""

import unittest
from datetime import timedelta
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
from app.models.user import User


class AuthSecurityApiTests(unittest.TestCase):
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
                full_name="Security Admin",
                email="security-admin@example.com",
                hashed_password=hash_password("StrongPass1!"),
                role="admin",
                is_active=True,
                password_changed_at=utc_now(),
            )
        )
        session.add(
            User(
                full_name="Security Viewer",
                email="security-viewer@example.com",
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

    def auth_headers(self, email: str, password: str = "StrongPass1!") -> dict[str, str]:
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def test_login_sets_refresh_and_csrf_cookies_and_refresh_rotates(self):
        login_response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "security-viewer@example.com", "password": "StrongPass1!"},
        )
        self.assertEqual(login_response.status_code, 200, login_response.text)
        login_payload = login_response.json()
        self.assertEqual(login_payload["expires_in"], settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        self.assertEqual(
            login_payload["refresh_expires_in"],
            settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        )

        initial_refresh_cookie = self.client.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
        initial_csrf_cookie = self.client.cookies.get(settings.CSRF_COOKIE_NAME)
        self.assertIsNotNone(initial_refresh_cookie)
        self.assertEqual(initial_csrf_cookie, login_payload["csrf_token"])

        csrf_headers = {settings.CSRF_HEADER_NAME: initial_csrf_cookie}
        refresh_response = self.client.post("/api/v1/auth/refresh", headers=csrf_headers)
        self.assertEqual(refresh_response.status_code, 200, refresh_response.text)
        refresh_payload = refresh_response.json()
        rotated_refresh_cookie = self.client.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
        rotated_csrf_cookie = self.client.cookies.get(settings.CSRF_COOKIE_NAME)
        self.assertNotEqual(rotated_refresh_cookie, initial_refresh_cookie)
        self.assertNotEqual(rotated_csrf_cookie, initial_csrf_cookie)
        self.assertEqual(rotated_csrf_cookie, refresh_payload["csrf_token"])

        self.client.cookies.set(settings.REFRESH_TOKEN_COOKIE_NAME, initial_refresh_cookie, path="/api/v1/auth")
        self.client.cookies.set(settings.CSRF_COOKIE_NAME, initial_csrf_cookie, path="/api/v1/auth")
        reused_response = self.client.post(
            "/api/v1/auth/refresh",
            headers={settings.CSRF_HEADER_NAME: initial_csrf_cookie},
        )
        self.assertEqual(reused_response.status_code, 401, reused_response.text)

    def test_refresh_requires_csrf_header(self):
        self.client.post(
            "/api/v1/auth/login",
            json={"email": "security-viewer@example.com", "password": "StrongPass1!"},
        )
        refresh_response = self.client.post("/api/v1/auth/refresh")
        self.assertEqual(refresh_response.status_code, 403, refresh_response.text)

    def test_password_reset_otp_flow_resets_password_and_revokes_old_session(self):
        login_response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "security-viewer@example.com", "password": "StrongPass1!"},
        )
        self.assertEqual(login_response.status_code, 200, login_response.text)
        stale_refresh_cookie = self.client.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
        stale_csrf_cookie = self.client.cookies.get(settings.CSRF_COOKIE_NAME)

        with patch("app.services.auth_service.send_password_reset_otp_email") as send_email:
            forgot_response = self.client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "security-viewer@example.com"},
            )
            self.assertEqual(forgot_response.status_code, 200, forgot_response.text)
            send_email.assert_called_once()
            otp_code = send_email.call_args.kwargs["otp_code"]

        reset_response = self.client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "security-viewer@example.com",
                "otp_code": otp_code,
                "new_password": "NewStrong2!",
            },
        )
        self.assertEqual(reset_response.status_code, 200, reset_response.text)

        old_password_login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "security-viewer@example.com", "password": "StrongPass1!"},
        )
        self.assertEqual(old_password_login.status_code, 401, old_password_login.text)

        new_password_login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "security-viewer@example.com", "password": "NewStrong2!"},
        )
        self.assertEqual(new_password_login.status_code, 200, new_password_login.text)

        self.client.cookies.set(settings.REFRESH_TOKEN_COOKIE_NAME, stale_refresh_cookie, path="/api/v1/auth")
        self.client.cookies.set(settings.CSRF_COOKIE_NAME, stale_csrf_cookie, path="/api/v1/auth")
        stale_refresh_response = self.client.post(
            "/api/v1/auth/refresh",
            headers={settings.CSRF_HEADER_NAME: stale_csrf_cookie},
        )
        self.assertEqual(stale_refresh_response.status_code, 401, stale_refresh_response.text)

    def test_forgot_password_is_generic_for_unknown_email(self):
        with patch("app.services.auth_service.send_password_reset_otp_email") as send_email:
            response = self.client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "unknown@example.com"},
            )
            self.assertEqual(response.status_code, 200, response.text)
            send_email.assert_not_called()
            self.assertIn("If an account exists", response.json()["message"])

    def test_account_lockout_after_five_failed_attempts_and_unlock_after_window(self):
        for attempt in range(4):
            response = self.client.post(
                "/api/v1/auth/login",
                json={"email": "security-viewer@example.com", "password": "WrongPass1!"},
            )
            self.assertEqual(
                response.status_code,
                401,
                msg=f"attempt {attempt + 1}: {response.text}",
            )

        locked_response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "security-viewer@example.com", "password": "WrongPass1!"},
        )
        self.assertEqual(locked_response.status_code, 423, locked_response.text)

        session = self.SessionLocal()
        user = session.query(User).filter(User.email == "security-viewer@example.com").first()
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.locked_until)
        unlock_time = user.locked_until + timedelta(seconds=1)
        session.close()

        with patch("app.services.auth_service.utc_now", return_value=unlock_time):
            unlocked_response = self.client.post(
                "/api/v1/auth/login",
                json={"email": "security-viewer@example.com", "password": "StrongPass1!"},
            )
        self.assertEqual(unlocked_response.status_code, 200, unlocked_response.text)

    def test_password_policy_is_enforced_for_register_and_admin_user_create(self):
        weak_register = self.client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Weak Viewer",
                "email": "weak-viewer@example.com",
                "password": "password1",
                "role": "viewer",
            },
        )
        self.assertEqual(weak_register.status_code, 400, weak_register.text)

        admin_headers = self.auth_headers("security-admin@example.com")
        weak_create = self.client.post(
            "/api/v1/users/",
            headers=admin_headers,
            json={
                "full_name": "Weak Managed User",
                "email": "weak-managed@example.com",
                "password": "weakpass1",
                "role": "viewer",
            },
        )
        self.assertEqual(weak_create.status_code, 400, weak_create.text)

    def test_rate_limiting_applies_to_login_and_global_requests(self):
        login_headers = {
            "X-RateLimit-Test": "1",
            "X-Forwarded-For": "198.51.100.24",
        }
        last_login_response = None
        for _ in range(6):
            last_login_response = self.client.post(
                "/api/v1/auth/login",
                headers=login_headers,
                json={"email": "nobody@example.com", "password": "StrongPass1!"},
            )
        self.assertIsNotNone(last_login_response)
        self.assertEqual(last_login_response.status_code, 429, last_login_response.text)

        global_headers = {
            "X-RateLimit-Test": "1",
            "X-Forwarded-For": "198.51.100.25",
        }
        last_global_response = None
        for _ in range(101):
            last_global_response = self.client.get("/api/v1/auth/me", headers=global_headers)
        self.assertIsNotNone(last_global_response)
        self.assertEqual(last_global_response.status_code, 429, last_global_response.text)

    def test_security_headers_are_attached_to_api_responses(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("Content-Security-Policy", response.headers)
        self.assertIn("Permissions-Policy", response.headers)


if __name__ == "__main__":
    unittest.main()
