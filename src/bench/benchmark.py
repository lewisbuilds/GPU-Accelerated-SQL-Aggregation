from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
from cudf_fdw.engine import AggregationEngine

from . import bootstrap
from . import features
from . import gpu_timing
from . import guards
from . import mask_patterns
from . import pilot
from . import report


def _build_dataframe(n: int, mask: np.ndarray, backend: str):
    rng = np.random.default_rng(123)
    keys = rng.integers(0, 10_000, size=n, dtype=np.int32)
    vals = rng.standard_normal(size=n).astype("float64") * 100.0
    vals[mask] = np.nan
    if backend == "cudf":  # pragma: no cover
        try:  # lazy optional dependency
            import cudf  # type: ignore  # noqa: F401

            return cudf.DataFrame({"key": keys, "val": vals})
        except Exception:  # pragma: no cover
            backend = "pandas"
    import pandas as pd  # type: ignore  # pylint: disable=import-outside-toplevel

    return pd.DataFrame({"key": keys, "val": vals})


def _aggregation_workload(df, backend: str):
    engine = AggregationEngine(df, backend)
    return engine.aggregate(["key"], {"val": "SUM", "val_count": "COUNT"})


def _time_operator(df_builder: Callable[[], Any], backend: str, n_iter: int, warmups: int = 3):
    timings = []
    host_overheads = []
    rows = 0
    for _ in range(warmups):
        _aggregation_workload(df_builder(), backend)
    for _ in range(n_iter):
        df = df_builder()
        if backend == "cudf" and gpu_timing.gpu_available():  # pragma: no cover
            # segmented: build df (host) already done; kernel timing only
            t_host_start = time.perf_counter()
            with gpu_timing.cuda_timer() as elapsed:
                _aggregation_workload(df, backend)
                kernel = elapsed()
            total = time.perf_counter() - t_host_start
            timings.append(kernel)
            host_overheads.append(max(total - kernel, 0.0))
        else:
            start = time.perf_counter()
            _aggregation_workload(df, backend)
            total = time.perf_counter() - start
            timings.append(total)
            host_overheads.append(0.0)
        rows = len(df)
    return rows, np.array(timings), np.array(host_overheads)


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=1_000_000)
    parser.add_argument("--pattern", choices=list(mask_patterns.PATTERNS.keys()), default="uniform")
    parser.add_argument(
        "--patterns",
        nargs="*",
        choices=list(mask_patterns.PATTERNS.keys()),
        help="Optional list of patterns for simultaneous inference (overrides --pattern)",
    )
    parser.add_argument("--null-rate", type=float, default=0.5)
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--n", type=int)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--json", help="Write JSON results to file (default dir: bench_outputs)")
    parser.add_argument(
        "--markdown", help="Write markdown summary table to file (default dir: bench_outputs)"
    )
    parser.add_argument("--alpha", type=float, default=0.05, help="Family-wise alpha")
    parser.add_argument("--report", action="store_true", help="Include interpretation block")
    return parser.parse_args(list(argv) if argv is not None else None)


def _validate_args(a: argparse.Namespace) -> None:
    if a.rows <= 0 or a.rows > 50_000_000:
        raise SystemExit("--rows must be between 1 and 50,000,000")
    if not 0.0 <= a.null_rate <= 0.99:
        raise SystemExit("--null-rate must be in [0,0.99]")
    if a.alpha <= 0 or a.alpha >= 0.5:
        raise SystemExit("--alpha should be in (0,0.5)")
    if a.n is not None and (a.n <= 1 or a.n > 10_000):
        raise SystemExit("--n must be >1 and <=10000 if provided")
    if a.patterns and len(a.patterns) > 16:
        raise SystemExit("Too many patterns supplied (max 16)")


MaskGen = Callable[[], np.ndarray]


