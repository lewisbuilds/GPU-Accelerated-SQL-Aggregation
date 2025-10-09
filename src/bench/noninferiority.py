from __future__ import annotations


def holm_step_down(pvals: dict[str, float], alpha: float = 0.05) -> dict[str, bool]:
    ordered = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(ordered)
    accepted: dict[str, bool] = {k: False for k in pvals}
    for i, (name, p) in enumerate(ordered):
        thresh = alpha / (m - i)
        if p <= thresh:
            accepted[name] = True
        else:
            break
    return accepted
