from __future__ import annotations

from collections.abc import Callable

import numpy as np


def uniform_mask(n: int, p_null: float, rng: np.random.Generator) -> np.ndarray:
    return rng.random(n) < p_null


def clustered_mask(
    n: int, p_null: float, rng: np.random.Generator, mean_run: int = 16
) -> np.ndarray:
    mask = np.zeros(n, dtype=bool)
    i = 0
    null = True
    while i < n:
        run = max(1, int(rng.geometric(1 / mean_run)))
        end = min(n, i + run)
        if null:
            mask[i:end] = True
        null = not null
        i = end
    current = mask.mean()
    if current > 0:
        scale = p_null / current
        if scale < 1:
            drop = rng.random(mask.sum()) > scale
            mask[np.where(mask)[0][drop]] = False
        elif scale > 1:
            need = int(p_null * n) - mask.sum()
            if need > 0:
                cand = np.where(~mask)[0]
                rng.shuffle(cand)
                mask[cand[:need]] = True
    return mask


def periodic_mask(n: int, period: int = 2) -> np.ndarray:
    pattern = np.zeros(period, dtype=bool)
    pattern[-1] = True
    return np.tile(pattern, (n + period - 1) // period)[:n]


def adversarial_burst_mask(n: int, burst: int = 64, gap: int = 256) -> np.ndarray:
    mask = np.zeros(n, dtype=bool)
    pos = 0
    toggle = True
    while pos < n:
        length = burst if toggle else gap
        end = min(n, pos + length)
        if toggle:
            mask[pos:end] = True
        toggle = not toggle
        pos = end
    return mask


PATTERNS: dict[str, Callable[..., np.ndarray]] = {
    "uniform": uniform_mask,
    "clustered": clustered_mask,
    "periodic": periodic_mask,
    "adversarial": adversarial_burst_mask,
}
