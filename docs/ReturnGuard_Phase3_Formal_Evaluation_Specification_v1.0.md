# ReturnGuard Phase 3 Formal Evaluation Specification v1.0

**Project:** PE6201 End-of-Course Project — ReturnGuard  
**Phase:** 3 — Formal Evaluation  
**Status:** Design-frozen implementation specification  
**Date:** 2026-10-01  
**Repository:** `St-roller/returnguard`  
**Phase 3 branch:** `phase3-evaluation-v1`  
**Branch point:** merged `main` at PR #3 merge commit `35ea848b2da3d0b1a6245d18edb33f5dcf49e708`

---

# 1. Purpose

Phase 3 measures ReturnGuard on the frozen `ReturnGuard-Synth-v1` benchmark without reopening dataset construction, policy design, extraction prompt design, or acceptance semantics.

The formal sequence is:

```text
frozen dev
    ↓
one GPT-5.6 Luna extraction call per case
    ↓
candidate routes + support scores
    ↓
dev-only support-score diagnostic
    ↓
dev-only provisional threshold selection
    ↓
lock threshold + baseline
    ↓
GATE 3A: stop and return dev package
    ↓
explicit locked-test authorization
    ↓
frozen held-out test
    ↓
same locked threshold
    ↓
same locked Keyword+Rules baseline
    ↓
final metrics + error analysis
```

The held-out test split must remain untouched by model/prompt/threshold/baseline tuning.

---

# 2. Immutable starting point

## 2.1 Frozen benchmark

Dataset:

```text
ReturnGuard-Synth-v1
```

Freeze data commit:

```text
28095bd3c9f407d15eca4fe28a4d6e2775b9fffb
```

Freeze manifest commit:

```text
6531604a4d4347d40e89ec2ded6fc63da13c9383
```

Source blueprint commit:

```text
c2af09ffb1346c91a8d6cb4783d827c24c6704bd
```

Frozen files:

```text
data/returnguard_synth_v1/dev.jsonl
data/returnguard_synth_v1/test.jsonl
data/returnguard_synth_v1/freeze_manifest.json
```

Frozen sizes:

```text
dev_n = 90
test_n = 90
```

Frozen hashes:

```text
dev_sha256 =
39943bdf053298dc3a9e6c45b58d6b6d06fb136fc1e5c30519b5de62e6c14c70

test_sha256 =
9b3fe0451253d089923c42ca5071684ad3c9d1d5ce3ab6814a0af9bc9a511933
```

Schema:

```text
case_v1.0
```

Policy:

```text
policy_v1.0
```

The Phase 3 runner must verify these hashes against `freeze_manifest.json` before any formal model call.

A mismatch is a hard stop.

## 2.2 No dataset edits

During Phase 3:

```text
dev.jsonl          immutable
test.jsonl         immutable
audit_report.json  immutable
structured_reviews immutable
Policy v1          immutable
Schema v1          immutable
```

Do not repair, relabel, paraphrase, or remove a case after formal evaluation begins.

---

# 3. Evaluation questions

Phase 3 answers five questions.

### Q1. Can the LLM-driven pipeline automatically route useful cases while maintaining the predefined safety constraint?

Primary operating constraint:

```text
selective accuracy >= 90%
```

Primary value metric:

```text
coverage
```

Project target:

```text
held-out coverage >= 60%
while held-out selective accuracy >= 90%
```

The 60% target is a success target, **not** a threshold-selection rule.

### Q2. Does the model's self-reported support score rank likely errors well enough to support abstention?

This is evaluated descriptively on dev only before test.

Do not call the score calibrated probability.

### Q3. How often does the system correctly preserve policy-required manual review?

Report manual-review recall and unsafe auto-routing of gold manual cases.

### Q4. How does ReturnGuard compare with a simple deterministic Keyword+Rules baseline?

The baseline uses the same trusted order facts and the same Policy v1 but no LLM.

### Q5. What failure modes remain?

Use deterministic metrics and direct case-level error analysis. No model judge is required.

---

# 4. Formal evaluated-model contract

## 4.1 Gateway and model

Use:

```text
gateway: OpenRouter
model_id: openai/gpt-5.6-luna
```

Do not switch to direct OpenAI during this experiment.

Do not substitute a different model or rolling alias.

If the gateway returns a different model identity indicating model substitution, stop the formal run and report the mismatch.

