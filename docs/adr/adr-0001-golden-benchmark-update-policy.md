---
title: "ADR-0001: Golden Benchmark Update Policy"
status: "Proposed"
date: "2025-10-08"
authors: "Engineering Team"
tags: ["architecture", "performance", "benchmarking"]
supersedes: ""
superseded_by: ""
---

# ADR-0001: Golden Benchmark Update Policy

## Status
Proposed

## Context
The project relies on reproducible performance evidence via golden benchmark artifacts located under `bench/golden/`. These artifacts (JSON + Markdown) encode:
- Median log speedups per pattern (currently: `uniform`, `periodic`)
- Confidence intervals and provenance (commit hash, env, library versions)

They serve as:
- A guard against accidental regressions
- A didactic baseline for statistical transparency

Uncontrolled or ad‑hoc regeneration erodes trust, obscures regressions, and weakens educational value. A formal policy is needed to:
- Define legitimate triggers for updates
- Enforce evidence standards
- Separate semantic changes from data refresh noise
- Require rationale and traceability

## Decision
Adopt a governed update protocol:
1. Golden benchmarks MAY be regenerated only when:
   - PERF-001: A verified, statistically supported improvement (all tracked patterns) exceeds noise thresholds (|Δ median log speedup| > 0.02 and directionally beneficial), OR
   - PERF-002: A correctness fix alters algorithmic path making old baseline invalid, OR
   - PERF-003: An unavoidable ecosystem change (dependency ABI / CUDA / RAPIDS) shifts stable distributions, OR
   - PERF-004: Scope expansion intentionally adds/removes benchmark patterns (requires separate ADR).
2. Each regeneration MUST:
   - EVID-001: Capture pre-change verify output (JSON) + post-change benchmark JSON in the PR
   - EVID-002: Include delta analysis (median log + percent speed change) per pattern
   - TRACE-001: Reference this ADR and (if applicable) additional ADR covering feature/scope expansion
3. Commit hygiene:
   - GIT-001: Code / algorithm changes in one commit (with analysis)
   - GIT-002: Golden regeneration in a distinct follow-up commit: `chore(golden): regenerate after <reason>`
4. Documentation:
   - DOC-001: If methodology shifts (stat model, CI bounds) update related docs (`docs/methodology.md`, performance guide)
   - DOC-002: Link ADR in PR description & changelog (if maintained)
5. Rejection criteria:
   - REJ-001: Pure cosmetic refactors without measurable improvement
   - REJ-002: Single-pattern wins that degrade another pattern unless net effect justified
   - REJ-003: Regeneration due solely to transient environment noise

## Consequences
### Positive
- POS-001: Strong audit trail discourages silent regressions
- POS-002: Cleaner diffs (data refresh isolated)
- POS-003: Improves reviewer efficiency—focus on evidence not guesswork
- POS-004: Promotes statistical literacy and reproducibility norms

### Negative
- NEG-001: Slightly higher procedural overhead for legitimate updates
- NEG-002: May delay merging small performance uplifts pending full evidence
- NEG-003: Adds cognitive load for new contributors

### Neutral
- NEU-001: Does not change runtime benchmarking logic
- NEU-002: Does not affect scope guard rails

## Alternatives
- ALT-001: Regenerate on every performance-related PR (Rejected: noise + churn)
- ALT-002: Automate nightly regeneration (Rejected: hides regressions; baseline loses pedagogical value)
- ALT-003: Single monolithic artifact per release tag (Rejected: slower iteration; delays feedback)

## Rationale
Structured policy balances rigor (preventing drift) with flexibility (allowing legitimate improvements). Separation of commits improves bisectability and aligns with minimal, inspectable change sets. Evidence + threshold criteria mitigate overfitting to noise.

## Evidence
- EVB-001: Historical variability (pilot runs) shows median log speedup standard deviation < 0.01 for current patterns at N=25 ⇒ 0.02 threshold is >2σ (reduces false positives).
- EVB-002: Prior educational review sessions flagged confusion when artifacts regenerated without narrative.

## Follow-ups
- FUP-001: Add CI gate to warn if golden updated in same commit as logic changes
- FUP-002: Extend patterns only with separate ADR (future: clustered / high-null patterns)
- FUP-003: Automate delta table generator script for PR template

## Accessibility & Security Notes
No new surface area. Documentation additions should maintain contrast and avoid color-only encoding in delta tables.

## References
- Golden generation script: `scripts/make_golden.py`
- Benchmark summary artifacts: `bench/golden`
- Methodology: `docs/methodology.md`
