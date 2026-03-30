"""Tests for AI usage boundary settings and service behavior."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app.core.config import Settings, settings
from app.schemas.ai_boundary import AIBoundaryEvaluationRequest
from app.services.ai_boundary_service import evaluate_ai_operation, get_ai_boundary_policy


class AIUsageBoundaryTests(unittest.TestCase):
    def test_settings_reject_enabled_ai_without_suggestion_only_mode(self):
        with self.assertRaises(ValidationError):
            Settings(
                SECRET_KEY="dev-secret",
                ENVIRONMENT="development",
                AI_ENABLED=True,
                AI_MODE="disabled",
            )

    def test_settings_reject_disabled_ai_with_non_disabled_mode(self):
        with self.assertRaises(ValidationError):
            Settings(
                SECRET_KEY="dev-secret",
                ENVIRONMENT="development",
                AI_ENABLED=False,
                AI_MODE="suggestion_only",
            )

    def test_settings_require_human_review_and_backend_validation_when_ai_enabled(self):
        with self.assertRaises(ValidationError):
            Settings(
                SECRET_KEY="dev-secret",
                ENVIRONMENT="development",
                AI_ENABLED=True,
                AI_MODE="suggestion_only",
                AI_REQUIRE_HUMAN_REVIEW=False,
            )

        with self.assertRaises(ValidationError):
            Settings(
                SECRET_KEY="dev-secret",
                ENVIRONMENT="development",
                AI_ENABLED=True,
                AI_MODE="suggestion_only",
                AI_REQUIRE_BACKEND_VALIDATION=False,
            )

    def test_policy_snapshot_defaults_to_disabled_and_blocks_state_changes(self):
        policy = get_ai_boundary_policy()
        self.assertFalse(policy.ai_enabled)
        self.assertEqual(policy.ai_mode, "disabled")
        self.assertFalse(policy.allow_state_changing_execution)
        self.assertIn("approve", policy.blocked_operation_types)

    def test_evaluation_blocks_write_actions_even_if_ai_is_enabled(self):
        with patch.object(settings, "AI_ENABLED", True), patch.object(
            settings, "AI_MODE", "suggestion_only"
        ):
            decision = evaluate_ai_operation(
                AIBoundaryEvaluationRequest(operation_type="approve", affects_state=True)
            )

        self.assertFalse(decision.allowed)
        self.assertTrue(
            any(
                "cannot execute state-changing backend operations" in reason
                for reason in decision.reasons
            )
        )

    def test_evaluation_allows_whitelisted_read_only_operation_only_when_enabled(self):
        disabled_decision = evaluate_ai_operation(
            AIBoundaryEvaluationRequest(operation_type="summarize", affects_state=False)
        )
        self.assertFalse(disabled_decision.allowed)

        with patch.object(settings, "AI_ENABLED", True), patch.object(
            settings, "AI_MODE", "suggestion_only"
        ):
            enabled_decision = evaluate_ai_operation(
                AIBoundaryEvaluationRequest(operation_type="summarize", affects_state=False)
            )
            blocked_unknown_decision = evaluate_ai_operation(
                AIBoundaryEvaluationRequest(operation_type="forecast", affects_state=False)
            )

        self.assertTrue(enabled_decision.allowed)
        self.assertFalse(blocked_unknown_decision.allowed)


if __name__ == "__main__":
    unittest.main()