Upstream provider routing within OpenRouter may vary; record it if exposed by the response metadata.

## 4.2 Prompt

Use exactly:

```text
prompts/extraction_v1.md
prompt_version = extraction_v1
```

Compute and record the SHA-256 of the committed prompt before the dev run.

Do not edit the extraction prompt based on dev or test results.

If the prompt changes, it becomes a different experiment and requires a new versioned evaluation plan.

## 4.3 Structured-output schema

Use the existing strict structured-output schema:

```text
returnguard_extraction_v1
```

with:

```text
Extraction.model_json_schema()
strict = true
```

Expected fields:

```text
return_reason
tag_status
damage_or_stain
use_beyond_inspection
```

Each field contains:

```text
value
evidence[]
support_score
```

## 4.4 Request contract

Use the existing Responses-style request contract:

```text
system = extraction_v1 prompt
user = Chinese customer_message only
tools = []
structured JSON schema = strict
```

The model must **not** receive:

```text
case_id
split
trusted order facts
gold extraction
gold route
gold rule ID
review metadata
English annotation
difficulty
reason family
composition tags
blueprint metadata
threshold
```

Trusted order facts are used only by deterministic code after extraction.

## 4.5 Sampling parameters

For the formal evaluated model, send **no explicit**:

```text
temperature
top_p
seed
```

Reason: the existing Phase 1 extractor contract does not send them. Phase 3 must preserve that request contract rather than introduce a new unvalidated sampling configuration.

Record in provenance:

```text
temperature = omitted
top_p = omitted
seed = omitted
```

Do not misreport omitted parameters as zero.

## 4.6 Request ordering

Process formal cases in ascending `case_id` order.

Each case is an independent request.

No conversational state is shared across cases.

---

# 5. Infrastructure retry and execution-failure policy

Formal evaluation must distinguish infrastructure failure from model/content failure.

## 5.1 Retryable infrastructure errors

For transient infrastructure failures only:

```text
initial attempt + up to 2 retries
maximum = 3 request attempts per case
```

Retryable examples:

```text
connection failure
timeout
HTTP 429
HTTP 5xx
temporary gateway failure
```

Use the exact same model, prompt, customer message and request settings.

Do not alter content between retries.

Record every attempt.

## 5.2 Non-retryable failures

Do not retry for:

```text
valid response with wrong extraction
schema-invalid model output
invalid/non-verbatim evidence
model refusal represented as unusable content
content-quality concerns
wrong support score
wrong candidate route
```

These are performance outcomes, not reasons to resample.

No "try again for a better answer" behavior is permitted.

## 5.3 Exhausted infrastructure failure

If all 3 infrastructure attempts fail:

```text
evaluation_status = execution_failure
final_route = manual_review
```

Keep `execution_failure` as an **evaluation-level abstention category**.

Do not modify the frozen core `ReviewReason` enum merely to add this category.

Execution failures:

- stay in the denominator for coverage;
- are not counted as auto-routed cases;
- are reported separately;
- are not silently deleted.

---

# 6. Formal prediction record

For every case record at least:

```json
{
  "case_id": "dev_001",
  "split": "dev",
  "formal_run_id": "phase3_dev_v1_<run>",
  "dataset_version": "ReturnGuard-Synth-v1",
  "dataset_file_sha256": "...",
  "eval_config_version": "formal_eval_v1.0",
  "gateway": "OpenRouter",
  "model_id_requested": "openai/gpt-5.6-luna",
  "model_id_returned": "...",
  "upstream_provider": null,
  "prompt_version": "extraction_v1",
  "prompt_sha256": "...",
  "request_attempts": 1,
  "evaluation_status": "completed",
  "raw_structured_extraction": {},
  "validated_extraction": {},
  "derived_facts": {},
  "candidate_route": "eligible",
  "candidate_rule_id": "EL01_7DAY",
  "candidate_review_reason": null,
  "case_support_score": 0.94,
  "final_route": "eligible",
  "review_reason": null,
  "latency_seconds": 1.23,
  "token_usage": {
    "input_tokens": 0,
    "output_tokens": 0
  },
  "reported_usage_cost_usd": null,
  "timestamp": "ISO-8601"
}
```

Store raw structured model output before any metric scoring.

Do not put gold labels inside raw prediction records.

---

# 7. Gold isolation and scoring separation

