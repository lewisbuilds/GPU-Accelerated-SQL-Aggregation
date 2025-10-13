from __future__ import annotations

import numpy as np


def lag1_autocorr(mask: np.ndarray) -> float:
    x = mask.astype(float)
    if len(x) < 2:
        return 0.0
    x0, x1 = x[:-1], x[1:]
    num = ((x0 - x0.mean()) * (x1 - x1.mean())).sum()
    den = ((x0 - x0.mean()) ** 2).sum()
    return float(num / den) if den else 0.0


def run_lengths(mask: np.ndarray) -> dict[str, float]:
    if len(mask) == 0:
        return {"null_mean": 0.0, "valid_mean": 0.0}
    diffs = np.diff(mask.astype(int))
    change_idx = np.where(diffs != 0)[0] + 1
    segments = np.split(mask, change_idx)
    null_runs = [len(s) for s in segments if s[0]]
    valid_runs = [len(s) for s in segments if not s[0]]
    return {
        "null_mean": float(np.mean(null_runs)) if null_runs else 0.0,
        "valid_mean": float(np.mean(valid_runs)) if valid_runs else 0.0,
    }


def fft_dominant_period(mask: np.ndarray, max_period: int = 128) -> int | None:
    x = mask.astype(float)
    n = len(x)
    if n == 0:
        return None
    x = x - x.mean()
    fft = np.fft.rfft(x)
    power = np.abs(fft) ** 2
    power[0] = 0
    if power.max() == 0:
        return None
    idx = int(np.argmax(power))
    freqs = np.fft.rfftfreq(n)
    freq = freqs[idx]
    if freq == 0:
        return None
    period = int(round(1 / freq))
    if 2 <= period <= max_period:
        return period
    return None


def bitmap_entropy(mask: np.ndarray, chunk: int = 8) -> float:
    if len(mask) == 0:
        return 0.0
    pad = (-len(mask)) % chunk
    if pad:
        mask = np.concatenate([mask, np.zeros(pad, dtype=bool)])
    reshaped = mask.reshape(-1, chunk)
    values = reshaped.dot(1 << np.arange(chunk))
    counts = np.bincount(values, minlength=2**chunk)
    probs = counts[counts > 0] / counts.sum()
    return float(-(probs * np.log2(probs)).sum() / chunk)


def compute_features(mask: np.ndarray) -> dict[str, float]:
    feats: dict[str, float] = {}
    feats["p_null"] = float(mask.mean())
    feats["lag1"] = lag1_autocorr(mask)
    feats.update(run_lengths(mask))
    period = fft_dominant_period(mask)
    feats["period"] = float(period) if period is not None else float("nan")
    feats["entropy8"] = bitmap_entropy(mask)
    return feats
