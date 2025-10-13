#!/usr/bin/env bash
set -euo pipefail

# 1) Driver visibility
if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi not found" >&2
  exit 1
fi
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || exit 1

# 2) Python GPU stack readiness
python3.11 - <<'PY'
import sys
try:
    import cudf, cupy, rmm
    import cupy.cuda.runtime as rt
    n = rt.getDeviceCount()
    assert n > 0, "No CUDA devices visible"
    print("GPU OK:", n, "device(s)")
except Exception as e:
    print("GPU stack not ready:", e, file=sys.stderr)
    sys.exit(1)
PY