Create deterministic input-only projections from the frozen files.

Recommended:

```text
results/phase3/dev_inputs.jsonl
results/phase3/test_inputs.jsonl
```

Each projection contains only:

```text
case_id
split
input.order_facts
input.customer_message
```

Hash the projections.

The inference runner must consume only the input projection.

The model still receives only `customer_message`; order facts remain deterministic-policy inputs.

Gold labels are joined only in a separate scoring step after prediction files are finalized.

For the held-out test run, this separation is mandatory.

---

# 8. Experiment configuration artifact

Before any formal dev call, create and commit:

```text
results/phase3/eval_config_v1.json
```

It must record:

```text
eval_config_version = formal_eval_v1.0
gateway = OpenRouter
model_id = openai/gpt-5.6-luna
prompt_version = extraction_v1
prompt_sha256
schema_version = case_v1.0
policy_version = policy_v1.0
acceptance_version = acceptance_v1.0
dataset_version = ReturnGuard-Synth-v1
freeze_data_commit = 28095bd...
freeze_manifest_commit = 6531604...
dev_sha256
test_sha256
temperature = omitted
top_p = omitted
seed = omitted
tools = []
retry_policy = infrastructure_only_max_3_attempts
case_order = ascending_case_id
```

Compute and record:

```text
eval_config_sha256
```

Do not change this file after the first formal dev call.

---

# 9. Phase 3A — formal dev inference

## 9.1 Branch

Create:

```text
phase3-evaluation-v1
```

from merged `main` at:

```text
35ea848b2da3d0b1a6245d18edb33f5dcf49e708
```

## 9.2 Preflight

Before live calls:

```text
python -m pytest -q
python scripts/generate_blueprints.py --check
verify freeze_manifest hashes
verify eval_config hash
verify prompt hash
verify baseline lock exists
verify dev input projection has 90 cases
verify test formal results do not exist
```

Preflight tests must make zero evaluated-model calls.

## 9.3 Candidate collection

Run the 90 frozen dev cases exactly once, subject only to the infrastructure retry policy.

The existing pipeline can be invoked at:

```text
threshold = 0.0
```

for candidate collection because this accepts every valid auto-route candidate while preserving:

```text
candidate_route
candidate_rule_id
case_support_score
```

Important:

```text
0.0 is NOT the selected operating threshold.
```

Do not report the `threshold=0.0` final routes as the formal operating result.

The selected operating point is computed offline from stored candidate scores.

## 9.4 No dev resampling

Once a case has produced a content response, that response is final for this formal dev run.

Do not recall the model because:

```text
the result is wrong
the support score is low
the output validates poorly
another answer might improve metrics
```

If a job is interrupted, resume from persisted case-level results and run only cases with no completed content response.

Do not overwrite completed formal predictions.

---

# 10. Dev diagnostic metrics before thresholding

Using stored dev predictions, compute:

```text
N = 90
```

Report raw counts first.

## 10.1 Extraction diagnostics

For each field:

```text
return_reason value accuracy
tag_status value accuracy
damage_or_stain value accuracy
use_beyond_inspection value accuracy
```

Also report:

```text
all-four-value exact case accuracy
hard validation failure count
evidence-valid case count
```

Do not use exact gold evidence-span equality as a primary metric because multiple different exact spans can validly support the same value.

## 10.2 Candidate policy diagnostics

Report:

```text
candidate route accuracy
candidate rule-ID accuracy
candidate policy-required manual count
candidate auto-route count
validation failure count
execution failure count
```

For candidate route accuracy, a missing candidate because of validation/execution failure is not silently treated as correct.

---

# 11. Dev support-score diagnostic

This is descriptive only.

It must not change the predefined threshold-selection algorithm.

Use auto-route candidate cases only.

Report score bins aligned with the extraction prompt:

```text
< 0.50
0.50–0.69
0.70–0.89
0.90–1.00
```

For each bin report:

```text
n
candidate-route errors
candidate-route error rate
```

Also report:

```text
median score for correct auto candidates
median score for incorrect auto candidates
min/max score
number of unique case scores
```

Optional:

```text
AUROC of support score vs candidate correctness
```

Only compute AUROC if both correct and incorrect candidate classes exist.

Do not call this calibration.

Do not fit Platt scaling, isotonic regression, or any second confidence model.

---

# 12. Provisional threshold selection — dev only

