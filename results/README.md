# Closed formal evaluation

Phase 3 is complete, approved and immutable. Held-out test was evaluated once under the dev-locked configuration and **provisional threshold 0.86**. This directory holds recorded evidence; the TA path verifies/replays stored artifacts without model calls or result rewrites.

## Evaluated contract

| Component | Locked value |
|---|---|
| Gateway / model | OpenRouter / `openai/gpt-5.6-luna` |
| Prompt / schema | [extraction_v1](../prompts/extraction_v1.md), strict four-field extraction JSON; `case_v1.0` data contract |
| Policy / acceptance | [policy_v1.0](../policies/policy_v1.json), `acceptance_v1.0` rule-specific aggregation |
| Sampling / tools | Temperature, top_p and seed omitted; tools `[]` |
| Requests | Independent ascending case IDs; one content response per case; infrastructure-only retries capped at 3; no content/validation retry |
| Comparator | Locked `keyword_rules_v1.0`, conservative regex extraction plus the same Policy v1 |

The model receives only Chinese text. Trusted order facts go to code. [eval_config_v1.json](phase3/eval_config_v1.json) binds dataset/prompt/schema/source/dependency hashes; [baseline_lock_v1.json](phase3/baseline_lock_v1.json) binds baseline patterns/code. Returned model identity matched the alias, but upstream provider and immutable underlying revision were not exposed.

## Dev-only selection and held-out protection

The full threshold table used 90 frozen dev cases. Selection maximized coverage subject to selective accuracy >=90%; ties preferred higher accuracy, then higher threshold. The selected point accepted 57/90 with 57/57 correct. **0.86** was locked before test, with `score >= threshold` and no epsilon. Policy-required manual routes bypass the threshold. This is provisional, not production-calibrated confidence.

Test required explicit authorization matching the frozen test hash, config, threshold and baseline locks. Its 90 input-only cases used those same locks. Attempt/response records were persisted before parsing; complete raw predictions were frozen and hashed before gold joining. Test had 90 requests/content responses, zero retries, zero validation failures and zero execution failures. Completed responses were not resampled. Test observations did not change data, prompt, model, aggregation, policy, schema, baseline or threshold.

See [threshold table](phase3/dev_threshold_table.json), [support diagnostic](phase3/dev_support_score_diagnostic.json), [threshold lock](phase3/threshold_lock_v1.json), [test authorization](phase3/test_authorization.json), [prediction freeze](phase3/test_prediction_freeze.json) and [scoring start](phase3/test_scoring_start.json). Dev-selected intervals are optimistic with respect to selection on those same cases. Old dev-pending fields are historical provenance, not current status.

## Metric definitions

| Metric | Definition |
|---|---|
| Coverage | Final eligible/ineligible automatic routes / all 90 cases |
| Selective accuracy | Automatic cases matching the gold route / all automatic cases |
| Manual-review recall | Gold manual cases finally sent to manual_review / all 30 gold manual cases |
| Final route accuracy | Correct final routes across all three classes / all 90 cases |
| Gold-manual automatic count | Gold manual cases sent to eligible/ineligible |
| Error capture | Erroneous valid automatic **candidates** withheld by low confidence / all erroneous valid automatic candidates; N/A at zero denominator |

Policy-required, low-confidence, validation-failure and execution-failure abstentions are separate. Failures stay in all-case denominators. Error capture excludes policy-required manual candidates and validation/execution failures. Field diagnostics compare values, not exact equality with one gold evidence-span choice. Definitions are in locked [eval_metrics.py](../src/returnguard/eval_metrics.py).

## Frozen held-out results and targets

| Metric | ReturnGuard | Locked Keyword+Rules |
|---|---:|---:|
| Coverage | 57/90 (63.33%) | 26/90 (28.89%) |
| Selective accuracy | 57/57 (100%) | 25/26 (96.15%) |
| Manual-review recall | 30/30 (100%) | 29/30 (96.67%) |
| Final route accuracy | 87/90 (96.67%) | 54/90 (60%) |
| Gold-manual automatic count | 0 | 1 |

Both meet the predefined **point-estimate** selective-accuracy requirement of >=90%, permitting the fixed-point comparison. Safe coverage gain is **+34.44 percentage points**. The >=90% selective accuracy, >=60% coverage and >=10 pp safe gain targets were met. No post-hoc baseline point, confidence score or threshold was introduced.

