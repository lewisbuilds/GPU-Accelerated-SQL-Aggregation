from cudf_fdw.engine import AggregationEngine


def test_package_success_end_to_end(sample_csv_path):
    """Smoke: run two aggregates grouped by region and validate East totals.

    Runs on either pandas (CPU fallback) or cuDF (GPU) backend.
    """
    engine = AggregationEngine.from_csv(str(sample_csv_path))
    rows = engine.aggregate(["region"], {"sales_amount": "SUM", "units": "COUNT"})
    rows = engine.aggregate(["region"], {"sales_amount": "SUM", "units": "SUM"})
    regions = {r["region"]: r for r in rows}
    assert "East" in regions and "West" in regions
    assert round(regions["East"]["sales_amount"], 2) == 150.50
    assert regions["East"]["units"] == 5
    assert engine.backend in {"pandas", "cudf"}
