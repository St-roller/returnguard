# ReturnGuard Phase 2B handoff — generated, awaiting real human review

```yaml
project: ReturnGuard
specification: ReturnGuard_Phase2A_2B_Implementation_Specification_v1.1
gate_2: approved_by_user
phase: 2B
status: generated_and_audited_drafts_pending_human_review
generated_records: 180
dev_records: 90
test_records: 90
human_approved_records: 0
frozen_dataset: false
freeze_manifest_created: false
formal_gpt_5_6_luna_calls: 0
acceptance_threshold_selected: false
policy_v1_changed: false
schema_v1_changed: false
acceptance_v1_changed: false
blueprint_matrix_changed: false
```

## Repository and immutable source

- Repository: https://github.com/St-roller/returnguard
- Draft PR: https://github.com/St-roller/returnguard/pull/3
- Branch: `phase2b-generation-review-v1`
- Approved merged PR #2 source commit: `c2af09ffb1346c91a8d6cb4783d827c24c6704bd`.
- Generation execution commit: `244cd39dd9f2a3022fecb09a5b17328fc55af824`.
- Live generation run: https://github.com/St-roller/returnguard/actions/runs/36690532439
- Current repository matrix/blueprints were verified against merged main, including the matrix Git blob and tree. No older exported attachment was used for source data.
- Accepted structural overlaps remain unchanged: same-index core/full twins 0; all-cross-split core overlap pairs 10; full overlap pairs 0. No matrix redesign occurred.

| Source file | SHA-256 |
|---|---|
| matrix_report.json | a5d38bcd9f8a7c496d5cad8a843d2026d7f136b1642a0933b307265db27d45c8 |
| blueprints_dev.jsonl | 00c67b86bb87988a3e028f07c64cdef3e9ddd0b203612d963ef0e52a33034832 |
| blueprints_test.jsonl | 27c02b91f81f0416bb6d1bdd4846f4ace19acaef560b94f9001a13077a955c88 |

## Actual generation

```yaml
gateway: OpenRouter
requested_model: deepseek/deepseek-v4-pro-0813
returned_model_matches: 180/180
prompt_version: dataset_generation_v1
temperature: 0.7
top_p: 0.9
max_tokens: 4096
seed: null
parameter_fallbacks: []
http_request_attempts: 180
infrastructure_retries_used: 0
content_quality_retries_used: 0
api_failures: 0
parsed_complete_surface_outputs: 174
truncated_outputs_needing_revision: 6
dev_batch: dev_generation_v1_36690532439_1
test_batch: test_generation_v1_36690532439_1
prompt_tokens: 115638
completion_tokens: 73682
reported_usage_cost_usd: 0.28557238222
```

The cost is the sum of OpenRouter's returned `usage.cost`, not a fresh pricing estimate. Complete usage objects and raw responses are retained.

Dev and test ran in separate clean GitHub Actions jobs. The test job downloaded only the actual settings artifact; it received no dev customer messages. Generation inputs were a factual/style whitelist with no blueprint IDs, route targets, rule IDs or composition labels. Stored requests are independently checked against this contract for all 180 cases. Chinese is canonical; English is annotation-only metadata. Actual upstream providers varied through OpenRouter routing and are recorded per case and per split; no model substitution was made.

## Draft audit findings — not a final passed audit

```yaml
draft_audit_status: pending_human_review
preflight_issue_cases: 56
dev_preflight_issue_cases: 23
test_preflight_issue_cases: 33
nonempty_parsed_messages: 174
exact_duplicate_count_among_nonempty_messages: 0
near_duplicate_pairs: 11
near_dev_pairs: 5
near_test_pairs: 1
near_cross_split_pairs: 5
dev_pairs_compared: 3741
test_pairs_compared: 3741
cross_split_pairs_compared: 7569
near_sequence_ratio_threshold: 0.80
near_character_trigram_jaccard_threshold: 0.55
near_flag_operator: OR
route_rule_input_leakage_hits: 0
id_label_leakage_hits: 0
generation_requests_scanned: 180
generation_request_label_leakage_hits: 0
english_annotation_word_flags: 0
chinese_generic_word_flag_cases: 4
generator_artifact_word_flag_cases: 4
```

These thresholds were fixed before the actual generation audit. Exact and near duplicate scans exclude empty placeholders; the six unparsed cases remain pending and must be included in the final re-audit after repair. The earlier count of 5 apparent duplicates was caused by grouping six empty placeholders; it is not evidence of duplicated generated Chinese messages.

