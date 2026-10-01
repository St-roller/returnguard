# Phase 3A development evaluation handoff

Status: **DEV_COMPLETE_PENDING_GATE_3A_APPROVAL**. Only the frozen development split was evaluated. No held-out test inference, scoring, baseline test outputs or test authorization exist. Stop at Gate 3A for design approval.

Authority: `docs/ReturnGuard_Phase3_Formal_Evaluation_Specification_v1.0.md`, particularly §33. Branch `phase3-evaluation-v1` originates at `35ea848b2da3d0b1a6245d18edb33f5dcf49e708`. Frozen dataset snapshot `6bc97f310cffef6b62c32e473455bb7c60766479521d6d1d96758db94681977a` and all committed freeze bytes were verified before live calls.

## Locked experiment provenance

Gateway OpenRouter; requested model `openai/gpt-5.6-luna`; returned identities `['openai/gpt-5.6-luna']`. Prompt `extraction_v1`, strict `Extraction.model_json_schema()`, tools `[]`. Temperature/top_p/seed omitted. Cases processed in ascending case_id order with independent requests; only customer_message sent to the model. Trusted order facts enter deterministic Policy v1 after extraction. No prompt, core policy/schema/acceptance or dataset changes.

Configuration, baseline patterns, baseline lock and input-only dev projection were committed before the first dev call. `dev_run_start.json` binds that commit and the configuration/lock hashes. Every attempt has a started/outcome record; gateway responses were persisted before parsing, validation or gold scoring. Predictions were finalized and SHA-256 recorded in `dev_prediction_freeze.json` before the separate gold join. SDK automatic retries disabled; only infrastructure retries up to three attempts; no content resampling. On ambiguous in-flight requests resume hard-stops.

Model request attempts: **90**. Processed cases: **90**. Content responses: **90**. Validated/completed cases: **90**. Execution failures: **0**. Hard validation failures: **0**. Evidence-valid cases: **90**. All failures remain in N=90.

## Extraction and candidate diagnostics

| Metric | Raw count and percentage |
|---|---|
| return_reason value accuracy | 88/90 (97.78%) |
| tag_status value accuracy | 90/90 (100.00%) |
| damage_or_stain value accuracy | 90/90 (100.00%) |
| use_beyond_inspection value accuracy | 88/90 (97.78%) |
| All-four exact values | 86/90 (95.56%) |
| Candidate route accuracy | 87/90 (96.67%) |
| Candidate rule-ID accuracy | 87/90 (96.67%) |

Candidate policy-required manual: 33; candidate auto routes: 57. Missing candidates are not scored as correct. Value diagnostics use raw parsed values; hard-validation failures are reported separately. Exact evidence equality to gold is not an accuracy criterion.

## Dev support-score diagnostic

Only auto-route candidates; descriptive ranking, not calibration or probability.

| Score bin | n | Candidate errors | Error rate |
|---|---:|---:|---:|
| <0.50 | 0 | 0 | N/A |
| 0.50–0.69 | 0 | 0 | N/A |
| 0.70–0.89 | 1 | 0 | 0.00% |
| 0.90–1.00 | 56 | 0 | 0.00% |

Median scores: correct 0.96; incorrect None. Range 0.86–0.99; unique scores 10; correctness AUROC None. No confidence model was fitted.

## Provisional operating point

A provisional acceptance threshold **0.86** was selected on the 90-case development split by maximizing coverage subject to at least 90% selective accuracy, then locked before held-out evaluation. Acceptance is `score >= threshold`, without epsilon; ties resolve by higher accuracy and then higher threshold. The full unique-score table is in `dev_threshold_table.json`. Candidate collection at 0.0 is not the operating result.

- Coverage: 57/90 (63.33%; descriptive Wilson 95% 53.02–72.55%).
- Selective accuracy: 57/57 (100.00%; descriptive Wilson 95% 93.69–100.00%).
- Manual-review recall: 30/30 (100.00%; descriptive Wilson 95% 88.65–100.00%).
- Three-class route accuracy: 87/90 (96.67%; descriptive Wilson 95% 90.65–98.86%).

