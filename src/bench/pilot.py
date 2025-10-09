from __future__ import annotations

import numpy as np

Z_975 = 1.96
LOG_HALF_WIDTH_TARGET = 0.5 * np.log(1.10)


def _acf(values: np.ndarray, max_lag: int = 10) -> np.ndarray:
    x = values - values.mean()
    den = (x * x).sum()
    out = [1.0]
    for k in range(1, min(max_lag, len(values) - 1) + 1):
        num = (x[:-k] * x[k:]).sum()
        out.append(float(num / den) if den else 0.0)
    return np.array(out)


def _design_effect(acf: np.ndarray, cutoff: float = 0.1) -> float:
    acc = 0.0
    for r in acf[1:]:
        if abs(r) < cutoff:
            break
        acc += 2 * r
    return 1.0 + acc


def pilot_required_n(log_speedups: np.ndarray) -> dict[str, float]:
    n = len(log_speedups)
    if n < 4:
        raise ValueError("Pilot requires at least 4 observations")
    sigma = float(np.std(log_speedups, ddof=1))
    acf = _acf(log_speedups)
    deff = _design_effect(acf)
    n_req = ((Z_975 * sigma) / LOG_HALF_WIDTH_TARGET) ** 2 * deff
    return {
        "pilot_n": n,
        "sigma": sigma,
        "design_effect": deff,
        "acf": acf.tolist(),
        "n_required": float(np.ceil(n_req)),
    }
