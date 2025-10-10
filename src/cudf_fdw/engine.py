# ruff: noqa: I001  (conditional import ordering for optional backends)
from __future__ import annotations

from typing import Any, Protocol


_cudf_import_error: Exception | None
_pandas_import_error: Exception | None

try:  # Try GPU first
    import cudf  # type: ignore  # pylint: disable=import-error
except Exception as e:  # pragma: no cover  # pylint: disable=broad-exception-caught
    cudf = None  # type: ignore
    _cudf_import_error = e
else:  # pragma: no cover
    _cudf_import_error = None

try:  # Fallback CPU dataframe implementation
    import pandas as pd  # type: ignore  # pylint: disable=import-error
except Exception as e:  # pragma: no cover  # pylint: disable=broad-exception-caught
    pd = None  # type: ignore
    _pandas_import_error = e
else:  # pragma: no cover
    _pandas_import_error = None

SUPPORTED = {"sum", "avg", "min", "max", "count"}


class _GroupByLike(Protocol):  # pragma: no cover - typing aid only
    def agg(self, *args, **_kw) -> Any: ...  # returns dataframe-like
    def size(self) -> Any: ...
    def head(self, n: int) -> Any: ...


class _DataFrameLike(Protocol):  # pragma: no cover - typing aid only
    def groupby(self, *_cols, **_kw) -> _GroupByLike: ...
    def agg(self, *args, **_kw) -> Any: ...
    def head(self, n: int) -> Any: ...
    def to_pandas(self) -> Any: ...
    def __len__(self) -> int: ...
    def __getitem__(self, key: Any) -> Any: ...  # column selection (e.g., df[group_cols])


