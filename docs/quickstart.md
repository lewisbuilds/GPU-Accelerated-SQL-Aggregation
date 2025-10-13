# Quickstart

Get running fast.

## Install
```powershell
poetry install --no-root
```
GPU extras:
```powershell
poetry install --with gpu --no-root
```

## Simple Aggregation (CPU fallback if no GPU)
```powershell
poetry run python -c "from cudf_fdw.engine import AggregationEngine;print(AggregationEngine().aggregate('data/sample.csv',['value'],['sum','avg']))"
```

## Golden Benchmarks
```powershell
poetry run golden-bench generate
poetry run golden-bench verify
```

If verify reports drift, review changes before regenerating.

## Dev Container
Open in VS Code and use the Dev Containers extension. The `.devcontainer/devcontainer.json` sets up Python 3.11 and installs dependencies automatically (GPU access if host supports `--gpus=all`).

Quick environment check:
```powershell
poetry run python scripts/dev_check.py
```

## Next
See `architecture.md`, `methodology.md`, and `CONTRIBUTING_PERF.md` for deeper and contribution details.
