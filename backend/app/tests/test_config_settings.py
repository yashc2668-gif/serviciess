"""Tests for runtime settings parsing and precedence."""

from __future__ import annotations

import os
import tempfile
import textwrap
import unittest
from unittest.mock import patch

from app.core.config import Settings


class SettingsConfigTests(unittest.TestCase):
    def test_environment_variables_override_dotenv_values(self):
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as env_file:
            env_file.write(
                textwrap.dedent(
                    """
                    SECRET_KEY=dotenv-secret
                    ENVIRONMENT=production
                    DEBUG=False
                    ALLOWED_ORIGINS=["http://localhost:5173"]
                    """
                ).strip()
            )
            env_file_path = env_file.name

        try:
            with patch.dict(
                os.environ,
                {
                    "ALLOWED_ORIGINS": '["https://m2n-frontend.vercel.app"]',
                    "SECRET_KEY": "env-secret",
                    "ENVIRONMENT": "production",
                    "DEBUG": "False",
                },
                clear=False,
            ):
                settings = Settings(_env_file=env_file_path)

            self.assertEqual(
                settings.ALLOWED_ORIGINS,
                ["https://m2n-frontend.vercel.app"],
            )
        finally:
            os.unlink(env_file_path)

    def test_allowed_origins_normalize_wrapped_and_trailing_slash_values(self):
        settings = Settings(
            SECRET_KEY="dev-secret",
            ENVIRONMENT="production",
            DEBUG=False,
            ALLOWED_ORIGINS='["https://m2n-frontend.vercel.app/","https://m2n-frontend.vercel.app"]',
        )

        self.assertEqual(settings.ALLOWED_ORIGINS, ["https://m2n-frontend.vercel.app"])


if __name__ == "__main__":
    unittest.main()
