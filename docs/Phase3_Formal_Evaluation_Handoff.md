# ReturnGuard Phase 3 formal evaluation handoff

Status: **PHASE_3_FORMAL_EVALUATION_CLOSED — TEST_COMPLETE**. This is the formal evaluation handoff, not a rewrite of the course final report, README, dataset documentation or demo. Those materials remain deferred under the latest user instruction.

The 90-case held-out split was evaluated once under the locked model, prompt, policy, schema, acceptance aggregation and threshold. Gate 3A was explicitly approved by the user on 1 October 2026. `test_authorization.json` binds the four approved hashes and threshold 0.86; `test_run_start.json` binds the execution commit, run ID and dependency versions. `test_scoring_start.json` records the finalized raw prediction hash before gold joining.

A provisional acceptance threshold was selected on the 90-case development split by maximizing coverage subject to at least 90% selective accuracy, then locked before held-out evaluation. The threshold remains **0.86**, acceptance `score >= threshold`, without epsilon. No threshold selection was performed on test.

Gateway OpenRouter; model `openai/gpt-5.6-luna`; exact `extraction_v1` prompt hash `3c2d740f12bf2f80b69caea30672b5970d162b0ea93c3410c219b5dde49ce4c8`. Strict extraction schema; tools `[]`; temperature/top_p/seed omitted. Ascending case_id, independent requests, model receives Chinese customer_message only. Trusted order facts enter deterministic code after extraction. Input projections contain no gold/English/review/design metadata. Only infrastructure failures are retried, at most 3 attempts; content/validation failures never trigger resampling. Every attempt and raw gateway response is retained before parsing/scoring. Completed content responses are immutable.

## Test operating point and targets

Raw counts are reported alongside percentages because the development and held-out samples are small. Wilson 95% intervals are descriptive, not significance tests. Dev intervals remain optimistic with respect to threshold selection on the same data.

| Test metric | ReturnGuard | Locked Keyword+Rules |
|---|---|---|
| Coverage | 57/90 (63.33%; Wilson 95% 53.02–72.55%) | 26/90 (28.89%; Wilson 95% 20.54–38.96%) |
| Selective accuracy | 57/57 (100.00%; Wilson 95% 93.69–100.00%) | 25/26 (96.15%; Wilson 95% 81.11–99.32%) |
| Three-class route accuracy | 87/90 (96.67%; Wilson 95% 90.65–98.86%) | 54/90 (60.00%; Wilson 95% 49.67–69.51%) |
| Manual-review recall | 30/30 (100.00%; Wilson 95% 88.65–100.00%) | 29/30 (96.67%; Wilson 95% 83.33–99.41%) |

Gold-manual cases auto-routed: ReturnGuard **0**, baseline **1**. Error capture: **1/1** (captured low-confidence candidate errors / all validation-passed, execution-completed auto-candidate errors; policy/validation/execution abstentions are not forced through).

- 90% selective-accuracy constraint: **met**.
- 60% held-out coverage target: **met**.

The Keyword+Rules baseline met the 90% selective-accuracy constraint; coverage was therefore compared at the predefined safety requirement. ReturnGuard also met the safety constraint.

Coverage difference: **34.44 percentage points**. Coverage gap >=10 pp: True; combined safe coverage gain target: True. A safe comparison also requires ReturnGuard to meet the safety constraint.

Abstention decomposition (counts / 90):

| Reason | ReturnGuard | Keyword+Rules |
|---|---:|---:|
| policy_required | 30/90 (33.33%) | 64/90 (71.11%) |
| low_confidence | 3/90 (3.33%) | 0/90 (0.00%) |
| validation_failure | 0/90 (0.00%) | 0/90 (0.00%) |
| execution_failure | 0/90 (0.00%) | 0/90 (0.00%) |

ReturnGuard final confusion matrix (gold rows, final columns):

| Gold | eligible | ineligible | manual_review |
|---|---:|---:|---:|
| eligible | 29 | 0 | 1 |
| ineligible | 0 | 28 | 2 |
| manual_review | 0 | 0 | 30 |

Keyword+Rules final confusion matrix (gold rows, final columns):

| Gold | eligible | ineligible | manual_review |
|---|---:|---:|---:|
| eligible | 4 | 0 | 26 |
| ineligible | 0 | 21 | 9 |
| manual_review | 0 | 1 | 29 |

## Extraction and candidate diagnostics

| Metric | Count / 90 |
|---|---|
| return_reason value accuracy | 87/90 (96.67%) |
| tag_status value accuracy | 90/90 (100.00%) |
| damage_or_stain value accuracy | 90/90 (100.00%) |
| use_beyond_inspection value accuracy | 89/90 (98.89%) |
| All-four values exact | 86/90 (95.56%) |
| Candidate route accuracy | 88/90 (97.78%) |
| Candidate rule-ID accuracy | 87/90 (96.67%) |

Evidence-valid cases 90/90; hard validation failures 0/90; execution failures 0/90. Candidate auto routes 60; candidate policy manual routes 30. Missing candidates do not count as correct. Exact gold evidence equality is not a primary accuracy metric.

Support scores were treated as model self-assessments for ranking and abstention, not as calibrated probabilities. The support-score diagnostic and threshold table were dev-only and remain unchanged. See `dev_support_score_diagnostic.json` and `dev_threshold_table.json`; no test confidence fitting or test threshold enumeration occurred.

