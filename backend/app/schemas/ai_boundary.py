"""Schemas for AI usage boundary inspection."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, field_validator


class AIBoundaryPolicyRead(BaseModel):
    ai_enabled: bool
    ai_mode: str
    allow_state_changing_execution: bool
    require_human_review: bool
    require_backend_validation: bool
    allowed_operation_types: list[str]
    blocked_operation_types: list[str]
    required_guards: list[str]
    notes: list[str]


class AIBoundaryEvaluationRequest(BaseModel):
    operation_type: str
    affects_state: Optional[bool] = None

    @field_validator("operation_type")
    @classmethod
    def validate_operation_type(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("operation_type is required")
        return normalized


class AIBoundaryEvaluationResponse(BaseModel):
    operation_type: str
    normalized_operation_type: str
    affects_state: bool
    allowed: bool
    reasons: list[str]
    required_guards: list[str]
