from __future__ import annotations

from app.models.contracts import Money, Recommendation, RiskLevel, ScenarioInput, SimulationResult


class RecommendationService:
    def rank(self, scenario_input: ScenarioInput, simulation: SimulationResult) -> tuple[list[Recommendation], dict[str, float]]:
        delta = simulation.delta_final_net_worth_cents
        downside = simulation.downside_p10_delta_cents
        success_prob = simulation.goal_success_probability

        raw_candidates = [
            {
                "title": "Boost monthly contributions by 10%",
                "action_type": "increase_monthly_contribution",
                "risk_level": RiskLevel.low,
                "delta_multiplier": 0.6,
                "friction_penalty": 0.08,
                "liquidity_bonus": 0.2,
                "volatility_penalty": 0.05,
                "rationale": [
                    "Improves expected long-term wealth while maintaining conservative risk posture.",
                    "Fits well when discretionary cash flow exists in most months.",
                ],
                "sensitivity": ["monthly_spend_change_pct", "income_change_pct"],
            },
            {
                "title": "Increase emergency fund coverage to 6 months",
                "action_type": "increase_emergency_fund",
                "risk_level": RiskLevel.low,
                "delta_multiplier": 0.35,
                "friction_penalty": 0.04,
                "liquidity_bonus": 0.35,
                "volatility_penalty": 0.03,
                "rationale": [
                    "Reduces downside in job-loss and high-volatility scenarios.",
                    "Creates stronger resilience before larger commitments.",
                ],
                "sensitivity": ["monthly_spend_change_pct", "income_change_pct"],
            },
            {
                "title": "Accelerate debt repayment with targeted extra payments",
                "action_type": "accelerate_debt_paydown",
                "risk_level": RiskLevel.moderate,
                "delta_multiplier": 0.45,
                "friction_penalty": 0.06,
                "liquidity_bonus": 0.18,
                "volatility_penalty": 0.02,
                "rationale": [
                    "Lowers liability drag and improves net worth trajectory stability.",
                    "Can improve affordability metrics ahead of major life moves.",
                ],
                "sensitivity": ["debt_plan.extra_payment_monthly", "income_change_pct"],
            },
            {
                "title": "Delay home purchase by 6-12 months",
                "action_type": "defer_home_purchase",
                "risk_level": RiskLevel.moderate,
                "delta_multiplier": 0.5,
                "friction_penalty": 0.1,
                "liquidity_bonus": 0.3,
                "volatility_penalty": 0.02,
                "rationale": [
                    "Improves cash buffer and reduces downside probability from leverage.",
                    "Allows additional runway for down payment and closing-cost reserves.",
                ],
                "sensitivity": ["home_purchase.target_month", "monthly_spend_change_pct"],
            },
        ]

        if scenario_input.assumptions.home_purchase is None:
            raw_candidates = [c for c in raw_candidates if c["action_type"] != "defer_home_purchase"]

        ranked: list[Recommendation] = []
        for candidate in raw_candidates:
            expected_delta = int(delta * candidate["delta_multiplier"])
            downside_delta = int(downside * candidate["delta_multiplier"])
            score = self._score(
                success_prob=success_prob,
                liquidity_bonus=candidate["liquidity_bonus"],
                volatility_penalty=candidate["volatility_penalty"],
                friction_penalty=candidate["friction_penalty"],
            )
            ranked.append(
                Recommendation(
                    title=candidate["title"],
                    expected_net_worth_delta=Money(amount_cents=expected_delta),
                    downside_p10_delta=Money(amount_cents=downside_delta),
                    goal_success_probability=success_prob,
                    confidence=min(
                        0.98,
                        max(0.15, simulation.confidence * (1.0 - (candidate["friction_penalty"] * 0.35))),
                    ),
                    rationale=candidate["rationale"],
                    key_assumptions=self._key_assumptions(scenario_input),
                    sensitivity_top_factors=candidate["sensitivity"],
                    risk_level=candidate["risk_level"],
                    score=score,
                    action_type=candidate["action_type"],
                )
            )

        ranked.sort(key=lambda rec: rec.score, reverse=True)
        feature_contributions = {
            "goal_probability": round(success_prob * 0.45, 4),
            "liquidity_safety": 0.25,
            "volatility_penalty": -0.12,
            "user_friction_penalty": -0.08,
        }
        return ranked[:3], feature_contributions

    def _score(
        self,
        success_prob: float,
        liquidity_bonus: float,
        volatility_penalty: float,
        friction_penalty: float,
    ) -> float:
        score = (
            (success_prob * 0.45)
            + (liquidity_bonus * 0.25)
            + ((1.0 - volatility_penalty) * 0.2)
            + ((1.0 - friction_penalty) * 0.1)
        )
        return max(0.0, min(1.0, round(score, 4)))

    def _key_assumptions(self, scenario_input: ScenarioInput) -> list[str]:
        assumptions = scenario_input.assumptions
        statements = [
            f"horizon_months={scenario_input.horizon_months}",
            f"income_change_pct={assumptions.income_change_pct or 0.0}",
            f"monthly_spend_change_pct={assumptions.monthly_spend_change_pct or 0.0}",
        ]
        if assumptions.home_purchase:
            statements.append(f"home_purchase_target_month={assumptions.home_purchase.target_month}")
        if assumptions.debt_plan:
            statements.append(
                f"debt_extra_payment_monthly_cents={assumptions.debt_plan.extra_payment_monthly.amount_cents}"
            )
        return statements
