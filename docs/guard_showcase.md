# Guard Violation Showcase

| Pattern | Null p | Lag1 | Period | Entropy8 | Guard |
|---|---|---|---|---|---|
| uniform | 0.600 | 0.00 | 3.0 | 0.967 | Out-of-scope: float64 � high null-rate � clustered/periodic mask (lag1=0.00, period=3.0) |
| clustered | 0.601 | 0.63 | nan | 0.571 | Out-of-scope: float64 � high null-rate � clustered/periodic mask (lag1=0.63, period=NA) |
| periodic | 0.500 | -1.00 | 2.0 | -0.000 | Out-of-scope: float64 � high null-rate � clustered/periodic mask (lag1=-1.00, period=2.0) |