Keyword+Rules uses fixed conservative patterns for values/evidence and the same policy. Missing/ambiguous matches often cause review. It has no LLM call or confidence threshold. Its automatic error on `test_087` misses the condition conflict and emits ineligible instead of manual review; 96.15% selective accuracy does not mean every gold-manual case was handled safely.

ReturnGuard abstentions: 30 policy-required + 3 low-confidence + 0 validation + 0 execution. Field accuracies: reason 87/90, tag 90/90, damage/stain 90/90, use 89/90; all four exact 86/90. Candidate route accuracy was 88/90 and rule-ID accuracy 87/90. Full matrices/diagnostics are in [test_metrics.json](phase3/test_metrics.json) and [baseline_test_metrics.json](phase3/baseline_test_metrics.json).

## Uncertainty and support-score caveats

| Descriptive Wilson 95% interval | ReturnGuard | Keyword+Rules |
|---|---:|---:|
| Coverage | 53.02–72.55% | 20.54–38.96% |
| Selective accuracy | 93.69–100% | 81.11–99.32% |
| Manual-review recall | 88.65–100% | 83.33–99.41% |

The benchmark is **small, balanced and synthetic**, not real customer traffic. Intervals are descriptive; the gap is not a significance test or production-superiority claim. Targets use point estimates; the baseline interval's lower bound is below 90%.

Support scores are self-assessments for ranking/abstention, not probabilities. Dev had no erroneous automatic candidates, so error capture/correctness AUROC were unavailable. Test caught one erroneous automatic candidate (`test_079`): **1/1** error capture. Two correct candidates (`test_024`, `test_045`) were also withheld. A denominator of one provides limited evidence for general error ranking. [Error analysis](phase3/error_analysis.json) retains all critical errors and representative field failures without label changes or an authoritative LLM judge.

## Usage and reproducibility artifacts

| Split | Requests | Input / output tokens | Directly reported cost USD |
|---|---:|---:|---:|
| Dev | 90 | 91,690 / 15,368 | 0.03834265 |
| Test | 90 | 91,731 / 16,864 | 0.04014795 |
| Total | 180 | 183,421 / 32,232 | 0.07849060 |

All 180 responses exposed cost. These are recorded costs, not fresh price estimates. Per-case token counts, latency and costs remain available. See [phase3_summary.json](phase3/phase3_summary.json) and [test usage](phase3/test_usage_summary.json).

| Artifact | Audit purpose |
|---|---|
| `dev_inputs.jsonl`, `test_inputs.jsonl` | Input-only projections; [data explainer](../data/README.md) identifies frozen gold |
| `*_predictions_raw.jsonl`, `*_cases/`, `*_attempts/` | Structured outputs, routing/support and sanitized request audit |
| `*_predictions_scored.jsonl`, `*_metrics.json` | Gold joins, counts, matrices and diagnostics |
| `baseline_*_predictions.jsonl`, `baseline_*_metrics.json` | Unchanged comparator outputs/results |
| `eval_config_v1.json`, `threshold_lock_v1.json`, `baseline_lock_v1.json` | Experiment identity and locked operating points |
| `*_run_start.json`, `test_authorization.json`, `test_scoring_start.json` | Execution, authorization and raw-before-gold provenance |
| [public_artifact_manifest.json](phase3/public_artifact_manifest.json) | SHA-256 of current sanitized public artifacts |
| [sanitization_equivalence_v1.json](phase3/sanitization_equivalence_v1.json) | Equivalence and original/public hash mapping |
| [formal handoff](../docs/Phase3_Formal_Evaluation_Handoff.md), [verification notes](../docs/Phase3B_Verification_Notes.md) | Closed experiment and independent checks |

Provider envelopes omit reasoning/encrypted payloads and opaque metadata; response IDs are deterministic hashes. Structured outputs/evaluation fields remain. Original freeze/package/summary hashes refer to private original bytes; the public manifest hashes sanitized current bytes. History and earlier Actions artifacts were not rewritten/deleted. [Publication notes](../docs/Phase3_Publication_Sanitization.md) explain this distinction.

Run `python scripts/sanitize_phase3_public.py verify-public` from the repository root to validate existing hashes without API calls or writes. The [TA quick start](../README.md#ta-quick-start-offline-no-api-key) covers setup, fixture tests and recorded-case replay. Historical inference/scoring scripts are provenance tools; do not use them to redo the closed experiment or select another threshold.
