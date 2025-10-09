import os

from cudf_fdw.engine import AggregationEngine

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sales.csv")


def test_basic_aggs():
    engine = AggregationEngine.from_csv(os.path.normpath(CSV_PATH))
    rows = engine.aggregate(["region"], {"sales_amount": "SUM", "units": "COUNT"})
    rows = engine.aggregate(["region"], {"sales_amount": "SUM", "units": "SUM"})
    by_region = {r["region"]: r for r in rows}
    assert round(by_region["East"]["sales_amount"], 2) == 150.50
    assert by_region["East"]["units"] == 5
    assert engine.backend in {"pandas", "cudf"}