Unparsed cases: `dev_008`, `dev_014`, `dev_053`, `test_015`, `test_033`, `test_054`. All six raw outputs finished with `finish_reason=length`; some include partial JSON, some no final content. They are not silently retried, deleted or replaced by AI-approved gold.

The four generic Chinese word flags are the garment word “标签” in `test_023`, `test_036`, `test_047`, `test_081`; they also appear in those raw response artifacts. They require human inspection, not automatic deletion or a claim of confirmed label leakage. Route/rule token matches are hard blockers. Message formatting by route and repeated six-character prefixes are provided in the draft audit for actual human inspection.

Preflight issues identify syntactic evidence/blueprint-consistency failures; they are not a complete semantic review. All 180 cases need human reading, including the 124 with no automated preflight issue. Do not treat proposed extraction values copied from blueprints as supported by the realized Chinese unless a human verifies them.

## Deliverables and commands

- `prompts/dataset_generation_v1.md`: locked generator prompt.
- `src/returnguard/surface_generation.py`, `scripts/generate_dataset.py`: isolated generation, provenance and bounded infrastructure retries.
- `data/returnguard_synth_v1/construction/raw_{dev,test}.jsonl.gz`: lossless raw records, including failures.
- `construction/provenance_{dev,test}.json`: actual settings, split batches, raw/source hashes and upstream providers.
- `construction/human_review.html`: all 180 cases, editable messages/annotations/evidence, 13 individual checks, named/timestamped approval, local progress, JSON export and audit review.
- `construction/draft_audit_report.json`: deterministic draft duplicate/leakage/formatting report.
- `src/returnguard/dataset_review.py`: exact evidence validation, blueprint preservation, deterministic gold, approval and audit gates.
- `scripts/prepare_dataset_review.py`: rebuild packet from original raw records; `--reviews FILE` preserves actual human edits and re-audits them.
- `scripts/freeze_dataset.py`: permits final files only after 180 real individual approvals and passed current audits; manifest only after verification against an actual dedicated data commit.
- `docs/Phase2B_Human_Review_Instructions.md`: user instructions in Chinese.

```bash
python scripts/prepare_dataset_review.py
python scripts/prepare_dataset_review.py --reviews /path/to/returnguard_human_reviews.json
# Only after real human approvals and current audit attestation:
python scripts/freeze_dataset.py --reviews /path/to/returnguard_human_reviews.json
# Commit the final data/audit/reviews/provenance first; then:
python scripts/freeze_dataset.py --reviews /path/to/returnguard_human_reviews.json --freeze-commit ACTUAL_DATA_COMMIT_SHA
```

To preserve frozen Schema v1, final generation provenance, dataset version and design tags are stored inside its extensible `review_metadata`; they are not added as extra CaseRecord root fields. English is `review_metadata.english_annotation`. Gold has no invented confidence score; schema-only score placeholders are used transiently inside deterministic derivation and removed from gold.

## Verification

- 46 local pytest tests passed, including all-blueprint policy gold recomputation, verbatim evidence/intent rejection, missing/explicit uncertainty distinction, approval gates, content-bound pair decisions, current audit attestation and actual raw request/provenance verification.
- `python scripts/generate_blueprints.py --check` passed; all 180 policy targets and source bytes remain unchanged.
- JavaScript syntax check passed for the generated offline page. Full browser interaction verification was unavailable locally because the installed Playwright package has no browser executable; no visual/interactive QA success is claimed.
- Dev/test generation jobs both succeeded; initial generator implementation passed 40 tests in the live job before any API call.
- Human approval metadata remains pending, with no invented name/timestamp and no final freeze manifest.

## Exact continuation boundary

The next input must be the user's actual exported `returnguard_human_reviews.json`, after reading/checking each case. A general “approved” message does not manufacture these review records. This follows the user-approved specification Sections 19 and 24: generated cases are not gold immediately, and freeze comes after all 180 approvals and audits.

Work then re-audits corrected messages, returns any remaining evidence/semantic/pair/formatting issues for human resolution, recomputes all final gold decisions with unchanged Policy v1, creates the dedicated data commit, verifies it and records SHA-256 hashes plus its real commit SHA in the manifest. No evaluated-model formal calls or provisional threshold selection may begin before that freeze and the subsequent evaluation authorization.
