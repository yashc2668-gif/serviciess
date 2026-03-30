"""Authentication and foundation error-format tests."""

import unittest
from unittest.mock import patch

import app.db.base  # noqa: F401
import main
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import Base, get_db
from app.models.user import User


class AuthApiTests(unittest.TestCase):
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
                full_name="Auth Admin",
                email="auth-admin@example.com",
                hashed_password=hash_password("StrongPass123!"),
                role="admin",
                is_active=True,
            )
        )
        session.add(
            User(
                full_name="Disabled User",
                email="disabled@example.com",
                hashed_password=hash_password("StrongPass123!"),
                role="viewer",
                is_active=False,
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

    def test_register_login_and_me_flow_works_for_viewer(self):
        register_response = self.client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Viewer User",
                "email": "viewer@example.com",
                "password": "StrongPass123!",
                "role": "viewer",
            },
        )
        self.assertEqual(register_response.status_code, 201, register_response.text)
        self.assertEqual(register_response.json()["role"], "viewer")

        login_response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "viewer@example.com", "password": "StrongPass123!"},
        )
        self.assertEqual(login_response.status_code, 200, login_response.text)
        token = login_response.json()["access_token"]

        me_response = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me_response.status_code, 200, me_response.text)
        self.assertEqual(me_response.json()["email"], "viewer@example.com")

    def test_auth_endpoints_return_standard_error_format(self):
        unauthorized = self.client.get("/api/v1/auth/me")
        self.assertEqual(unauthorized.status_code, 401)
        self.assertFalse(unauthorized.json()["success"])
        self.assertEqual(unauthorized.json()["error"]["type"], "authentication_error")
        self.assertEqual(unauthorized.json()["path"], "/api/v1/auth/me")
        self.assertIn("X-Request-ID", unauthorized.headers)

        forbidden = self.client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Illegal Admin",
                "email": "illegal-admin@example.com",
                "password": "StrongPass123!",
                "role": "admin",
            },
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertFalse(forbidden.json()["success"])
        self.assertEqual(forbidden.json()["error"]["type"], "permission_denied")

        validation_error = self.client.post(
            "/api/v1/auth/login",
            json={"email": "bad-email", "password": "short"},
        )
        self.assertEqual(validation_error.status_code, 422)
        self.assertFalse(validation_error.json()["success"])
        self.assertEqual(validation_error.json()["error"]["type"], "validation_error")

    def test_disabled_user_is_blocked_from_login(self):
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "disabled@example.com", "password": "StrongPass123!"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["type"], "permission_denied")


if __name__ == "__main__":
    unittest.main()