def _pattern_generators(
    args: argparse.Namespace, rng: np.random.Generator
) -> list[tuple[str, MaskGen]]:
    names = list(dict.fromkeys(args.patterns)) if args.patterns else [args.pattern]
    gens: list[tuple[str, MaskGen]] = []
    for name in names:
        fn = mask_patterns.PATTERNS[name]
        if name == "uniform":

            def gen_uniform(_fn=fn) -> np.ndarray:  # type: ignore[valid-type]
                return _fn(args.rows, args.null_rate, rng)

            gens.append((name, gen_uniform))
        elif name == "clustered":

            def gen_clustered(_fn=fn) -> np.ndarray:  # type: ignore[valid-type]
                return _fn(args.rows, args.null_rate, rng, mean_run=32)

            gens.append((name, gen_clustered))
        elif name == "periodic":

            def gen_periodic(_fn=fn) -> np.ndarray:  # type: ignore[valid-type]
                return _fn(args.rows, period=2)

            gens.append((name, gen_periodic))
        else:

            def gen_other(_fn=fn) -> np.ndarray:  # type: ignore[valid-type]
                return _fn(args.rows)

            gens.append((name, gen_other))
    return gens


def _pilot_run(
    gen: MaskGen,
    args: argparse.Namespace,
    gpu_backend: str | None,
    cpu_backend: str,
    feat: dict[str, Any],
) -> dict[str, Any]:
    def build_gpu(mask_gen: Callable[[], np.ndarray]):  # local helpers
        return _build_dataframe(args.rows, mask_gen(), gpu_backend)  # type: ignore[arg-type]

    def build_cpu(mask_gen: Callable[[], np.ndarray]):
        return _build_dataframe(args.rows, mask_gen(), cpu_backend)

    m = 12
    builder_gpu = (lambda: build_gpu(gen)) if gpu_backend else (lambda: build_cpu(gen))
    rows, gpu_times, _gpu_host = _time_operator(builder_gpu, gpu_backend or cpu_backend, m)
    rows2, cpu_times, _cpu_host = _time_operator(lambda: build_cpu(gen), cpu_backend, m)
    assert rows == rows2
    gpu_thr = rows / gpu_times
    cpu_thr = rows / cpu_times
    log_speedup = np.log(gpu_thr) - np.log(cpu_thr)
    pstats = pilot.pilot_required_n(log_speedup)
    return {"pilot": pstats, "features": feat}


def _measure_patterns(
    patterns: list[tuple[str, MaskGen]],
    args: argparse.Namespace,
    gpu_backend: str | None,
    cpu_backend: str,
    feat: dict[str, Any],
) -> dict[str, Any]:
    final_n = args.n or 20
    results: dict[str, Any] = {
        "n": final_n,
        "patterns": [],
        "features": feat,
        "alpha": args.alpha,
        "gpu_available": bool(gpu_backend),
    }
    pattern_diffs: dict[str, np.ndarray] = {}
    rows_ref: int | None = None

    def build(mask_gen: MaskGen, backend: str):
        return _build_dataframe(args.rows, mask_gen(), backend)

    def make_builder(mask_gen: MaskGen, backend: str) -> Callable[[], Any]:
        def _builder() -> Any:
            return build(mask_gen, backend)

        return _builder

    for name, mask_gen in patterns:
        if gpu_backend:
            rows, gpu_times, gpu_host = _time_operator(
                make_builder(mask_gen, gpu_backend), gpu_backend, final_n
            )
        else:
            rows, gpu_times, gpu_host = _time_operator(
                make_builder(mask_gen, cpu_backend), cpu_backend, final_n
            )
        rows2, cpu_times, cpu_host = _time_operator(
            make_builder(mask_gen, cpu_backend), cpu_backend, final_n
        )
        assert rows == rows2
        rows_ref = rows if rows_ref is None else rows_ref
        assert rows_ref == rows, "Row count mismatch across patterns"
        gpu_thr = rows / gpu_times
        cpu_thr = rows / cpu_times
        log_speed = np.log(gpu_thr) - np.log(cpu_thr)
        block = int(round(final_n ** (1 / 3)))
        rng2 = np.random.default_rng(args.seed + 100 + hash(name) % 10_000)
        boot = bootstrap.paired_bootstrap(log_speed, reps=600, rng=rng2, block=block)
        lo, hi = np.quantile(boot, [0.025, 0.975])
        pattern_diffs[name] = log_speed
        results["patterns"].append(
            {
                "pattern": name,
                "median_log_speedup": float(np.median(log_speed)),
                "median_speedup": float(np.exp(np.median(log_speed))),
                "ci_log": [float(lo), float(hi)],
                "ci_speedup": [float(np.exp(lo)), float(np.exp(hi))],
                "gpu_host_overhead_mean": float(np.mean(gpu_host)),
                "gpu_host_overhead_p95": float(np.quantile(gpu_host, 0.95)),
                "cpu_host_overhead_mean": float(np.mean(cpu_host)),
            }
        )

    if len(patterns) > 1 and pattern_diffs:
        block = int(round(final_n ** (1 / 3)))
        rng_mt = np.random.default_rng(args.seed + 999)
        lowers = bootstrap.maxT_simultaneous_lower(
            pattern_diffs, reps=400, rng=rng_mt, block=block, alpha=args.alpha
        )
        results["simultaneous_lower_log"] = lowers
        results["simultaneous_lower_speedup"] = {k: float(np.exp(v)) for k, v in lowers.items()}
    return results


