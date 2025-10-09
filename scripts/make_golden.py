"""Generate or verify canonical golden benchmark artifacts.

Purpose:
  * Provide a deterministic baseline ("golden") for educational reproducibility
  * Detect drift (environment / dependency / algorithmic) via median log-speedup deltas

Usage:
  Generate (creates/overwrites bench/golden/golden.json & golden.md):
    PYTHONPATH=src python scripts/make_golden.py generate

  Verify (re-run and compare against existing golden):
    PYTHONPATH=src python scripts/make_golden.py verify

Exit codes:
  0 success (generate or verify within tolerance)
  1 verification drift beyond tolerance OR missing golden on verify

Golden JSON adds a provenance block capturing commit, python, packages, timestamps, seeds.

Scope Guardrails:
  - Fixed patterns: uniform, periodic (minimal representative set)
  - Fixed seed: 42
  - Rows: 500_000 (balance speed vs signal)
  - Iterations (n): 25
  - Alpha: 0.05
  - Tolerance: absolute delta in median_log_speedup > 0.05 triggers failure
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = REPO_ROOT / "src"
GOLDEN_DIR = REPO_ROOT / "bench" / "golden"
GOLDEN_JSON = GOLDEN_DIR / "golden.json"
GOLDEN_MD = GOLDEN_DIR / "golden.md"

# Ensure src is importable if code paths are imported (not needed for subprocess, but safe)
sys.path.insert(0, str(SRC_PATH))

PATTERNS = ["uniform", "periodic"]
ROWS = 500_000
N_ITER = 25
SEED = 42
ALPHA = 0.05
TOLERANCE_LOG_MEDIAN = 0.05  # ~5% in log domain (≈5% speedup relative for small deltas)


@dataclass
class Provenance:
    git_commit: str
    python_version: str
    platform: str
    numpy_version: str
    cudf_version: str | None
    timestamp_utc: str
    seed: int
    rows: int
    n_iter: int
    patterns: list[str]
    alpha: float


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()
    except Exception:  # pragma: no cover
        return "unknown"


def _pkg_version(name: str) -> str | None:
    try:
        mod = __import__(name)
        return getattr(mod, "__version__", "unknown")
    except Exception:  # pragma: no cover
        return None


def _run_benchmark(json_path: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "bench.benchmark",
        "--rows",
        str(ROWS),
        "--patterns",
        *PATTERNS,
        "--n",
        str(N_ITER),
        "--seed",
        str(SEED),
        "--alpha",
        str(ALPHA),
        "--json",
        str(json_path),
    ]
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(SRC_PATH))
    subprocess.check_call(cmd, cwd=REPO_ROOT, env=env)
    return json.loads(json_path.read_text())


def _build_provenance() -> Provenance:
    return Provenance(
        git_commit=_git_commit(),
        python_version=sys.version.replace("\n", " "),
        platform=sys.platform,
        numpy_version=_pkg_version("numpy") or "missing",
        cudf_version=_pkg_version("cudf"),
        timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        seed=SEED,
        rows=ROWS,
        n_iter=N_ITER,
        patterns=PATTERNS,
        alpha=ALPHA,
    )


def _golden_payload(raw: dict[str, Any], provenance: Provenance) -> dict[str, Any]:
    # Extract per-pattern medians for quick comparison
    medians = {p["pattern"]: p["median_log_speedup"] for p in raw.get("patterns", [])}
    return {
        "golden_spec": {
            "rows": ROWS,
            "n_iter": N_ITER,
            "patterns": PATTERNS,
            "seed": SEED,
            "alpha": ALPHA,
            "tolerance_log_median": TOLERANCE_LOG_MEDIAN,
        },
        "medians_log": medians,
        "raw": raw,
        "provenance": asdict(provenance),
    }


def _write_markdown(golden: dict[str, Any]) -> None:
    rows: list[str] = [
        "# Golden Benchmark Summary",
        "",
        "| Pattern | Median Speedup | Median Log | 95% CI (speedup) |",
        "|---|---|---|---|",
    ]
    for item in golden["raw"].get("patterns", []):
        ci = item["ci_speedup"]
        rows.append(
            f"| {item['pattern']} | {item['median_speedup']:.3f} | {item['median_log_speedup']:.4f} | "
            f"[{ci[0]:.3f}, {ci[1]:.3f}] |"
        )
    rows.append("")
    prov = golden["provenance"]
    rows.append("## Provenance")
    rows.append("```")
    rows.append(json.dumps(prov, indent=2))
    rows.append("```")
    GOLDEN_MD.write_text("\n".join(rows) + "\n", encoding="utf-8")


def generate() -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    tmp_json = GOLDEN_DIR / "_tmp_run.json"
    raw = _run_benchmark(tmp_json)
    prov = _build_provenance()
    golden = _golden_payload(raw, prov)
    GOLDEN_JSON.write_text(json.dumps(golden, indent=2) + "\n", encoding="utf-8")
    _write_markdown(golden)
    tmp_json.unlink(missing_ok=True)
    print(f"Golden artifacts written: {GOLDEN_JSON} | {GOLDEN_MD}")


def verify() -> int:
    if not GOLDEN_JSON.exists():
        print("Golden JSON missing. Run generate first.", file=sys.stderr)
        return 1
    prior = json.loads(GOLDEN_JSON.read_text())
    # Re-run
    tmp_json = GOLDEN_DIR / "_verify_run.json"
    new_raw = _run_benchmark(tmp_json)
    tmp_json.unlink(missing_ok=True)

    tolerance = prior["golden_spec"]["tolerance_log_median"]
    failures: list[str] = []
    new_medians = {p["pattern"]: p["median_log_speedup"] for p in new_raw.get("patterns", [])}
    for pat, old_val in prior["medians_log"].items():
        new_val = new_medians.get(pat)
        if new_val is None:
            failures.append(f"Pattern missing in new run: {pat}")
            continue
        delta = abs(new_val - old_val)
        if delta > tolerance:
            failures.append(f"Pattern {pat} median log-speedup drift {delta:.4f} > {tolerance}")

    if failures:
        print("Verification FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("Verification passed: drift within tolerance.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "action", choices=["generate", "verify"], help="Generate or verify golden artifacts"
    )
    args = ap.parse_args()
    if args.action == "generate":
        generate()
    else:
        code = verify()
        sys.exit(code)


if __name__ == "__main__":  # pragma: no cover
    main()
