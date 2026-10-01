# ReturnGuard

Phase 1 core for a Simplified Chinese apparel-return triage prototype. One model call extracts four facts and verbatim Chinese evidence. Deterministic code validates the extraction, derives item condition and calendar days, and applies the ordered rules in `policies/policy_v1.json`. The output is for human confirmation and takes no operational action.

## Run the Phase 1 tests

Python 3.11+ is required. From the repository root:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

On Windows, activate with `.venv\Scripts\activate` instead. The automated smoke tests use a fixture extractor to test the complete validation and routing path without an API key; they do **not** establish the live model's extraction accuracy.

## Run five live smoke inputs

Set `OPENAI_API_KEY` in your shell without committing it, then run:

```bash
python scripts/run_smoke.py
```

This makes one `gpt-5.6-luna` Responses API call per case and prints route, rule ID, review reason, score and whether the fixture's expected route and rule matched. A live failure remains a failure to investigate; the script does not edit the fixtures or policy. The actual model version, latency and token counts are in each in-memory prediction record. No API key is included in the repository.

For an OpenRouter key, set `OPENROUTER_API_KEY` instead and run `python scripts/run_smoke.py --provider openrouter`. This uses the OpenRouter model ID `openai/gpt-5.6-luna` through its OpenAI-compatible Responses endpoint. The five live calls will establish whether this gateway accepts the exact structured-output request and whether the model produces valid evidence; local fixture tests do not establish either result. Provider choice and model ID should be reported with any experiment.

To run without local key configuration, add a repository Actions secret named `OPENROUTER_API_KEY` in GitHub Settings → Secrets and variables → Actions. The branch workflow `Phase 1 live smoke` reads it only during the five-case run. Do not add the key to an issue, PR, commit, fixture, or chat. The Actions logs contain the synthetic case outputs and are visible to anyone who can read this repository's Actions logs. Once the secret is saved, rerun the workflow or push to this branch.

## Phase 1 boundaries

- The five Chinese smoke messages and their gold decisions are in `tests/fixtures/smoke_cases.jsonl`. Adjacent English annotations help a reader understand the demonstration. English, gold labels, order facts and case IDs never enter the model prompt; only the original Chinese message does.
- The output schema contains four extraction fields with field-level support scores. Scores are ranking signals, not calibrated probabilities. `threshold=None` runs a clearly marked `smoke_unlocked` mode; no acceptance threshold has been selected yet. Do not report smoke-mode routes as held-out evaluation results.
- A `manual_review` output distinguishes `policy_required`, `low_confidence` and `validation_failure`. The threshold applies only to an otherwise automatic policy decision.
- The policy is a simplified project policy, including a 14-day brand goodwill extension. It is not a complete returns policy or a consumer-facing legal decision.
- Phase 1 includes no 180-case dataset, baseline, Streamlit UI, threshold tuning or held-out results.

## Phase 2A blueprint review

`data/returnguard_synth_v1/blueprints_dev.jsonl` and `blueprints_test.jsonl` contain 90 **design blueprints** each. They specify intended order/extraction facts and language constraints; they contain no Chinese customer messages and are not a finished benchmark. Their route/rule targets are design metadata, not model input. `matrix_report.json` records every quota, boundary-day counts, policy recomputations and blueprint file hashes. `review_samples.json` presents five complete blueprints for design review.

Recheck the committed files without changing them:

```bash
python -m pytest -q
python scripts/generate_blueprints.py --check
```

The deterministic generator is `scripts/generate_blueprints.py`; it creates missing outputs but refuses to overwrite different existing bytes. Phase 2A makes **zero API calls**. Surface generation with DeepSeek and formal dev/test evaluation require later design approval and are not part of these blueprints.

The test split uses a separate fixed construction seed to independently recombine factual/day, difficulty, length, tone, reason-family and linguistic-feature assignments within the quota constraints. Dev blueprints are unchanged. `overlap_report.json` compares all 8,100 dev/test pairs and all 90 same-index pairs, excluding IDs, absolute dates and provenance. The core signature includes rule, policy facts, elapsed days, difficulty, length and composition; the full signature adds tone, reason family and linguistic features (as an unordered set). Same-index twins under both signatures must be zero. Repeated policy facts across arbitrary indices are expected; this blueprint audit does not replace the later Chinese-message duplicate/leakage audit.

## Phase 2B construction and structured case review

Separate clean jobs produced 90 dev and 90 test records using `deepseek/deepseek-v4-pro-0813`, temperature 0.7 and top_p 0.9. The test job received only dev settings, never dev messages. Full raw responses, provenance and the original draft audit remain unchanged. Six generation responses were truncated and were completed against their frozen blueprints during structured case review, with no generation retries.

All 180 cases now have explicit `structured_case_review_v1.1` records: findings, repairs, exact evidence, source/content hashes and timestamps. Case-specific semantic review includes every unflagged case. No author-wide personal manual-review claim or fabricated reviewer identity is made. The project author owns the final dataset-level approval.

Validate the concrete reviewed snapshot without API calls:

```bash
python scripts/check_review_readiness.py
python scripts/prepare_dataset_review.py --reviews data/returnguard_synth_v1/construction/structured_reviews.json
```

The commands produce review-stage candidates/audits and an optional offline inspector in `construction/`; they do not create frozen root splits or a freeze manifest. Case content hashes, pair hashes and audit snapshot hashes invalidate stale decisions after edits. Exact evidence, frozen intended values and unchanged Policy v1 are validated separately from substantive semantic review.

Read `docs/Phase2B_Review_Approval_Package.md` for counts, issue distribution, ten representative cases, all near-pair decisions, audit findings and course-feedback consistency. The status is **READY_FOR_DATASET_LEVEL_APPROVAL**, pending project-level go/no-go. `docs/Phase2B_Human_Review_Instructions.md` retains its old filename but describes the revised workflow. The original `human_review.html` is historical; the current optional inspector is `structured_review.html`.

After explicit approval of this snapshot, `scripts/freeze_dataset.py` requires both `--reviews REVIEW_PACKET` and `--approval APPROVAL_RECORD`. Its existing dedicated data commit, committed-byte verification and separate freeze-manifest procedure then applies. Formal GPT-5.6 Luna dev/test evaluation, provisional threshold selection and the baseline remain later work.