def _ensure_out_path(path_str: str) -> Path:
    """Return a normalized output path ensuring parent directory exists.

    If the provided path has no parent (filename only), place it under
    ./bench_outputs/ to avoid writing to the repo root or system root.
    """
    p = Path(path_str)
    if not p.parent or str(p.parent) in (".", ""):
        p = Path("bench_outputs") / p.name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _write_markdown(
    args: argparse.Namespace, results: dict[str, Any], patterns: list[tuple[str, MaskGen]]
):
    lines = [
        "| Pattern | Median Speedup | 95% CI | Simultaneous Lower (log) | Simultaneous Lower (speedup) |",
        "|---|---|---|---|---|",
    ]
    low_log = results.get("simultaneous_lower_log", {})
    low_spd = results.get("simultaneous_lower_speedup", {})
    for name, _ in patterns:
        pat_res = next(r for r in results["patterns"] if r["pattern"] == name)
        ci = pat_res["ci_speedup"]
        lines.append(
            f"| {name} | {pat_res['median_speedup']:.3f} | [{ci[0]:.3f}, {ci[1]:.3f}] | "
            f"{low_log.get(name, float('nan')):.3f} | {low_spd.get(name, float('nan')):.3f} |"
        )
    md_path = _ensure_out_path(args.markdown)
    with md_path.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main():  # pragma: no cover
    args = _parse_args()
    _validate_args(args)
    rng = np.random.default_rng(args.seed)
    patterns = _pattern_generators(args, rng)

    # Feature / guard evaluation uses first pattern only
    sample_mask = patterns[0][1]()[: min(args.rows, 50_000)]
    feat = features.compute_features(sample_mask)
    try:  # attempt GPU backend
        import cudf  # type: ignore  # noqa: F401  # pylint: disable=import-outside-toplevel,unused-import

        gpu_backend: str | None = "cudf"
    except Exception:  # pragma: no cover  # pylint: disable=broad-except
        gpu_backend = None
    cpu_backend = "pandas"

    try:
        guards.enforce_guard_or_raise("float64", feat["p_null"], feat)
    except AssertionError as e:
        out = {"guard": str(e), "features": feat}
        print(json.dumps(out, indent=2))
        if args.json:
            out_path = _ensure_out_path(args.json)
            with out_path.open("w", encoding="utf-8") as fh:
                json.dump(out, fh, indent=2)
        return

    if args.pilot:
        pilot_out = _pilot_run(patterns[0][1], args, gpu_backend, cpu_backend, feat)
        print(json.dumps(pilot_out, indent=2))
        if args.json:
            out_path = _ensure_out_path(args.json)
            with out_path.open("w", encoding="utf-8") as fh:
                json.dump(pilot_out, fh, indent=2)
        return

    results = _measure_patterns(patterns, args, gpu_backend, cpu_backend, feat)
    if args.report:
        report.enrich_with_report(results)
    print(json.dumps(results, indent=2))
    if args.json:
        out_path = _ensure_out_path(args.json)
        with out_path.open("w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)
    if args.markdown:
        _write_markdown(args, results, patterns)


if __name__ == "__main__":  # pragma: no cover
    main()
