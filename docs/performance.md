# Performance & Pitfalls

## Bottlenecks
- Small data: host↔device transfer overhead dwarfs kernel time.
- High null clustering: reduced parallel occupancy.

## Tips
- Batch operations; avoid many tiny CSV loads.
- Keep dtypes consistent (avoid silent float64 upcasts when not needed).

## Upcoming Instrumentation
- Split kernel vs host timing.
- Optional NVML power sampling (guarded dependency).
