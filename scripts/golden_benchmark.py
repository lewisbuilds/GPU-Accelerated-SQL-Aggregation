"""Generate and verify canonical golden benchmark artifacts.

Usage (after poetry install):
  poetry run golden-bench generate   # writes bench/golden/golden.json / .md
  poetry run golden-bench verify     # compares current run to stored golden

Drift Policy:
  Fails verify if absolute difference in median log-speedup for any pattern
  exceeds DRIFT_LOG_THRESHOLD (default 0.10 log units ≈ 10.5% speed factor) OR
  if simultaneous lower bound drops below stored by more than ALLOW_LOWER_DELTA.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# (numpy used indirectly via benchmark package; direct import removed)

# Ensure src is on path when executing script directly via entry point pre-install
if str(Path(__file__).resolve().parent.parent / "src") not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


GOLDEN_DIR = Path("bench/golden")
GOLDEN_JSON = GOLDEN_DIR / "golden.json"
GOLDEN_MD = GOLDEN_DIR / "golden.md"

PATTERNS = ["uniform", "periodic"]  # minimal authoritative set
ROWS = 500_000
N = 25
SEED = 42
ALPHA = 0.05
DRIFT_LOG_THRESHOLD = 0.10  # log units (~10% multiplicative)
ALLOW_LOWER_DELTA = 0.05  # allow lower bound to fall by at most 0.05 log units


def _run_benchmark() -> dict[str, Any]:
    """Invoke benchmark.main programmatically with controlled args."""
    # Emulate argparse path by constructing args list and calling main in subprocess for isolation.
    cmd = [
        sys.executable,
        "-m",
        "bench.benchmark",
        "--rows",
        str(ROWS),
        "--patterns",
        *PATTERNS,
        "--n",
        str(N),
        "--alpha",
        str(ALPHA),
        "--json",
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def _provenance(block: dict[str, Any]) -> dict[str, Any]:
    python_ver = sys.version.split()[0]
    try:
        import importlib.metadata as _md  # Python 3.11+

        md: Any | None = _md
    except Exception:  # pragma: no cover  # pylint: disable=broad-except
        # Broad except is intentional: on some stripped-down runtimes metadata import can fail
        md = None
    pkgs = {}
    for name in ["numpy", "pyarrow"]:
        try:
            pkgs[name] = md.version(name) if md else "?"
        except Exception:  # pylint: disable=broad-except
            # Package may be absent in minimal environment; record unknown
            pkgs[name] = "?"
    cudf_ver = "none"
    try:  # pragma: no cover
        import cudf  # type: ignore  # pylint: disable=import-error

        cudf_ver = getattr(cudf, "__version__", "?")  # type: ignore[attr-defined]
    except Exception:  # pylint: disable=broad-except
        # cudf not installed (CPU-only environment) or version attr missing
        pass
    git_sha = _git_commit()
    payload = {
        "timestamp_utc": dt.datetime.utcnow().isoformat() + "Z",
        "python": python_ver,
        "git_sha": git_sha,
        "packages": pkgs,
        "cudf": cudf_ver,
        "config": {
            "rows": ROWS,
            "n": N,
            "patterns": PATTERNS,
            "alpha": ALPHA,
        },
    }
    # Integrate hash of primary speed samples if present
    pattern_entries = block.get("patterns", [])
    concat = ";".join(
        f"{p['pattern']}:{p['median_log_speedup']}:{p['ci_log'][0]}:{p['ci_log'][1]}"
        for p in pattern_entries
    )
    payload["integrity_hash"] = hashlib.sha256(concat.encode()).hexdigest()
    return payload


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # pragma: no cover
        return "unknown"


def generate():
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    result = _run_benchmark()
    result["provenance"] = _provenance(result)
    with open(GOLDEN_JSON, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    _write_markdown(result)
    print(f"Golden benchmark written: {GOLDEN_JSON}")


def _write_markdown(result: dict[str, Any]):
    lines = [
        "# Golden Benchmark Summary",
        "",
        f"Patterns: {', '.join(PATTERNS)}  ",
        f"Rows: {ROWS}  Iterations: {N}  Alpha: {ALPHA}",
        "",
        "| Pattern | Median Speedup | 95% CI | Median Log |",
        "|---|---|---|---|",
    ]
    for p in result["patterns"]:
        ci = p["ci_speedup"]
        lines.append(
            f"| {p['pattern']} | {p['median_speedup']:.3f} | [{ci[0]:.3f}, {ci[1]:.3f}] | {p['median_log_speedup']:.3f} |"
        )
    prov = result.get("provenance", {})
    lines += [
        "",
        "## Provenance",
        "```json",
        json.dumps(prov, indent=2),
        "```",
    ]
    with open(GOLDEN_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def verify():
    if not GOLDEN_JSON.exists():
        print("Golden JSON not found. Run generate first.", file=sys.stderr)
        sys.exit(2)
    baseline = json.loads(GOLDEN_JSON.read_text())
    current = _run_benchmark()
    failures: list[str] = []
    # Compare medians
    base_map = {p["pattern"]: p for p in baseline.get("patterns", [])}
    cur_map = {p["pattern"]: p for p in current.get("patterns", [])}
    for pat in PATTERNS:
        b = base_map[pat]
        c = cur_map[pat]
        delta = abs(c["median_log_speedup"] - b["median_log_speedup"])
        if delta > DRIFT_LOG_THRESHOLD:
            failures.append(f"Median log-speedup drift {pat}: {delta:.3f} > {DRIFT_LOG_THRESHOLD}")
    # If simultaneous lower bounds exist compare
    if "simultaneous_lower_log" in baseline and "simultaneous_lower_log" in current:
        for pat, base_lb in baseline["simultaneous_lower_log"].items():
            cur_lb = current["simultaneous_lower_log"][pat]
            if base_lb - cur_lb > ALLOW_LOWER_DELTA:
                failures.append(
                    f"Lower bound regression {pat}: drop {(base_lb - cur_lb):.3f} > {ALLOW_LOWER_DELTA}"
                )
    if failures:
        print("DRIFT DETECTED:")
        for f in failures:
            print(f" - {f}")
        sys.exit(1)
    print("Golden benchmark verified: no significant drift.")


def main():  # pragma: no cover
    if len(sys.argv) < 2 or sys.argv[1] not in {"generate", "verify"}:
        print("Usage: golden-bench [generate|verify]", file=sys.stderr)
        sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "generate":
        generate()
    else:
        verify()


if __name__ == "__main__":  # pragma: no cover
    main()
