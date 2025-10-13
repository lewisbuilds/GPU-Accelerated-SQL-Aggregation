"""Reporting utilities for benchmark statistical interpretation.

Generates SESOI (smallest effect size of interest) decisions using a
log-speedup threshold (default ln(0.90) ≈ -0.1053605). If the simultaneous
lower log bound is above the SESOI threshold the pattern is classified as
"non_inferior"; otherwise "undetermined". (We do not assert superiority in
this educational context.)
"""

from __future__ import annotations

import math
from typing import Any

SESOI_LOG = math.log(0.90)  # negative value (~ -0.1053)


def sesoi_decisions(result: dict[str, Any]) -> dict[str, str]:
    """Return mapping pattern -> decision based on simultaneous lower log bounds.

    If simultaneous bounds absent (single pattern) fallback to individual CI lower.
    Decisions:
      - non_inferior: lower bound >= SESOI threshold
      - undetermined: otherwise
    """
    decisions: dict[str, str] = {}
    sim = result.get("simultaneous_lower_log")
    by_pattern = {p["pattern"]: p for p in result.get("patterns", [])}
    for pat in by_pattern:
        if sim:
            lb = sim[pat]
        else:
            # fall back to pattern-specific 95% CI lower (conservative for decision)
            lb = by_pattern[pat]["ci_log"][0]
        decisions[pat] = "non_inferior" if lb >= SESOI_LOG else "undetermined"
    return decisions


def enrich_with_report(result: dict[str, Any]) -> None:
    """Mutates result dict adding a 'report' sub-structure with decisions & parameters."""
    result["report"] = {
        "sesoi_log": SESOI_LOG,
        "decisions": sesoi_decisions(result),
    }
