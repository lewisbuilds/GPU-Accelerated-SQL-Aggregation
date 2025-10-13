import os
import re
from collections.abc import Iterator
from collections.abc import Sequence
from typing import Any

from multicorn import ForeignDataWrapper

from .engine import AggregationEngine


class CuDFFDW(ForeignDataWrapper):
    """Minimal Multicorn FDW bridging to a cuDF aggregation engine.

    Scope: read-only, aggregate pushdown only. Aggregates and grouping are
    provided via FDW options for simplicity (not production-quality planning).
    """

    def __init__(self, options: dict[str, str], columns: list[Any]):  # type: ignore[override]
        super().__init__(options, columns)
        self.options = options
        csv_path = options.get("csv_path")
        if not csv_path:
            raise RuntimeError("csv_path option is required")
        # Path security: require absolute path & prevent traversal symlink tricks by resolving.
        # NOTE: This is a simplified approach; in hardened deployments consider confining inside
        # a predefined base directory.
        real_path = os.path.realpath(csv_path)
        if not os.path.isabs(real_path):
            raise RuntimeError("csv_path must be absolute")
        if not os.path.exists(real_path):
            raise RuntimeError("csv_path does not exist")
        if not real_path.endswith((".csv", ".CSV")):
            raise RuntimeError("csv_path must end with .csv")
        # Basic safeguard against newline / control chars that could pollute logs.
        if re.search(r"[\r\n\x00]", real_path):  # pragma: no cover (defensive)
            raise RuntimeError("Invalid characters in csv_path")
        self.engine = AggregationEngine.from_csv(real_path)
        if (
            getattr(self.engine, "backend", None) != "cudf"
        ):  # pragma: no cover - requires missing GPU in prod
            raise RuntimeError(
                "CuDFFDW requires cuDF (GPU backend). Install RAPIDS/cuDF in the server environment."
            )

    def execute(
        self, _quals: Sequence[Any], columns: Sequence[str]
    ) -> Iterator[dict[str, Any]]:  # noqa: D401  # quals unused (planning out-of-scope)
        aggs_opt = self.options.get("aggregates")  # format: col:FUNC,col:FUNC
        group_opt = self.options.get("group_by")  # format: col[,col]
        if not aggs_opt:
            raise RuntimeError("Aggregates required (aggregates option)")
        aggs = dict(item.split(":", 1) for item in aggs_opt.split(","))
        groups = group_opt.split(",") if group_opt else []

        # Whitelist aggregate functions enforced by engine; validate early to fail fast.
        allowed_funcs = {"SUM", "AVG", "MIN", "MAX", "COUNT"}
        for col, func in aggs.items():
            f_upper = func.upper()
            if f_upper not in allowed_funcs:
                raise RuntimeError(f"Unsupported aggregate function: {func}")
            aggs[col] = f_upper  # Normalize

        # Column existence check: ensure referenced group & agg columns are part of declared FDW columns.
        declared_cols = {getattr(c, "name", str(c)) for c in self.columns}
        missing = [c for c in list(aggs.keys()) + groups if c not in declared_cols]
        if missing:
            raise RuntimeError(f"Referenced columns not declared in foreign table: {missing}")

        rows = self.engine.aggregate(groups, aggs)
        yield from rows

    # Explicitly disallow writes
    def insert(self, values: dict[str, Any]):  # pragma: no cover
        raise NotImplementedError("Read-only FDW (aggregations only)")
