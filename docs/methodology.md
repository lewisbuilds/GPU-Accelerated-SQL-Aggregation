# Statistical Methodology

## Effect Metric
Log speedup = ln(GPU_time / CPU_time). SESOI set to ln(0.90) (~ -10% threshold) for non-inferiority framing.

## Resampling & Inference
- Moving/block bootstrap accounts for short-period / clustered null patterns.
- maxT simultaneous inference produces lower bounds controlling family-wise error at α.

## Drift Rules
`golden-bench verify` fails if:
- |Δ median log speedup| > 0.10
- Lower bound regression > 0.05 log units

## Rationale
- Log stabilizes variance of multiplicative ratios.
- Simultaneous bounds avoid false positives across multiple patterns.

## SESOI Decisions
`--report` adds a `report` block. Threshold: ln(0.90) (≈ -0.1053). If a pattern's simultaneous lower log bound ≥ threshold → `non_inferior`, else `undetermined`.
