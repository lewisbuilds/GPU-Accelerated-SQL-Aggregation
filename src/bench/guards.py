from __future__ import annotations

import math

INTERACTION_DTYPE = "float64"
INTERACTION_NULL_RATE = 0.5
CLUSTER_AUTOCORR_THRESHOLD = 0.6
PERIOD_MAX = 8


def evaluate_distribution_guard(
    value_dtype: str, value_null_rate: float, features: dict[str, float]
) -> str | None:
    if value_dtype != INTERACTION_DTYPE or value_null_rate < INTERACTION_NULL_RATE:
        return None
    lag1 = features.get("lag1", 0.0)
    period = features.get("period", math.nan)
    periodic_flag = not math.isnan(period) and period <= PERIOD_MAX
    if lag1 >= CLUSTER_AUTOCORR_THRESHOLD or periodic_flag:
        return (
            "Out-of-scope: float64 × high null-rate × clustered/periodic mask "
            f"(lag1={lag1:.2f}, period={period if not math.isnan(period) else 'NA'})"
        )
    return None


def enforce_guard_or_raise(dtype: str, null_rate: float, features: dict[str, float]) -> None:
    reason = evaluate_distribution_guard(dtype, null_rate, features)
    if reason:
        raise AssertionError(reason)
