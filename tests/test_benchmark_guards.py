import numpy as np

from bench import features
from bench import guards
from bench import mask_patterns


def test_uniform_passes_guard():
    rng = np.random.default_rng(0)
    mask = mask_patterns.uniform_mask(10_000, 0.5, rng)
    feats = features.compute_features(mask)
    assert guards.evaluate_distribution_guard("float64", feats["p_null"], feats) is None


def test_periodic_triggers_guard():
    mask = mask_patterns.periodic_mask(10_000, period=2)
    feats = features.compute_features(mask)
    reason = guards.evaluate_distribution_guard("float64", feats["p_null"], feats)
    assert reason is not None and "periodic" in reason.lower()
