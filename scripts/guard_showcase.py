"""Generate guard violation showcase examples.

Produces a markdown table comparing an in-scope pattern vs two out-of-scope
cases (high null-rate + clustered, high null-rate + periodic) and captures the
guard messages plus feature metrics.

Run:
  poetry run python scripts/guard_showcase.py --rows 100000 --null-rate 0.6
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TypedDict
from typing import cast

import numpy as np  # type: ignore[import-not-found]  # pylint: disable=import-error

from bench import features  # type: ignore[attr-defined]
from bench import guards  # type: ignore[attr-defined]
from bench import mask_patterns  # type: ignore[attr-defined]


class FeatureRow(TypedDict, total=False):
    p_null: float
    lag1: float
    period: float
    entropy8: float


def build_mask(pattern: str, rows: int, null_rate: float, rng: np.random.Generator) -> np.ndarray:
    gen = mask_patterns.PATTERNS[pattern]
    if pattern == "uniform":
        return gen(rows, null_rate, rng)
    if pattern == "clustered":
        return gen(rows, null_rate, rng, mean_run=48)
    if pattern == "periodic":
        return gen(rows, period=2)
    return gen(rows)


def summarize(mask: np.ndarray) -> FeatureRow:
    f = features.compute_features(mask)
    return cast(FeatureRow, f)


def main():  # pragma: no cover
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=200_000)
    ap.add_argument("--null-rate", type=float, default=0.6, help="High null rate to trigger guard")
    ap.add_argument("--out", type=Path, default=Path("docs/guard_showcase.md"))
    ap.add_argument("--seed", type=int, default=1234)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    patterns = ["uniform", "clustered", "periodic"]
    rows = []
    for pat in patterns:
        m = build_mask(pat, args.rows, args.null_rate, rng)
        feat = summarize(m[: min(args.rows, 50_000)])
        reason = guards.evaluate_distribution_guard("float64", feat["p_null"], feat)
        rows.append({"pattern": pat, "features": feat, "guard": reason or "(in-scope)"})

    # Build markdown table (column order documented in header below)
    lines = [
        "# Guard Violation Showcase",
        "",
        "| Pattern | Null p | Lag1 | Period | Entropy8 | Guard |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        f = cast(FeatureRow, r["features"])  # explicit cast for mypy
        lines.append(
            f"| {r['pattern']} | {f['p_null']:.3f} | {f['lag1']:.2f} | "
            f"{f['period']:.1f} | {f['entropy8']:.3f} | {r['guard']} |"
        )
    args.out.write_text("\n".join(lines) + "\n")
    print(f"Wrote {args.out}")


if __name__ == "__main__":  # pragma: no cover
    main()
