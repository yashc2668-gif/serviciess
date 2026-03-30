"""AI usage boundary helpers."""

from __future__ import annotations

from app.core.config import settings
from app.schemas.ai_boundary import (
    AIBoundaryEvaluationRequest,
    AIBoundaryEvaluationResponse,
    AIBoundaryPolicyRead,
)

READ_ONLY_OPERATION_TYPES = (
    "summarize",
    "suggest",
    "classify",
    "extract",
    "explain",
)

STATE_CHANGING_OPERATION_TYPES = (
    "create",
    "update",
    "delete",
    "submit",
    "approve",
    "reject",
    "issue",
    "receive",
    "adjust",
    "allocate",
    "release",
    "mark_paid",
)

REQUIRED_GUARDS = (
    "Human review is required before any AI suggestion is used operationally.",
    "Backend service rules, DB constraints, and workflow checks remain authoritative.",
    "AI outputs must not bypass tests, approvals, or audit requirements.",
)


def normalize_operation_type(operation_type: str) -> str:
    return operation_type.strip().lower().replace(" ", "_")


def get_ai_boundary_policy() -> AIBoundaryPolicyRead:
    return AIBoundaryPolicyRead(
        ai_enabled=settings.AI_ENABLED,
        ai_mode=settings.AI_MODE,
        allow_state_changing_execution=False,
        require_human_review=settings.AI_REQUIRE_HUMAN_REVIEW,
        require_backend_validation=settings.AI_REQUIRE_BACKEND_VALIDATION,
        allowed_operation_types=list(READ_ONLY_OPERATION_TYPES),
        blocked_operation_types=list(STATE_CHANGING_OPERATION_TYPES),
        required_guards=list(REQUIRED_GUARDS),
        notes=[
            "AI is disabled by default in this backend.",
            "When enabled, AI remains suggestion-only and cannot execute state-changing backend actions.",
            "Final decisions must still pass backend rules, DB constraints, and tests.",
        ],
    )


def evaluate_ai_operation(
    payload: AIBoundaryEvaluationRequest,
) -> AIBoundaryEvaluationResponse:
    normalized_operation_type = normalize_operation_type(payload.operation_type)
    affects_state = (
        payload.affects_state
        if payload.affects_state is not None
        else normalized_operation_type in STATE_CHANGING_OPERATION_TYPES
    )

    reasons: list[str] = []
    if not settings.AI_ENABLED:
        reasons.append("AI features are disabled in this environment.")
    if affects_state:
        reasons.append(
            "AI can suggest actions but cannot execute state-changing backend operations."
        )
    if (
        not affects_state
        and settings.AI_ENABLED
        and normalized_operation_type not in READ_ONLY_OPERATION_TYPES
    ):
        reasons.append(
            "Only explicitly whitelisted read-only AI operation types are allowed."
        )

    return AIBoundaryEvaluationResponse(
        operation_type=payload.operation_type,
        normalized_operation_type=normalized_operation_type,
        affects_state=affects_state,
        allowed=not reasons,
        reasons=reasons,
        required_guards=list(REQUIRED_GUARDS),
    )