Dev 60% coverage target: met (separate from threshold selection). Gold-manual cases auto-routed: 0. Error capture: N/A; definition excludes policy/validation/execution abstentions from forced-choice candidates.

Dev Wilson intervals are descriptive and optimistic because the threshold was selected on the same dev data. The threshold is provisional, not production-calibrated. No held-out success or project success is claimed.

Abstention decomposition (count / 90):

- policy_required: 33/90 (36.67%).
- low_confidence: 0/90 (0.00%).
- validation_failure: 0/90 (0.00%).
- execution_failure: 0/90 (0.00%).

Final confusion matrix (gold rows, predicted columns):

| Gold | eligible | ineligible | manual_review |
|---|---:|---:|---:|
| eligible | 29 | 0 | 1 |
| ineligible | 0 | 28 | 2 |
| manual_review | 0 | 0 | 30 |

## Locked Keyword+Rules dev baseline

One conservative deterministic operating point, no confidence score or threshold, exact-span evidence validator, unchanged Policy v1. Patterns come from the specification; no test-aware or LLM-aware tuning.

- Coverage: 24/90 (26.67%; descriptive Wilson 95% 18.62–36.62%).
- Selective accuracy: 24/24 (100.00%; descriptive Wilson 95% 86.20–100.00%).
- Route accuracy: 54/90 (60.00%; descriptive Wilson 95% 49.67–69.51%).
- Manual recall: 30/30 (100.00%; descriptive Wilson 95% 88.65–100.00%).

Baseline gold-manual auto-routed: 0; abstentions {"policy_required": {"n": 66, "rate": 0.7333333333333333}, "low_confidence": {"n": 0, "rate": 0.0}, "validation_failure": {"n": 0, "rate": 0.0}, "execution_failure": {"n": 0, "rate": 0.0}}. Full confusion matrix and diagnostics are in `baseline_dev_metrics.json`. This is dev only; the predefined held-out comparison rule is reserved for Phase 3B.

## Usage and reproducibility

Reported input/output tokens: 91690/15368 (available for 90/90). Reported API cost USD: 0.03834265000000001 (available for 90/90; complete=True). No fresh pricing estimate substituted. Provider metadata, where exposed: []. Model identity is an alias and does not prove an immutable underlying revision. Dependency versions are recorded in the pre-call config.

All raw/scored predictions, attempts, locks and metrics are in `results/phase3/`. `phase3a_artifact_hashes.json` lists exact SHA-256 values. Key hashes:

- `eval_config_v1.json`: `164ad582216ccb7a571f179eb7622e8274ff2e2506f9aefff668a4992ac5eddf`
- `baseline_lock_v1.json`: `63aacdbd263cae2c8a597401c60189d9c3e7b66b87faf01976e8c33f104bb2cf`
- `dev_inputs.jsonl`: `844f1f0f180d2cbae29f281ca828a1cb0ff10e319f772ca666e0d16d10217e3a`
- `dev_predictions_raw.jsonl`: `e0e880c011ce2a346bf604e644570d04bed2658f5b7e2c8a1fc7e4a16a77b764`
- `dev_predictions_scored.jsonl`: `47a882922a2bcb04428a0213e6f3b139fd7fa28fe2cb649885709a1543e2e127`
- `threshold_lock_v1.json`: `8be8a8084d288561c2e939631e03edfd78dd7fd3a05373a92d36ec6ce18b9e93`

## Gate 3A review

Verify run provenance, immutable config/prompt/baseline, support diagnostic, complete threshold table, provisional threshold lock, counts/metrics and absence of test outputs. Work has stopped here. No test_authorization.json is created by Phase 3A. The test runner requires explicit matching authorization before a model call.