## 12.1 Eligible threshold cases

Threshold selection applies only to cases with:

```text
validation passed
execution completed
candidate_route in {eligible, ineligible}
case_support_score available
```

Policy-required manual cases bypass the threshold.

Validation/execution failures remain manual.

## 12.2 Candidate thresholds

Let:

```text
S = set of unique dev case_support_score values
```

Enumerate every unique value `t` in `S`.

For each `t`:

```text
accepted(t) =
auto candidate cases with score >= t
```

If:

```text
accepted_n(t) = 0
```

exclude that point from selection.

For every threshold compute:

```text
accepted_n
correct_accepted_n
coverage = accepted_n / 90
selective_accuracy = correct_accepted_n / accepted_n
low_confidence_abstain_n
```

Acceptance uses:

```text
score >= threshold
```

Do not add an epsilon.

## 12.3 Feasibility constraint

A threshold is feasible iff:

```text
accepted_n > 0
and
selective_accuracy >= 0.90
```

## 12.4 Selection rule

Among feasible thresholds:

1. maximize `accepted_n` / coverage;
2. tie-break by higher selective accuracy;
3. if still tied, choose the higher threshold.

The selected threshold is:

```text
provisional
```

not production-calibrated.

## 12.5 Project target

After selection, separately state whether dev coverage reaches:

```text
60%
```

Do not use 60% as a threshold-selection constraint.

## 12.6 No feasible threshold

If no non-empty threshold reaches 90% selective accuracy:

```text
STOP
status = NO_FEASIBLE_DEV_THRESHOLD
```

Do not invent a threshold.

Do not run the held-out test.

Return to design authority with the full dev threshold table.

---

# 13. Threshold lock artifact

If a feasible threshold exists, create:

```text
results/phase3/threshold_lock_v1.json
```

Minimum content:

```json
{
  "threshold_version": "threshold_v1.0",
  "status": "provisional_locked_from_dev",
  "value": 0.0,
  "selection_rule": "max coverage subject to selective_accuracy >= 0.90; tie higher accuracy; then higher threshold",
  "acceptance_rule": "score >= threshold",
  "dev_n": 90,
  "accepted_n": 0,
  "correct_accepted_n": 0,
  "selective_accuracy": 0.0,
  "coverage": 0.0,
  "dev_dataset_sha256": "...",
  "dev_predictions_sha256": "...",
  "eval_config_sha256": "...",
  "prompt_sha256": "...",
  "selector_version": "threshold_selector_v1.0",
  "created_at": "ISO-8601"
}
```

Also save the complete threshold table:

```text
results/phase3/dev_threshold_table.json
```

or CSV.

Once locked:

```text
threshold value cannot change
selection rule cannot change
prompt cannot change
model cannot change
acceptance aggregation cannot change
```

before held-out test evaluation.

---

# 14. Formal metrics at a locked operating point

For dev and later test, define:

```text
auto-routed =
final_route in {eligible, ineligible}
```

## 14.1 Coverage

```text
coverage =
auto_routed_n / N
```

## 14.2 Selective accuracy

```text
selective_accuracy =
correct_auto_n / auto_routed_n
```

where:

```text
correct_auto =
final_route == gold_route
```

A gold `manual_review` case that is auto-routed is an auto-routing error.

## 14.3 Overall three-class route accuracy

Secondary:

```text
route_accuracy =
count(final_route == gold_route) / N
```

Do not substitute this metric for the primary selective accuracy + coverage pair.

## 14.4 Manual-review recall

```text
manual_recall =
gold_manual_and_final_manual
/
gold_manual_n
```

Also report:

```text
gold_manual_auto_routed_n
```

This is an important unsafe-automation count.

## 14.5 Abstention decomposition

Partition manual outputs into:

```text
policy_required
low_confidence
validation_failure
execution_failure
```

Report count and rate for each.

## 14.6 Confusion matrix

Report a 3×3 final-route confusion matrix:

```text
gold eligible / ineligible / manual_review
vs
final eligible / ineligible / manual_review
```

---

# 15. Error-capture metric

Use the previously frozen forced-choice definition.

Ignore only the low-confidence threshold.

Do **not** bypass:

```text
policy_required manual review
validation failure
execution failure
```

Among validation-passed, execution-completed auto candidates:

```text
E =
cases where candidate_route != gold_route
```

