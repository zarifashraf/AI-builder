from __future__ import annotations

import hashlib

from app.models.contracts import AccountSnapshot


class AccountDataProvider:
    """
    Prototype adapter that deterministically generates account snapshots
    by user_id. Replace this with internal data-source adapters in production.
    """

    @staticmethod
    def get_account_snapshot(user_id: str) -> AccountSnapshot:
        hashed = int(hashlib.sha256(user_id.encode("utf-8")).hexdigest(), 16)
        assets = 2_500_000 + (hashed % 15_000_000)
        liabilities = 500_000 + (hashed % 2_000_000)
        income = 450_000 + (hashed % 350_000)
        spend = 250_000 + (hashed % 250_000)
        emergency = min(assets // 4, 2_000_000 + (hashed % 1_000_000))
        tfsa = 500_000 + (hashed % 1_500_000)
        rrsp = 900_000 + (hashed % 2_500_000)
        fhsa = 200_000 + (hashed % 600_000)
        risk = ["conservative", "balanced", "growth"][hashed % 3]
        province = ["ON", "QC", "BC", "AB"][hashed % 4]
        return AccountSnapshot(
            user_id=user_id,
            assets_cents=assets,
            liabilities_cents=liabilities,
            monthly_income_cents=income,
            monthly_spend_cents=spend,
            emergency_fund_cents=emergency,
            tfsa_room_cents=tfsa,
            rrsp_room_cents=rrsp,
            fhsa_room_cents=fhsa,
            risk_profile=risk,
            province=province,
        )
