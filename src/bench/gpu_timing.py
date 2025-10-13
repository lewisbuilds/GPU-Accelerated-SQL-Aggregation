"""GPU timing helpers using CUDA events (cupy) with graceful fallback.

We prefer CUDA event timing (records GPU kernel execution latency) rather than
wall-clock Python time which includes host scheduling and potential async gaps.

If cupy or a CUDA device is unavailable we silently fall back to time.perf_counter.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from collections.abc import Iterator
from contextlib import contextmanager

try:  # pragma: no cover - exercised only in GPU environments
    import cupy as _cp  # type: ignore

    _have_gpu = True
except Exception:  # pragma: no cover
    _cp = None  # type: ignore
    _have_gpu = False


def gpu_available() -> bool:
    return _have_gpu


@contextmanager
def cuda_timer() -> Iterator[Callable[[], float]]:
    """Context manager yielding a zero-arg function returning elapsed seconds.

    Usage:
        with cuda_timer() as elapsed:
            do_work()
        print(elapsed())
    """
    if _have_gpu:  # pragma: no cover - GPU specific path
        start = _cp.cuda.Event()
        end = _cp.cuda.Event()
        start.record()

        def _elapsed() -> float:
            end.record()
            end.synchronize()
            return _cp.cuda.get_elapsed_time(start, end) / 1000.0  # ms -> s

        yield _elapsed
    else:
        t0 = time.perf_counter()

        def _elapsed() -> float:
            return time.perf_counter() - t0

        yield _elapsed


@contextmanager
def segmented_timer() -> Iterator[Callable[[str], None]]:
    """Segmented timing helper.

    Yields a function `mark(label)` which records time since last mark.
    After context, call `mark` with label "_end" to finalize if needed.
    Returns nothing; use `get_segments()` to retrieve stored segments.
    """
    stamps: dict[str, float] = {}
    order: list[str] = []
    last = time.perf_counter()

    def mark(label: str) -> None:
        nonlocal last
        now = time.perf_counter()
        stamps[label] = now - last
        order.append(label)
        last = now

    try:
        yield mark
    finally:
        # expose collected segments via attribute for caller
        mark.segments = [(lbl, stamps[lbl]) for lbl in order]  # type: ignore[attr-defined]


@contextmanager
def nvml_power_sampler(interval_s: float = 0.05):  # pragma: no cover - hardware dependent
    """Sample average GPU power draw (Watts) over a code region if NVML available.

    Falls back silently (yields noop) if NVML not present.
    """
    try:
        import pynvml  # type: ignore

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        samples: list[float] = []
        running = True

        def _poll():
            while running:
                try:
                    mw = pynvml.nvmlDeviceGetPowerUsage(handle)  # milliwatts
                    samples.append(mw / 1000.0)
                except Exception:
                    break
                time.sleep(interval_s)

        import threading

        th = threading.Thread(target=_poll, daemon=True)
        th.start()

        yield lambda: (float(sum(samples) / len(samples)) if samples else float("nan"))
        running = False
        th.join(timeout=0.2)
        pynvml.nvmlShutdown()
    except Exception:
        yield lambda: float("nan")