```text
C =
cases in E where normal locked-threshold system sends the case to low_confidence
```

Then:

```text
error_capture_rate = |C| / |E|
```

If:

```text
|E| = 0
```

report:

```text
N/A
```

Do not redefine the denominator after seeing results.

---

# 16. Uncertainty reporting

Because dev/test each contain only 90 cases, report raw counts before percentages.

For proportions report descriptive **Wilson 95% intervals** for:

```text
coverage
selective accuracy
manual-review recall
```

On dev, explicitly note that the threshold was selected on the same dev data, so the dev interval is descriptive and optimistic with respect to selection.

Do not claim statistical significance from these small synthetic samples unless a separately justified analysis is added.

---

# 17. Keyword+Rules baseline — baseline_v1.0

The baseline must be locked **before the first formal dev model call**.

This prevents post-hoc creation of a weak or test-aware comparator.

Create:

```text
baselines/keyword_rules_v1.json
```

and record its SHA-256 in:

```text
results/phase3/baseline_lock_v1.json
```

The baseline may use:

```text
customer_message
trusted order facts
```

It must not use:

```text
gold labels
English annotation
review metadata
design tags
LLM outputs
test results
```

No support score is produced.

Do not invent numeric confidence.

## 17.1 Baseline extraction structure

Use a baseline-specific extraction structure:

```text
value
evidence[]
```

No `support_score`.

The baseline should derive the same four semantic values and then use the **same Policy v1**.

Do not change Policy v1 for the baseline.

## 17.2 Return reason

Priority:

```text
quality_or_fulfillment_issue
ordinary_return
not_stated
```

Quality/fulfillment pattern families include fixed expressions for:

```text
wrong item / sent wrong item
pre-existing damage on receipt
shipping/logistics damage
```

Recommended locked regex families include terms such as:

```text
发错
寄错
错发
不是我买的
不是我下单的
收到...破/坏/污/脏
到手...破/坏/污/脏
运输...破/损
物流...破/损
本来就...破/坏/脏
```

Ordinary-return pattern families include:

```text
尺码
尺寸
大小
颜色
款式
风格
不合适
不适合
不喜欢
不想要
不要了
不需要
用不上
买重
重复买
多出来
改主意
改变主意
不合我喜好
不是我想要
```

If a quality hit and ordinary hit both occur:

```text
quality_or_fulfillment_issue wins
```

matching the extraction prompt semantics.

If no quality or ordinary reason pattern matches:

```text
not_stated
evidence = []
```

Baseline v1.0 does not attempt a complex free-text `return_reason=conflicting` detector.

## 17.3 Tag status

Detect exact evidence for:

```text
attached
removed
unknown
conflicting
```

Removed pattern families include combinations of:

```text
吊牌/标签
+
剪掉/剪下/拆掉/拆下/摘掉/摘下/取下
```

Attached pattern families include combinations of:

```text
吊牌/标签
+
还在/仍在/挂着/连着/完整/没拆/没剪
```

If distinct attached and removed spans are both present:

```text
conflicting
```

If neither matches:

```text
unknown
```

Use explicit uncertainty evidence when a fixed uncertainty expression such as:

```text
不知道
不确定
记不清
不记得
说不清
```

occurs near `吊牌` or `标签`.

## 17.4 Damage/stain

Baseline must be conservative.

Absent should require an expression that covers both cleanliness and damage, for example pattern families equivalent to:

```text
没脏没破
没有污渍或破损
没有污渍和破损
无污渍无破损
没有弄脏也没有弄破
```

Do not infer `absent` from only:

```text
没有污渍
```

or only:

```text
没有破损
```

Present pattern families include explicit positive expressions such as:

```text
有污渍
弄脏
蹭脏
脏了
有破损
破了
坏了
有破洞
开线
损坏
```

When searching for positive presence, do not allow a positive token inside an already matched negated/absent span to become a false positive.

If distinct absent and present spans both remain:

```text
conflicting
```

Otherwise no match:

```text
unknown
```

Fixed uncertainty terms near damage/stain language may produce:

```text
unknown + uncertainty evidence
```

## 17.5 Use beyond inspection

No-use pattern families include:

```text
只试穿
仅试穿
只在家...试/穿
没穿出门
没有穿出门
未穿出门
只试了一下
只是试了试
```

Yes-use pattern families include:

