# Phase 3B verification notes

The formal held-out evaluation is closed. Run [36842139464](https://github.com/St-roller/returnguard/actions/runs/36842139464), attempt 1, succeeded under execution/authorization commit `fc32b0451522887d9d3a212a354a70b56c4dde0e`. Additive offline scoring and orchestration were committed before test at `3b6272d34a7caef57d522a4e3625ec62af518a19`. Locked inference, policy, prompt, schema, aggregation, retry policy, baseline and threshold were not edited.

## Evidence and verification

- Exactly 90 distinct test IDs and 90 distinct content-response IDs; 90 started/outcome journals; one request per case, zero infrastructure retries. No additional live calls during verification.
- Original Actions artifact 11150709999, 980269 bytes, SHA-256 `e6276f88386b2f0da5b987e3be3f64786648d171c591b67beade9695184fd6bd`. All 575 archive entries were checked; 293 existing files matched byte for byte before 282 new files were materialized.
- Raw prediction SHA-256 `ab157376bb1df7cf8980489c5690042bb922f4df0ad3bf078ff34dbee6509b69`, frozen at 2026-10-01T09:24:35.600431+00:00. Scoring started at 09:24:35.970004+00:00 with that same hash before the first gold join.
- Every request journal binds the Chinese message, locked model, prompt and exact schema, tools=[] and omitted sampling. Each raw extraction matches the persisted gateway output. Case files concatenate exactly to the frozen raw JSONL.
- All 90 predictions were replayed through the unchanged deterministic pipeline using stored responses at threshold 0.86. Candidate/final route, rule, evidence validation, derived facts, score and abstention reason matched. Baseline predictions were independently reproduced byte for byte.
- Primary counts, all confusion entries, extraction-value diagnostics and Wilson intervals were independently recomputed from frozen gold. All critical errors and low-confidence cases are represented in error_analysis.json. Original 291 Phase 3A manifest entries and all four approved locks remain unchanged; frozen data and core match their historical commits.
- 94 offline tests and 180 blueprint cases passed in the execution workflow. No live evaluation ran in ordinary validation CI.
- Python 3.12's compensated float sum differs from Actions Python 3.11's sequential sum by less than 1e-12 for cost/latency aggregates. The original Actions results are retained unchanged. Currency figures below use the returned-cost sums, not a pricing estimate.

## Verified held-out results

| Metric | ReturnGuard | Keyword+Rules |
|---|---:|---:|
| Auto coverage | 57/90 (63.33%; Wilson 53.02–72.55%) | 26/90 (28.89%; Wilson 20.54–38.96%) |
| Selective accuracy | 57/57 (100%; Wilson 93.69–100%) | 25/26 (96.15%; Wilson 81.11–99.32%) |
| Final route accuracy | 87/90 (96.67%) | 54/90 (60%) |
| Manual-review recall | 30/30 | 29/30 |
| Gold-manual automatically routed | 0 | 1 |

ReturnGuard meets the predefined 90% selective-accuracy and 60% coverage targets. The baseline also meets the predefined selective-accuracy point-estimate constraint, allowing the locked comparison: coverage gain 34.44 percentage points, exceeding 10 pp. These are descriptive results on a small balanced synthetic benchmark, without significance or production-generalization claims. Threshold 0.86 remains provisional and was not changed.

ReturnGuard abstentions: 30 policy-required + 3 low-confidence + 0 validation + 0 execution = 33. Field accuracies: return_reason 87/90, tag_status 90/90, damage_or_stain 90/90, use_beyond_inspection 89/90; all four values exact 86/90. Candidate route 88/90; candidate rule 87/90. Final selective accuracy does not imply perfect extraction or perfect full-route accuracy.

## Descriptive case inspection

The frozen labels remain authoritative; these descriptions do not relabel cases or alter metrics. No model judge was used as an authoritative labeler.

| Case | Observed extraction or abstention | Consequence |
|---|---|---|
| test_024 | Correct ordinary reason, but score 0.76 for double-negation wording | Correct eligible candidate withheld; low-confidence false alarm |
| test_045 | Correct ordinary reason, but score 0.84 for double-negation wording | Correct ineligible candidate withheld; low-confidence false alarm |
| test_060 | Packaging-box dent selected as quality issue instead of stated sizing reason | MR01_QUALITY replaces gold IN03_NOT_INTACT; policy over-abstention |
| test_071 | Explicit inspection-only use classified unknown | Route/rule remain gold MR03_REASON; field error without route error |
| test_079 | Bare return request treated as ordinary reason instead of not_stated; score 0.82 | Wrong eligible candidate withheld; gold manual route preserved |
| test_087 | Condition stain/conflict treated as a quality return reason rather than stated style reason | Manual route remains correct but MR01_QUALITY replaces gold MR02_CONDITION |

There is one validation-passed automatic candidate error (test_079), captured by low-confidence abstention: error capture 1/1. This denominator is too small to establish general error-ranking performance. Two other low-confidence abstentions withheld correct candidates. Policy manual errors are outside that predefined error-capture denominator.

The baseline's sole automatic error is test_087: it detects a positive stain phrase but misses the simultaneously asserted contradictory condition evidence and emits ineligible rather than manual review. This is retained as the locked baseline's observed result; no pattern changes or replacement operating point were introduced.

## Cost and closure

Test: 91,731 input + 16,864 output tokens; directly returned cost USD 0.04014795. Dev+test: 183,421 input + 32,232 output tokens; USD 0.07849060. All 180 content responses expose returned cost. Returned model is openai/gpt-5.6-luna; upstream provider is not exposed, and the alias does not identify an immutable upstream model revision.

README, course final report, dataset documentation, demo, frozen benchmark, raw DeepSeek generation artifacts and review provenance remain unchanged. The instructor's latest deliverable clarification is reserved for the next reporting phase. No further test execution is authorized by this package.
