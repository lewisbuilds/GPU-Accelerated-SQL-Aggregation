from __future__ import annotations

from collections.abc import Callable

import numpy as np


def _moving_block_indices(n: int, block: int, rng: np.random.Generator) -> np.ndarray:
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, max(1, n - block + 1), size=n_blocks)
    idx: list[int] = []
    for s in starts:
        idx.extend(range(s, min(n, s + block)))
        if len(idx) >= n:
            break
    return np.array(idx[:n])


def paired_bootstrap(
    samples: np.ndarray,
    reps: int,
    rng: np.random.Generator,
    block: int | None = None,
    stat: Callable[[np.ndarray], float] = np.median,
) -> np.ndarray:
    n = len(samples)
    out = np.empty(reps)
    for i in range(reps):
        if block and block > 1:
            idx = _moving_block_indices(n, block, rng)
        else:
            idx = rng.integers(0, n, size=n)
        out[i] = stat(samples[idx])
    return out


def maxT_simultaneous_lower(
    diffs: dict[str, np.ndarray],
    reps: int,
    rng: np.random.Generator,
    block: int | None,
    alpha: float = 0.05,
) -> dict[str, float]:
    labels = list(diffs.keys())
    mat = np.vstack([diffs[k] for k in labels])
    med = np.median(mat, axis=1)
    m, n = mat.shape
    boot = np.empty((reps, m))
    for b in range(reps):
        if block and block > 1:
            idx = _moving_block_indices(n, block, rng)
        else:
            idx = rng.integers(0, n, size=n)
        boot[b] = np.median(mat[:, idx], axis=1)
    centered = boot - med
    min_dist = centered.min(axis=1)
    q = np.quantile(min_dist, alpha)
    lowers = med - q
    return {labels[i]: float(lowers[i]) for i in range(m)}
