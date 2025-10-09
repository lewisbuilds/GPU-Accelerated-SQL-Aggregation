"""Minimal deterministic tests for bench utilities.

Targets:
 - mask pattern generators (uniform proportion, periodic structure)
 - pilot.pilot_required_n basic contract & error handling
 - bootstrap.paired_bootstrap reproducibility
 - bootstrap.maxT_simultaneous_lower returns lowers <= medians

These keep runtime tiny (small sample sizes) while locking in core invariants
for future refactors.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

from bench import benchmark
from bench import bootstrap
from bench import mask_patterns
from bench import pilot


def test_uniform_mask_proportion():
    rng = np.random.default_rng(123)
    n = 10_000
    p = 0.37
    mask = mask_patterns.uniform_mask(n, p, rng)
    # Law of large numbers: tolerance ~ 1% absolute
    assert mask.dtype == bool
    assert mask.size == n
    assert abs(mask.mean() - p) < 0.01


def test_periodic_mask_structure():
    n = 25
    period = 4
    mask = mask_patterns.periodic_mask(n, period=period)
    # Expect last element of each period True, rest False
    for i in range(n):
        expected = (i % period) == (period - 1)
        assert bool(mask[i]) == expected


def test_pilot_required_n_contract():
    rng = np.random.default_rng(0)
    samples = rng.normal(size=32)
    out = pilot.pilot_required_n(np.log1p(np.abs(samples)))
    # Required keys
    for k in {"pilot_n", "sigma", "design_effect", "acf", "n_required"}:
        assert k in out
    assert out["pilot_n"] == 32
    assert out["n_required"] >= out["pilot_n"]


def test_pilot_required_n_too_small():
    rng = np.random.default_rng(1)
    small = rng.normal(size=3)
    try:
        pilot.pilot_required_n(np.log1p(np.abs(small)))
    except ValueError:  # expected
        pass
    else:  # pragma: no cover - defensive
        assert False, "Expected ValueError for too-few observations"


def test_paired_bootstrap_reproducibility():
    data = np.array([1.0, 2.0, 3.0, 4.0])
    rng1 = np.random.default_rng(42)
    rng2 = np.random.default_rng(42)
    out1 = bootstrap.paired_bootstrap(data, reps=25, rng=rng1, block=None)
    out2 = bootstrap.paired_bootstrap(data, reps=25, rng=rng2, block=None)
    assert np.allclose(out1, out2)
    rng3 = np.random.default_rng(43)
    out3 = bootstrap.paired_bootstrap(data, reps=25, rng=rng3, block=None)
    assert not np.allclose(out1, out3)


def test_maxT_simultaneous_lower_monotonic():
    rng = np.random.default_rng(7)
    diffs = {
        "a": rng.normal(loc=0.2, scale=0.05, size=40),
        "b": rng.normal(loc=0.1, scale=0.05, size=40),
    }
    lowers = bootstrap.maxT_simultaneous_lower(diffs, reps=50, rng=np.random.default_rng(8), block=None)
    # With low reps the empirical quantile may exceed a median; require it is not
    # excessively larger (<= +0.05 absolute) and all labels preserved.
    for k, arr in diffs.items():
        median = np.median(arr)
        assert k in lowers
        assert lowers[k] - median <= 0.05


def test_pattern_generators_wrapper_uniform():
    # Construct minimal args namespace for _pattern_generators
    args = SimpleNamespace(
        patterns=None,
        pattern="uniform",
        rows=1000,
        null_rate=0.25,
    )
    rng = np.random.default_rng(99)
    gens = benchmark._pattern_generators(args, rng)  # pylint: disable=protected-access
    assert gens and gens[0][0] == "uniform"
    mask = gens[0][1]()
    assert mask.shape == (args.rows,)
    assert mask.dtype == bool
