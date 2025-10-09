from cudf_fdw.engine import GpuAggregationEngine


def main():
    engine = GpuAggregationEngine.from_csv("data/sales.csv")
    rows = engine.aggregate(["region"], {"sales_amount": "SUM", "units": "COUNT"})
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
