from pathlib import Path

from cudf_fdw.engine import GpuAggregationEngine


def main():
    # Resolve CSV relative to the repo root so this works regardless of CWD
    repo_root = Path(__file__).resolve().parents[1]
    csv_path = repo_root / "data" / "sales.csv"
    engine = GpuAggregationEngine.from_csv(str(csv_path))
    rows = engine.aggregate(["region"], {"sales_amount": "SUM", "units": "COUNT"})
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
