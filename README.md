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

## Phase 2B construction and individual human review

Gate 2 authorized separate DeepSeek generation runs using the merged PR #2 blueprints. The run produced 90 dev and 90 test records with `deepseek/deepseek-v4-pro-0813`, temperature 0.7 and top_p 0.9. Raw responses are retained losslessly as `construction/raw_dev.jsonl.gz` and `raw_test.jsonl.gz`; split provenance records actual settings, provider routing, batch IDs and source hashes. The test job received only the dev settings file, never dev messages. Six outputs were truncated; no content-quality retry was made. This is a construction dataset, **not a frozen or evaluated benchmark**.

Prepare the offline review page without an API key:

```bash
python scripts/prepare_dataset_review.py
```

Open `data/returnguard_synth_v1/construction/human_review.html` in a browser. Every case starts pending. A named human must check all 13 items, correct Chinese realization/evidence/English annotation as necessary, and approve each case individually. Chinese remains canonical; English is stored only inside review metadata. The page saves progress locally and exports `returnguard_human_reviews.json`. Do not commit reviewer exports containing unreviewed cases as gold.

After edits, regenerate the page/audit while preserving actual review decisions:

```bash
python scripts/prepare_dataset_review.py --reviews /path/to/returnguard_human_reviews.json
```

Reopen the updated page, resolve current near-duplicate pairs and attest the new formatting/annotation/input-word audit. Content hashes prevent an old pair decision or audit attestation from silently approving edited text. Exact duplicates and route/rule leakage block freeze. Generic words such as the garment's Chinese “标签” are flags requiring human inspection, not automatically treated as policy labels.

Only after all 180 individual approvals and current audits pass:

```bash
python scripts/freeze_dataset.py --reviews /path/to/returnguard_human_reviews.json
```

This validates exact Chinese evidence, preserves blueprint facts/quotas, recomputes Policy v1 gold and prepares final CaseRecord v1 files. Commit final data, human-review export, provenance and audit in a dedicated data commit; then run the same command with `--freeze-commit ACTUAL_DATA_COMMIT_SHA`. The script verifies the committed bytes before writing `freeze_manifest.json`. Commit that manifest separately as metadata, so it can reference a real data commit without a self-reference. No freeze manifest is issued while human review is pending. No formal GPT-5.6 Luna calls or threshold selection belong to this phase.
