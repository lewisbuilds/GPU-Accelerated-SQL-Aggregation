from __future__ import annotations

import pathlib

import pytest


@pytest.fixture(scope="session")
def sample_csv_path(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    """Create a minimal deterministic CSV for aggregation tests.

    This avoids relying on a repo-tracked data/sales.csv file.
    """
    p = tmp_path_factory.mktemp("data") / "sales.csv"
    p.write_text(
        """region,sales_amount,units
East,100.50,4
East,50.00,1
West,75.25,2
West,125.00,3
""",
        encoding="utf-8",
    )
    return p