## Descriptive error analysis

All automatic-routing errors, validation failures, execution failures, unsafe gold-manual auto routes, extraction-value mismatches and over-abstentions are captured in `error_analysis.json`, with exact Chinese input, predicted/gold values and evidence, route/rule consequences and deterministic category labels. Low-confidence sample selection is the first five ascending IDs; field representatives are the first three mismatches per field. No LLM judge was used as authoritative labeler.

- auto_routing_error_ids: 0; none.
- validation_failure_ids: 0; none.
- execution_failure_ids: 0; none.
- gold_manual_auto_routed_ids: 0; none.
- over_abstention_ids: 3; test_024, test_045, test_060.
- field_value_error_ids: 4; test_060, test_071, test_079, test_087.
- low_confidence_sample_ids: 3; test_024, test_045, test_079.

No benchmark repair, label change, prompt change, baseline tuning, response resampling or threshold retuning occurred after observing test. Descriptive explanations do not change metrics.

## Usage and reproducibility

| Split | Request attempts | Content responses | Input tokens | Output tokens | Reported response cost USD |
|---|---:|---:|---:|---:|---:|
| dev | 90 | 90 | 91690 | 15368 | 0.03834265 |
| test | 90 | 90 | 91731 | 16864 | 0.04014795 |
| total | 180 | 180 | 183421 | 32232 | 0.07849060 |

Test infrastructure retries 0; validation failures 0; execution failures 0. Test cost available for 90 content responses; full returned-cost coverage=True. Failed infrastructure attempts without billing metadata have unknown cost. No fresh pricing estimate is substituted.

Returned model identities: ['openai/gpt-5.6-luna']; exposed upstream providers: unavailable. The alias does not establish an immutable underlying revision.

Dev remains: coverage 57/90 (63.33%; Wilson 95% 53.02–72.55%), selective accuracy 57/57 (100.00%; Wilson 95% 93.69–100.00%), manual recall 30/30 (100.00%; Wilson 95% 88.65–100.00%). Original Phase 3A predictions, metrics, locks, handoff and package hashes are preserved verbatim as historical Gate 3A records.

Key hashes:

- `eval_config_v1.json`: `164ad582216ccb7a571f179eb7622e8274ff2e2506f9aefff668a4992ac5eddf`
- `threshold_lock_v1.json`: `8be8a8084d288561c2e939631e03edfd78dd7fd3a05373a92d36ec6ce18b9e93`
- `baseline_lock_v1.json`: `63aacdbd263cae2c8a597401c60189d9c3e7b66b87faf01976e8c33f104bb2cf`
- `test_authorization.json`: `4997f79d60207ae8a81b9fe015342aa3947929c30c98038eed20e61bf14d53a5`
- `phase3b_scorer_lock.json`: `cbbdc8f8f367dc422cb6ae7decd433a0c998c9e70aebddcd1470c897c1e38a1f`
- `dev_inputs.jsonl`: `844f1f0f180d2cbae29f281ca828a1cb0ff10e319f772ca666e0d16d10217e3a`
- `test_inputs.jsonl`: `d68d5b0ad0a0a59fd4b2f4cb657d685086285777844df850422974a6a91c90ef`
- `dev_predictions_raw.jsonl`: `e0e880c011ce2a346bf604e644570d04bed2658f5b7e2c8a1fc7e4a16a77b764`
- `dev_predictions_scored.jsonl`: `47a882922a2bcb04428a0213e6f3b139fd7fa28fe2cb649885709a1543e2e127`
- `test_predictions_raw.jsonl`: `ab157376bb1df7cf8980489c5690042bb922f4df0ad3bf078ff34dbee6509b69`
- `test_predictions_scored.jsonl`: `92d60e551c068abb393ee814fd60a23fe0428895f82e5969c0b81bb63e34a1c9`
- `baseline_dev_predictions.jsonl`: `bcdeacd4fe002b6f467a5910a532b98d4719a732e6474b7e620344af86037725`
- `baseline_test_predictions.jsonl`: `65ba0a19c61f518b799d30aee273af6a4a74dea17afc9401ce97157ee224fc4e`
- `dev_metrics.json`: `69afa91e070a2c430424cd5598d6dc4db0147a21431186e23c78e50d008ae74f`
- `test_metrics.json`: `1025a7e9eb4a44d53b21966d6ea600dbf553191188e747804b5c5af4d7941157`
- `baseline_dev_metrics.json`: `5ac21969d852a15d4822c029a8032bfdb523e764295a1140eca8ecb7ecba731b`
- `baseline_test_metrics.json`: `334cb7d668ae6e16c51fab51e45846d869cfcdb6ec7b11178e0f2bc90a6dca81`
- `error_analysis.json`: `e6233dafa05617bdc76e17526d4c2a6f36e2955a1cadd7bc30b8e8b59d27d8ab`

`phase3_summary.json` contains all dev/test/baseline counts, metrics, target outcomes, uncertainty, abstentions, error capture and separate/total usage. Raw case/attempt files remain available in `results/phase3/`. Scoring/source/projection/authorization hashes are verified against their committed pre-test locks.

## Closure

Gate 3B: TEST_COMPLETE. Formal evaluation has stopped. No final report, README, dataset documentation or demo material is updated in this phase. Instructor deliverable clarification remains deferred to the subsequent reporting task.
