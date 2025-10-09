import os
import pathlib

import pytest

try:  # Determine if cuDF available for GPU integration
    import cudf  # type: ignore  # noqa: F401

    _has_cudf = True
except Exception:  # pragma: no cover
    _has_cudf = False

# Guard optional imports
psycopg = None
try:  # pragma: no cover
    import psycopg  # type: ignore
except Exception:  # pragma: no cover
    pass

PG_DSN = os.environ.get("PG_DSN")  # e.g. postgres://postgres:example@localhost:5432/postgres
DATA_PATH = pathlib.Path(__file__).parent.parent / "data" / "sales.csv"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.gpu,
    pytest.mark.skipif(
        not (PG_DSN and psycopg),
        reason="PG_DSN env var and psycopg required for SQL integration test.",
    ),
    pytest.mark.skipif(not _has_cudf, reason="cuDF required for FDW integration test"),
]


def _exec(cur, sql: str):  # small wrapper
    cur.execute(sql)


def test_fdw_sql_aggregate_path():
    """Integration sanity path through PostgreSQL + Multicorn + FDW aggregate."""
    with psycopg.connect(PG_DSN) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            _exec(cur, "CREATE EXTENSION IF NOT EXISTS multicorn;")
            _exec(cur, "DROP SERVER IF EXISTS cudf_fdw_srv CASCADE;")
            _exec(
                cur,
                """CREATE SERVER cudf_fdw_srv FOREIGN DATA WRAPPER multicorn OPTIONS (
                   wrapper 'cudf_fdw.fdw.CuDFFDW'
                );""",
            )
            _exec(cur, "DROP FOREIGN TABLE IF EXISTS sales_gpu;")
            _exec(
                cur,
                f"""CREATE FOREIGN TABLE sales_gpu (
                        region text,
                        sales_amount numeric,
                        units int
                    ) SERVER cudf_fdw_srv OPTIONS (
                        csv_path '{DATA_PATH.as_posix()}',
                        aggregates 'sales_amount:SUM,units:COUNT',
                        aggregates 'sales_amount:SUM,units:SUM',
                        group_by 'region'
                    );""",
            )
            cur.execute("SELECT region, sales_amount, units FROM sales_gpu ORDER BY region;")
            rows = cur.fetchall()
            assert len(rows) == 2
            east = [r for r in rows if r[0] == "East"][0]
            assert float(east[1]) == pytest.approx(150.50, rel=0, abs=0.001)
            assert east[2] == 5
