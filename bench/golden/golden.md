# Golden Benchmark Summary

Patterns: uniform, periodic  
Rows: 500000  Iterations: 25  Alpha: 0.05

| Pattern | Median Speedup | 95% CI | Median Log |
|---|---|---|---|
| uniform | 0.996 | [0.974, 1.031] | -0.004 |
| periodic | 1.012 | [1.005, 1.077] | 0.012 |

## Provenance
```json
{
  "timestamp_utc": "2025-10-08T13:14:11.130130Z",
  "python": "3.11.9",
  "git_sha": "e0b6009a93f005dc6464f464213831e398d59502",
  "packages": {
    "numpy": "1.26.4",
    "pyarrow": "16.1.0"
  },
  "cudf": "none",
  "config": {
    "rows": 500000,
    "n": 25,
    "patterns": [
      "uniform",
      "periodic"
    ],
    "alpha": 0.05
  },
  "integrity_hash": "7d7f68deae8384e0618b0c6e5fc7c92f292b1b4ed5287c59cc5de835da923485"
}
```
