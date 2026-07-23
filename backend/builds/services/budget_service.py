from datetime import date
from builds.config import BUILDS_DAILY_BUDGET_USD, BUILDS_PER_BUILD_CAP_USD
from builds.repositories import build_repository as repo


async def get_daily_budget() -> dict:
    spent, committed = await repo.get_today_spent_and_committed()
    cap = BUILDS_DAILY_BUDGET_USD
    remaining = max(0.0, cap - spent - committed)
    return {
        "spent_usd": round(spent, 4),
        "committed_usd": round(committed, 4),
        "cap_usd": cap,
        "remaining_usd": round(remaining, 4),
        "per_build_cap_usd": BUILDS_PER_BUILD_CAP_USD,
        "date": date.today().isoformat(),
    }
