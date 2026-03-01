from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.config import Settings
from app.models.contracts import (
    ActionExecuteRequest,
    ActionExecutionResult,
    ExecutionPreview,
    Money,
    Recommendation,
)
from app.services.storage import InMemoryStore


class ExecutionService:
    def __init__(self, settings: Settings, store: InMemoryStore) -> None:
        self.settings = settings
        self.store = store

    def preview(self, recommendation: Recommendation) -> ExecutionPreview:
        fees_cents = self._fee_for_action(recommendation.action_type)
        warnings = self._warnings_for_action(recommendation.action_type, recommendation.risk_level.value)
        impact = int(recommendation.expected_net_worth_delta.amount_cents * 0.35)
        return ExecutionPreview(
            action_id=recommendation.recommendation_id,
            projected_impact_12m=Money(amount_cents=impact),
            fees=Money(amount_cents=fees_cents),
            warnings=warnings,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=self.settings.preview_ttl_minutes),
        )

    def execute(self, request: ActionExecuteRequest) -> ActionExecutionResult:
        existing = self.store.get_execution_by_idempotency(request.idempotency_key)
        if existing:
            return existing

        if not request.confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Execution requires explicit confirmation",
            )

        preview = self.store.get_preview(request.preview_id)
        if preview is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="preview_id not found")
        if datetime.now(timezone.utc) > preview.expires_at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="preview has expired")
        if preview.action_id != request.action_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="action mismatch for preview")

        upstream_reference = self._generate_upstream_reference(request.action_id, request.idempotency_key)
        result = ActionExecutionResult(
            action_id=request.action_id,
            status="accepted",
            idempotency_key=request.idempotency_key,
            upstream_reference=upstream_reference,
        )
        self.store.save_execution(request.idempotency_key, result)
        return result

    def _fee_for_action(self, action_type: str) -> int:
        fee_table = {
            "increase_monthly_contribution": 0,
            "increase_emergency_fund": 0,
            "accelerate_debt_paydown": 99,
            "defer_home_purchase": 0,
        }
        return fee_table.get(action_type, 0)

    def _warnings_for_action(self, action_type: str, risk_level: str) -> list[str]:
        warnings = ["Confirm this action aligns with your near-term cash needs."]
        if action_type == "defer_home_purchase":
            warnings.append("Delaying purchase may increase exposure to housing price changes.")
        if risk_level == "moderate":
            warnings.append("This action may reduce short-term liquidity.")
        return warnings

    def _generate_upstream_reference(self, action_id: str, idempotency_key: str) -> str:
        digest = hashlib.sha256(f"{action_id}:{idempotency_key}".encode("utf-8")).hexdigest()
        return f"exec_{digest[:16]}"
