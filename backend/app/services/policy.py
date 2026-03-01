from __future__ import annotations

from app.models.contracts import AccountSnapshot, Recommendation, RiskLevel, ScenarioInput


class PolicyService:
    def __init__(self, version: str) -> None:
        self.version = version

    def evaluate(self, recommendation: Recommendation, scenario_input: ScenarioInput, snapshot: AccountSnapshot) -> tuple[bool, list[dict]]:
        checks: list[dict] = []
        emergency_months = 0.0
        if snapshot.monthly_spend_cents > 0:
            emergency_months = snapshot.emergency_fund_cents / snapshot.monthly_spend_cents
        checks.append(
            {
                "check": "minimum_emergency_fund",
                "result": "pass" if emergency_months >= 3 else "warn",
                "value": round(emergency_months, 2),
                "threshold": 3,
            }
        )

        horizon_is_short = scenario_input.horizon_months <= 24
        check_short_horizon = recommendation.action_type != "aggressive_allocation_shift" or not horizon_is_short
        checks.append(
            {
                "check": "short_horizon_allocation_limit",
                "result": "pass" if check_short_horizon else "fail",
                "horizon_months": scenario_input.horizon_months,
            }
        )

        high_risk = recommendation.risk_level == RiskLevel.high
        blocked = any(item["result"] == "fail" for item in checks) or (high_risk and emergency_months < 4)
        checks.append(
            {
                "check": "conservative_risk_posture",
                "result": "fail" if blocked else "pass",
                "risk_level": recommendation.risk_level.value,
            }
        )
        return (not blocked, checks)