class AggregationEngine:
    """Unified aggregation engine with optional GPU acceleration.

    If cuDF is available it is preferred; otherwise falls back to pandas so
    unit tests can run in CPU-only environments (e.g. CI, developer laptops).
    API is intentionally small/stable.
    """

    def __init__(self, df: _DataFrameLike, backend: str) -> None:
        self._df = df
        self._backend = backend  # "cudf" or "pandas"

    @property
    def backend(self) -> str:
        return self._backend

    @classmethod
    def from_csv(cls, path: str) -> AggregationEngine:
        if cudf is not None:
            df = cudf.read_csv(path)
            return cls(df, "cudf")
        if pd is not None:
            df = pd.read_csv(path)
            return cls(df, "pandas")
        raise RuntimeError(
            "Neither cuDF nor pandas available - install one to use AggregationEngine"
        ) from (
            _cudf_import_error or _pandas_import_error
        )  # type: ignore[arg-type]

    def aggregate(self, group_cols: list[str], aggs: dict[str, str]) -> list[dict[str, Any]]:
        """Perform grouped (or global) aggregations.

        Splits complexity into backend‑specific helpers to keep this entry
        point small (reduce cyclomatic complexity flagged by Ruff C901).
        """
        self._validate_aggs(aggs)
        count_cols, other_aggs = self._split_aggs(aggs)
        if group_cols:
            grouped = self._aggregate_grouped(group_cols, other_aggs, count_cols)
        else:
            grouped = self._aggregate_no_group(other_aggs, count_cols)
        return self._to_records(grouped)

    # ---------------------------- helper methods ----------------------------
    @staticmethod
    def _validate_aggs(aggs: dict[str, str]) -> None:
        for func in aggs.values():
            if func.lower() not in SUPPORTED:
                raise ValueError(f"Unsupported aggregate: {func}")

    @staticmethod
    def _split_aggs(aggs: dict[str, str]) -> tuple[list[str], dict[str, str]]:
        count_cols = [col for col, func in aggs.items() if func.lower() == "count"]
        other_aggs = {col: func.lower() for col, func in aggs.items() if func.lower() != "count"}
        return count_cols, other_aggs

    def _aggregate_grouped(self, group_cols: list[str], other_aggs: dict[str, str], count_cols: list[str]):  # type: ignore[override]
        if self._backend == "cudf":
            return self._aggregate_grouped_cudf(group_cols, other_aggs, count_cols)
        return self._aggregate_grouped_pandas(group_cols, other_aggs, count_cols)

    def _aggregate_no_group(self, other_aggs: dict[str, str], count_cols: list[str]):  # type: ignore[override]
        if self._backend == "cudf":
            return self._aggregate_no_group_cudf(other_aggs, count_cols)
        return self._aggregate_no_group_pandas(other_aggs, count_cols)

    # Backend specific implementations -------------------------------------------------
    def _aggregate_grouped_cudf(
        self, group_cols: list[str], other_aggs: dict[str, str], count_cols: list[str]
    ):
        # Compute requested aggregations first
        if other_aggs:
            base = self._df.groupby(group_cols).agg(other_aggs).reset_index()
        else:
            # Start from unique group keys as a DataFrame
            base = self._df[group_cols].drop_duplicates().reset_index(drop=True)

        # If row-counts are requested, compute group sizes and merge
        if count_cols:
            sizes = self._df.groupby(group_cols).size().reset_index(name="__row_count__")
            base = base.merge(sizes, on=group_cols, how="left")
            for c in count_cols:
                base[c] = base["__row_count__"].astype(int)
            base = base.drop(columns=["__row_count__"])  # type: ignore

        return base

    def _aggregate_grouped_pandas(
        self, group_cols: list[str], other_aggs: dict[str, str], count_cols: list[str]
    ):  # pragma: no cover - logic parity w/ previous implementation
        base = (
            self._df.groupby(group_cols).agg(other_aggs)
            if other_aggs
            else self._df.groupby(group_cols).head(0)
        )
        if not other_aggs:
            # ensure DataFrame with index for later join
            base = (
                base.groupby(level=list(range(len(group_cols))))
                .size()
                .to_frame(name="__dummy__")
                .drop(columns=["__dummy__"])  # type: ignore
            )
        if count_cols:
            counts = self._df.groupby(group_cols).size().rename("__row_count__")
            base = base.join(counts)
        base = base.reset_index()
        if count_cols:  # Expand count columns: same row count value
            for c in count_cols:
                base[c] = base["__row_count__"].astype(int)
            base = base.drop(columns=["__row_count__"])
        return base

    def _aggregate_no_group_cudf(
        self, other_aggs: dict[str, str], count_cols: list[str]
    ):  # pragma: no cover - backend specific
        parts = []
        if other_aggs:
            parts.append(self._df.agg(other_aggs).to_frame().T)
        if count_cols:
            row_ct = int(len(self._df))
            import pandas as _pd  # type: ignore

            count_df = _pd.DataFrame([{c: row_ct for c in count_cols}])
            parts.append(count_df)
        # join parts horizontally
        grouped = parts[0] if parts else self._df.head(0).to_pandas()  # type: ignore[union-attr]
        for p in parts[1:]:
            grouped = grouped.join(p)
        return grouped

    def _aggregate_no_group_pandas(self, other_aggs: dict[str, str], count_cols: list[str]):
        import pandas as _pd  # type: ignore

        data: dict[str, Any] = {}
        if other_aggs:
            agg_res = self._df.agg(other_aggs)
            for k, v in agg_res.items():
                data[k] = v
        if count_cols:
            row_ct = int(len(self._df))
            for c in count_cols:
                data[c] = row_ct
        return _pd.DataFrame([data])

    def _to_records(self, grouped):  # type: ignore[override]
        if self._backend == "cudf":  # normalize cudf -> pandas -> records
            return grouped.to_pandas().to_dict(orient="records")
        return grouped.to_dict(orient="records")


# Backwards compatibility name kept (GPU specific name)
GpuAggregationEngine = AggregationEngine


def main():  # pragma: no cover minimal utility
    import argparse
    import json

    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--group", nargs="*", default=[])
    p.add_argument("--agg", action="append", help="col:FUNC")
    args = p.parse_args()
    engine = AggregationEngine.from_csv(args.csv)
    aggs = dict(a.split(":", 1) for a in (args.agg or []))
    print(json.dumps(engine.aggregate(args.group, aggs), indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
