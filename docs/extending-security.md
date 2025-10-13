# Extending & Security

## Adding Aggregations
1. Implement GPU + pandas logic in `AggregationEngine`.
2. Add to whitelist & validation in FDW.
3. Update tests & (optionally) benchmark patterns.

## Security Checklist
- Normalize and validate CSV paths.
- Enforce aggregate & column whitelist.
- Bound CLI parameters (rows, alpha, null-rate, patterns count).

## Guard Violations (Planned)
See `guard_showcase.md` for generated examples comparing in-scope vs out-of-scope distributions.
