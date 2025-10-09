import pathlib

from cudf_fdw.engine import AggregationEngine

DATA_PATH = pathlib.Path(__file__).parent.parent / "data" / "sales.csv"


def test_package_success_end_to_end():
    """Smoke: run two aggregates grouped by region and validate East totals.

    Runs on either pandas (CPU fallback) or cuDF (GPU) backend.
    """
    engine = AggregationEngine.from_csv(str(DATA_PATH))
    rows = engine.aggregate(["region"], {"sales_amount": "SUM", "units": "COUNT"})
    rows = engine.aggregate(["region"], {"sales_amount": "SUM", "units": "SUM"})
    regions = {r["region"]: r for r in rows}
    assert "East" in regions and "West" in regions
    assert round(regions["East"]["sales_amount"], 2) == 150.50
    assert regions["East"]["units"] == 5
    assert engine.backend in {"pandas", "cudf"}
