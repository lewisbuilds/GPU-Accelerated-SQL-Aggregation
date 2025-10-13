"""Developer environment sanity checks.

Run:
  poetry run python scripts/dev_check.py
"""

from __future__ import annotations

import importlib
import json
import platform
import shutil
import sys
from dataclasses import asdict
from dataclasses import dataclass


@dataclass
class CheckResult:
    python: str
    poetry: bool
    gpu_available: bool
    cudf_version: str | None
    numpy_version: str | None
    pyarrow_version: str | None


def has_poetry() -> bool:
    return shutil.which("poetry") is not None


def version_of(pkg: str) -> str | None:
    try:  # runtime import to avoid failures during partial installs
        mod = importlib.import_module(pkg)
        return getattr(mod, "__version__", None)
    except Exception:  # pragma: no cover
        return None


def gpu_probe() -> tuple[bool, str | None]:
    try:  # attempt cuDF first
        import cudf  # type: ignore

        return True, getattr(cudf, "__version__", None)
    except Exception:
        return False, None


def main() -> int:
    gpu_ok, cudf_ver = gpu_probe()
    result = CheckResult(
        python=platform.python_version(),
        poetry=has_poetry(),
        gpu_available=gpu_ok,
        cudf_version=cudf_ver,
        numpy_version=version_of("numpy"),
        pyarrow_version=version_of("pyarrow"),
    )
    print(json.dumps(asdict(result), indent=2))
    if not result.poetry:
        print("WARNING: Poetry not detected in PATH", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
