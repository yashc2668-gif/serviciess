"""Admin-only AI usage boundary inspection endpoints."""

from fastapi import APIRouter, Depends

from app.core.permissions import require_roles
from app.models.user import User
from app.schemas.ai_boundary import (
    AIBoundaryEvaluationRequest,
    AIBoundaryEvaluationResponse,
    AIBoundaryPolicyRead,
)
from app.services.ai_boundary_service import evaluate_ai_operation, get_ai_boundary_policy

router = APIRouter(prefix="/ai-boundary", tags=["AI Boundary"])


@router.get("", response_model=AIBoundaryPolicyRead)
def read_ai_boundary_policy(
    _: User = Depends(require_roles("admin")),
) -> AIBoundaryPolicyRead:
    return get_ai_boundary_policy()


@router.post("/evaluate", response_model=AIBoundaryEvaluationResponse)
def evaluate_ai_boundary_request(
    payload: AIBoundaryEvaluationRequest,
    _: User = Depends(require_roles("admin")),
) -> AIBoundaryEvaluationResponse:
    return evaluate_ai_operation(payload)