```text
穿出门
穿出去
穿去上班
穿去逛街
穿了一整天
穿了一天
已经穿着...出门/上班/逛街
```

Important:

```text
"穿过" alone -> unknown
```

Do not let `穿出门` inside a negated phrase such as `没穿出门` become a positive match.

If distinct yes and no spans both remain:

```text
conflicting
```

Otherwise no match:

```text
unknown
```

## 17.6 Baseline evidence

All baseline evidence must be exact Chinese substrings.

The baseline must have its own deterministic evidence validator.

## 17.7 Baseline operating point

The baseline has **one conservative deterministic operating point**.

There is no synthetic confidence score and no threshold.

Its final route is the route obtained from:

```text
baseline extraction
→ derived facts
→ Policy v1
```

Validation failure goes to manual review.

---

# 18. Baseline metrics and comparison rule

Run the same metric definitions on baseline dev/test:

```text
coverage
selective accuracy
route accuracy
manual-review recall
abstention counts
confusion matrix
```

The primary comparison on held-out test is:

```text
ReturnGuard coverage
vs
Keyword+Rules coverage
```

at the safety requirement:

```text
selective accuracy >= 90%
```

## 18.1 If baseline meets 90%

If baseline held-out selective accuracy is at least 90%:

report:

```text
coverage difference in percentage points =
ReturnGuard coverage - baseline coverage
```

The proposal target is:

```text
ReturnGuard >= baseline + 10 percentage points
```

Report whether that target was met.

## 18.2 If baseline does not meet 90%

Do **not** pretend it has an equivalent safe operating point.

State:

> The Keyword+Rules baseline did not satisfy the predefined 90% selective-accuracy constraint at its conservative operating point.

Still report its raw coverage and accuracy descriptively.

Do not add a post-hoc baseline threshold.

## 18.3 Majority contextual baseline

Because each split has:

```text
30 eligible
30 ineligible
30 manual_review
```

the balanced three-class majority baseline route accuracy is:

```text
30 / 90 = 33.3%
```

This may be reported as context only.

It is not the primary business comparator.

---

# 19. Baseline lock artifact

Before the first formal dev model call create:

```text
results/phase3/baseline_lock_v1.json
```

Record:

```text
baseline_version = keyword_rules_v1.0
pattern_file_sha256
implementation_commit
policy_version
schema/value-space description
no_confidence_score = true
created_at
```

After formal dev inference begins:

```text
do not change baseline_v1.0
```

If a genuine implementation bug is discovered, stop and return to design authority before test.

---

# 20. Phase 3A output package

After the 90 formal dev calls and offline analysis, produce:

```text
results/phase3/eval_config_v1.json
results/phase3/dev_inputs.jsonl
results/phase3/dev_predictions_raw.jsonl
results/phase3/dev_predictions_scored.jsonl
results/phase3/dev_metrics.json
results/phase3/dev_support_score_diagnostic.json
results/phase3/dev_threshold_table.json
results/phase3/threshold_lock_v1.json
results/phase3/baseline_lock_v1.json
results/phase3/baseline_dev_predictions.jsonl
results/phase3/baseline_dev_metrics.json
docs/Phase3A_Dev_Evaluation_Handoff.md
```

The handoff must include:

```text
formal model request attempts
completed cases
execution failures
validation failures
field value accuracies
candidate route/rule accuracy
support-score diagnostic
selected provisional threshold
raw accepted/correct counts
dev coverage
dev selective accuracy
dev manual recall
dev abstention breakdown
dev error-capture rate
baseline dev metrics
API token usage
reported API cost if available
prediction/config hashes
```

At this point:

```text
STOP
```

Do not run held-out test.

---

# 21. Gate 3A — required before held-out test

The design-authority conversation must verify:

```text
dev run provenance
eval config
support-score diagnostic
threshold-selection table
threshold lock
baseline lock
dev metrics
no test outputs exist
```

Only after explicit approval may Work create:

```text
results/phase3/test_authorization.json
```

It should bind:

```text
decision = approved_for_locked_test
test_dataset_sha256
eval_config_sha256
threshold_lock_sha256
baseline_lock_sha256
locked_threshold_value
authorization timestamp/source
```

The test runner must refuse to run without this authorization artifact.

---

# 22. Phase 3B — held-out test inference

## 22.1 Preconditions

Before any test model call verify:

