# Performance & Benchmark Contribution Guide

This project treats performance evidence as a first-class artifact. Follow this checklist when proposing changes that may affect speed, memory, or statistical properties.

## 1. Baseline Verification
- [ ] Run `poetry run golden-bench verify` → must pass (no drift) before changes.
- [ ] Capture current short report:
```powershell
poetry run python -m bench.benchmark --rows 50000 --patterns uniform periodic --n 12 --null-rate 0.2 --report --json before.json
```

## 2. Make Changes
Keep PRs small. Avoid mixing refactors with new features if they affect performance.

## 3. Re-run Benchmarks
```powershell
poetry run python -m bench.benchmark --rows 50000 --patterns uniform periodic --n 12 --null-rate 0.2 --report --json after.json
```

## 4. Compare Deltas
- Compute median log speedup delta per pattern.
- If absolute delta > 0.05 log units (~5%) justify with rationale (e.g., correctness improvement, enabling future optimization).
- If simultaneous lower bound regresses below SESOI threshold (ln 0.90) investigate root cause or update methodology docs.

Quick comparison helper (Python one-liner):
```powershell
poetry run python - <<"PY"
import json, math
before=json.load(open('before.json'))
after=json.load(open('after.json'))
for p in {r['pattern'] for r in before['patterns']}:
    b=next(r for r in before['patterns'] if r['pattern']==p)
    a=next(r for r in after['patterns'] if r['pattern']==p)
    d=a['median_log_speedup']-b['median_log_speedup']
    print(f"{p}: Δlog={d:.4f} (≈ {(math.exp(d)-1)*100:.2f}% speed change)")
PY
```

## 5. Update Golden (Only If Required)
If a change intentionally improves stable performance across environments:
1. Include explanation in PR description.
2. Run `poetry run golden-bench generate` (separate commit).
3. Ensure matrix workflow passes with new golden.

## 6. Document Decisions
- For impactful deltas create an ADR using template (`docs/adr-template.md`).
- Link ADR in PR.

## 7. PR Checklist (include in description)
- [ ] Baseline golden verify passed before change
- [ ] After-change benchmark attached (JSON)
- [ ] Δ medians within ±5% OR justified
- [ ] Simultaneous lower bounds not degraded beyond thresholds
- [ ] ADR added (if required)
- [ ] Docs updated

## 8. Common Pitfalls
- Mixing random seeds: keep `--seed` unless studying variability.
- Small `--n` (unstable inference): use ≥12 for comparison passes.
- Ignoring guard warnings: out-of-scope distributions invalidate comparisons.

## 9. Accessibility & Reproducibility
Ensure any added output remains machine-parseable (JSON) and human-scannable (markdown summary) without relying on color-only cues.

## 10. How to Update Golden Benchmarks
Refer to ADR-0001 (`docs/adr/adr-0001-golden-benchmark-update-policy.md`). Only regenerate when a justified trigger applies.

### 10.1 Triggers (Summary)
- PERF-001: Verified multi-pattern improvement (|Δ median log speedup| > 0.02, beneficial)
- PERF-002: Correctness fix invalidates old baseline
- PERF-003: Ecosystem / dependency shift (CUDA, RAPIDS, ABI) changes stable distribution
- PERF-004: Benchmark scope change (add/remove pattern) — requires its own ADR

### 10.2 Workflow
1. Baseline verify:
   ```powershell
   poetry run golden-bench verify
   ```
2. Snapshot existing artifacts:
   ```powershell
   copy bench/golden/golden.json before.json
   ```
3. Apply code change (separate commit) – do NOT regenerate yet.
4. Re-run benchmark for evidence (optionally higher N for stability):
   ```powershell
   poetry run python -m bench.benchmark --rows 500000 --patterns uniform periodic --n 25 --alpha 0.05 --json after.json
   ```
5. Compute deltas:
   ```powershell
   poetry run python - <<'PY'
import json, math
b=json.load(open('before.json')); a=json.load(open('after.json'))
for p in {r['pattern'] for r in b['patterns']}:
    bb=next(r for r in b['patterns'] if r['pattern']==p)
    aa=next(r for r in a['patterns'] if r['pattern']==p)
    d=aa['median_log_speedup']-bb['median_log_speedup']
    print(f"{p}: Δlog={d:.4f} ≈ {(math.exp(d)-1)*100:.2f}%")
PY
   ```
6. If criteria satisfied, regenerate:
   ```powershell
   poetry run golden-bench generate
   git add bench/golden/golden.json bench/golden/golden.md
   git commit -m "chore(golden): regenerate after <reason>"
   ```
7. Prepare PR:
   - Separate commits (logic vs golden)
   - Include before/after JSON or delta output
   - Reference ADR-0001 and any new ADRs for scope changes

### 10.3 Reviewer Checklist
| Item | Pass? |
|------|-------|
| Separate commits | |
| Justified trigger documented | |
| Δ medians threshold respected or justified | |
| No single-pattern regression without rationale | |
| ADR referenced (and new ADR if scope change) | |

### 10.4 Common Rejections
| Reason | Example |
|--------|---------|
| Cosmetic refactor only | Code style tweak regenerates golden |
| Unstable run (low N) | N=3 with noisy deltas |
| Missing baseline snapshot | No `before.json` evidence |

### 10.5 Accessibility Note
Benchmark delta evidence should rely on text (tables/log lines) not color cues.

---
Generated with accessibility in mind—validate with tooling.
