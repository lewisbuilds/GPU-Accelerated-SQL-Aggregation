# Architecture

## Components
- Engine (`cudf_fdw.engine.AggregationEngine`) handles aggregation with cuDF or pandas fallback.
- FDW (`cudf_fdw.fdw`) validates and pushes aggregation into engine under PostgreSQL via Multicorn.
- Benchmark suite (`src/bench`) synthesizes patterns, times GPU vs CPU, bootstraps log speedups, computes simultaneous (maxT) lower bounds, applies guards.

## Flow
```
patterns -> synthetic column -> engine timings -> log speedups -> bootstrap + maxT -> golden / report
```

## Security
- Path normalization & extension (*.csv) whitelist.
- Aggregate whitelist (SUM AVG MIN MAX COUNT).
- Column existence checking.

## Extensibility
- New pattern: add generator in `mask_patterns.py` and register.
- New feature metric: add function in `features.py` consumed by benchmark.
- New statistical artifact: extend `bootstrap.py` and integrate in `benchmark.py`.