```text
test_sha256 =
9b3fe0451253d089923c42ca5071684ad3c9d1d5ce3ab6814a0af9bc9a511933

eval_config hash matches dev
prompt hash matches dev
model ID matches dev
threshold lock unchanged
baseline lock unchanged
test authorization matches all locks
```

Any mismatch is a hard stop.

## 22.2 Test inference

Run 90 frozen test cases exactly once under the same formal model contract and infrastructure retry policy.

Use the locked threshold:

```text
run_case(..., threshold=LOCKED_THRESHOLD)
```

Do not use test results to change:

```text
threshold
prompt
model
support-score aggregation
policy
schema
baseline patterns
retry policy
```

## 22.3 Test prediction immutability

Persist:

```text
results/phase3/test_predictions_raw.jsonl
```

and compute its SHA-256 before joining gold labels for scoring.

Completed content responses must not be overwritten.

---

# 23. Held-out test metrics

Report raw counts first.

Primary:

```text
auto_routed_n / 90
correct_auto_n / auto_routed_n
```

Then percentages:

```text
coverage
selective accuracy
```

Also report:

```text
Wilson 95% interval for coverage
Wilson 95% interval for selective accuracy
overall route accuracy
manual-review recall
gold-manual auto-routed count
policy-required manual count
low-confidence abstain count
validation-failure count
execution-failure count
error-capture rate
3×3 confusion matrix
field value accuracies
all-four-value exact accuracy
candidate route accuracy
candidate rule-ID accuracy
```

Report project outcomes explicitly:

```text
90% selective-accuracy constraint: met / not met
60% coverage target: met / not met
```

Do not reinterpret the targets after seeing test results.

---

# 24. Test baseline

Run the already locked `keyword_rules_v1.0` on the same frozen test inputs.

No pattern edits are allowed.

Persist:

```text
results/phase3/baseline_test_predictions.jsonl
results/phase3/baseline_test_metrics.json
```

Apply the comparison logic in Section 18 exactly.

---

# 25. Test error analysis

After all test metrics are computed, conduct descriptive error analysis.

This analysis may explain results but must not alter them.

Inspect:

```text
all auto-routing errors
all validation failures
all execution failures
gold-manual cases auto-routed
a sample of low-confidence abstentions
representative field extraction errors
```

Recommended error categories:

```text
return_reason extraction error
tag extraction error
damage/stain extraction error
use extraction error
evidence/validation failure
policy consequence of extraction error
unsafe automation of gold manual case
over-abstention / low-confidence false alarm
API execution failure
```

Do not use an LLM judge as the authoritative error labeler.

Do not repair the frozen benchmark after seeing errors.

---

# 26. Final Phase 3 artifacts

After Phase 3B create:

```text
results/phase3/test_predictions_raw.jsonl
results/phase3/test_predictions_scored.jsonl
results/phase3/test_metrics.json
results/phase3/baseline_test_predictions.jsonl
results/phase3/baseline_test_metrics.json
results/phase3/error_analysis.json
results/phase3/phase3_summary.json
docs/Phase3_Formal_Evaluation_Handoff.md
```

`phase3_summary.json` should contain at minimum:

```text
dataset hashes
eval config hash
model ID
prompt hash
threshold value/status
dev raw counts and metrics
test raw counts and metrics
baseline test metrics
coverage difference
target outcomes
abstention decomposition
error-capture result
execution failure counts
total token usage
reported API cost
prediction hashes
```

---

# 27. Reproducibility and cost reporting

Record per case where available:

```text
requested model ID
returned model ID
upstream provider
timestamp
request attempts
latency
input tokens
output tokens
reported usage cost
```

Aggregate separately for:

```text
dev
test
total
```

If OpenRouter returns a direct usage cost, sum the returned values.

If cost is unavailable:

```text
report unavailable
```

Do not silently substitute a fresh web pricing estimate into the formal experiment result.

The model alias may not expose an immutable underlying revision. State that limitation if applicable.

---

# 28. CI / workflow separation

Recommended workflows:

```text
.github/workflows/phase3-dev-eval.yml
.github/workflows/phase3-test-eval.yml
```

`phase3-dev-eval.yml` may access:

```text
dev inputs
OPENROUTER_API_KEY
```

It must not execute the test runner.

`phase3-test-eval.yml` must require:

```text
test_authorization.json
```

and verify every lock before live calls.

