"""Top-level package exports for cudf_fdw.

Multicorn (and thus the FDW class) is optional for local development and
CPU-only test runs. We guard its import so unit tests that only exercise the
pure Python/GPU aggregation engine do not require the external PostgreSQL
extension to be installed in the environment.
"""

__all__ = ["GpuAggregationEngine"]

from .engine import GpuAggregationEngine  # noqa: F401

try:  # pragma: no cover - exercised only when multicorn is installed
    from .fdw import CuDFFDW  # noqa: F401

    __all__.append("CuDFFDW")
except ModuleNotFoundError:  # multicorn not present; expose engine-only API
    CuDFFDW = None  # type: ignore