Both workflows should upload partial/result artifacts even on failure when possible.

A resume mechanism may continue missing cases, but must never resample completed content responses.

---

# 29. Required implementation tests before live evaluation

Add tests for at least:

```text
freeze hash mismatch hard-stops
model input excludes gold/English/case metadata
eval config becomes immutable after first formal call
retryable infrastructure error attempts <= 3
content/validation failure is not retried
completed prediction cannot be overwritten on resume
threshold table uses score >= t
threshold selection tie-breaking is deterministic
policy-required manual bypasses threshold
gold manual auto-route counts as selective error
execution failure stays in coverage denominator
error-capture denominator matches specification
Wilson interval implementation
baseline emits no confidence score
baseline evidence is verbatim
negated damage/use phrases do not become positive matches
baseline lock prevents test-time changes
test runner refuses to run without matching authorization
test scoring cannot alter threshold lock
```

Run:

```text
python -m pytest -q
```

before both live dev and live test workflows.

---

# 30. Prohibited actions

During Phase 3 do not:

```text
change frozen dataset text
change gold labels
change Policy v1
change Schema v1
change extraction_v1 after dev starts
change model after dev starts
sample multiple model answers and choose the best
retry content errors
delete difficult cases
drop execution failures from denominators
look at test results while selecting threshold
change threshold after seeing test
tune baseline on test
invent a baseline confidence score
report dev threshold as production-calibrated
claim support_score is a probability
claim 90% accuracy without raw counts
claim held-out success before the test run is complete
```

---

# 31. Gate logic

## Gate 3A — DEV COMPLETE

Pass when:

```text
90 dev cases processed
dev prediction file frozen
eval config frozen
baseline v1 frozen
support-score diagnostic complete
full threshold table complete
feasible provisional threshold locked
dev metrics reported with raw counts
no held-out test calls made
```

If there is no feasible threshold, Gate 3A does not pass and test remains blocked.

## Gate 3B — TEST COMPLETE

Pass when:

```text
90 test cases processed under locked config
locked threshold unchanged
baseline unchanged
test raw predictions frozen
test metrics complete
baseline test complete
error analysis complete
all result hashes recorded
no post-test retuning occurred
```

---

# 32. Reporting language

Use:

> A provisional acceptance threshold was selected on the 90-case development split by maximizing coverage subject to at least 90% selective accuracy, then locked before held-out evaluation.

Use:

> The 90-case held-out split was evaluated once under the locked model, prompt, policy, acceptance rule and threshold.

Use:

> Support scores were treated as model self-assessments for ranking and abstention, not as calibrated probabilities.

Use:

> Raw counts are reported alongside percentages because the development and held-out samples are small.

For the baseline, use one of:

> The Keyword+Rules baseline met the 90% selective-accuracy constraint; coverage was therefore compared at the predefined safety requirement.

or:

> The Keyword+Rules baseline did not meet the 90% selective-accuracy constraint at its conservative operating point, so its coverage is reported descriptively rather than treated as an equivalent safe comparator.

Do not use stronger wording than the observed results support.

---

# 33. Direct instruction to Work — Phase 3A

> Create `phase3-evaluation-v1` from merged main commit `35ea848b2da3d0b1a6245d18edb33f5dcf49e708`. Implement this specification without reopening the frozen dataset, Policy v1, Schema v1 or `extraction_v1`. Before any formal model call, verify the freeze hashes, commit `eval_config_v1.json`, and lock `keyword_rules_v1.0`. Run exactly the 90 frozen dev cases with `openai/gpt-5.6-luna` through OpenRouter, with no explicit temperature/top_p/seed, one content response per case, and infrastructure-only retries capped at 3 attempts. Persist candidate predictions, compute the predefined support-score diagnostic and complete threshold table, select the provisional threshold using the exact deterministic rule in Section 12, lock it, compute dev and baseline metrics, and return the Phase 3A package. Do not run the held-out test. Stop at Gate 3A for design approval.

---

# 34. Phase 3A completion claim

Before held-out authorization, Work may claim only:

> The frozen development split has been formally evaluated under the locked ReturnGuard extraction configuration, and a provisional acceptance threshold has been selected and locked using the predefined dev-only rule.

Work may not yet claim:

```text
held-out performance
final coverage
final selective accuracy
baseline superiority on test
project success target met
```

until Phase 3B is completed.
