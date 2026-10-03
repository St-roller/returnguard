# ReturnGuard-Synth-v1

ReturnGuard-Synth-v1 is the **frozen synthetic benchmark** for initial apparel-return triage in Simplified Chinese: 180 reviewed cases, split into 90 dev and 90 held-out test cases. Formal evaluation is closed; text, gold labels and freeze artifacts are immutable.

## Why synthetic data

The project had no real customer dataset. Synthetic construction allowed deliberate coverage of policy boundaries, absent/conflicting facts and varied Chinese wording without real customer records. A generator different from the evaluated model reduced self-generated evaluation bias: **both dev and test were drafted by `deepseek/deepseek-v4-pro-0813`**, while the evaluated extractor was `openai/gpt-5.6-luna`. Different models and structured review do not eliminate shared synthetic style or annotation bias.

## Composition and case format

| Axis | Dev | Test |
|---|---:|---:|
| Total | 90 | 90 |
| Gold eligible / ineligible / manual_review | 30 / 30 / 30 | 30 / 30 / 30 |
| Easy / medium / hard design assignments | 30 / 30 / 30 | 30 / 30 / 30 |
| Short / medium / long message assignments | 30 / 30 / 30 | 30 / 30 / 30 |

The [matrix report](returnguard_synth_v1/matrix_report.json) records rule quotas, tones, reason families, language features and calendar-day boundaries including days 0, 7, 8, 14 and 15. Difficulty/length assignments are design categories, not measurements of human difficulty or samples of natural traffic.

Canonical JSONL records contain IDs/split, schema/policy versions, `input`, `gold` and review metadata. Input has the Chinese message and trusted receipt/request dates and custom-made status. Gold contains four extraction values with exact evidence and a Policy v1 route/rule decision. English annotations and design/review metadata are for inspection only. The formal model received **only the Chinese message**; order facts went to code, while gold/English/IDs/split metadata were excluded from model requests.

## Generation provenance

1. Deterministic design blueprints fixed factual intent, policy coverage and language constraints before surface generation. Test used a separate fixed construction seed and independent quota-preserving recombination.
2. Isolated dev/test jobs used DeepSeek V4 Pro 0813 through OpenRouter, `temperature=0.7`, `top_p=0.9`, no seed. Test received settings but not dev messages. These are generator settings, not the evaluated model's parameters.
3. Each split produced 87 complete generations and 3 records needing revision. Six truncated responses were completed during review against their original blueprints; no generation retry selected a better answer. Original generations and provenance were preserved.

See [dev provenance](returnguard_synth_v1/provenance_dev.json), [test provenance](returnguard_synth_v1/provenance_test.json), the [generation prompt](../prompts/dataset_generation_v1.md), and historical `construction/raw_dev.jsonl.gz` / `raw_test.jsonl.gz`. Construction archives are source records, not canonical cases or formal predictions.

## Structured review and repair

Every case, including cases without automatic warnings, received a `structured_case_review_v1.1` record with findings, repairs, semantic/evidence checks, timestamps and source/content hashes. All 180 were approved: 160 had a text/evidence/annotation repair and 20 were unchanged. Repair categories overlap and must not be summed as additional cases. This was structured case review followed by explicit dataset-level author approval, not a claim that a named human independently hand-reviewed every label.

Repairs addressed surface wording, evidence, missing versus uncertain facts, reason families, language constraints, annotations and near-duplicates. Intended blueprint facts and Policy v1 stayed fixed. Gold route/rule labels were derived deterministically from reviewed gold extraction and trusted order facts, then checked against design intent. Evidence substring validation was separate from checking semantic support. No benchmark repair followed formal test observations.

See [structured reviews](returnguard_synth_v1/structured_reviews.json), [review summary](returnguard_synth_v1/construction/review_summary.json), and the [historical approval package](../docs/Phase2B_Review_Approval_Package.md).

## Leakage and duplicate controls

The [final audit](returnguard_synth_v1/audit_report.json) passed: 180 nonempty messages, 180 valid evidence records, 180 matching policy recomputations, zero exact duplicates and zero detected model-visible route/rule leakage. All 180 generation requests were scanned for target-label leakage. Blueprint overlap was checked separately across 8,100 dev/test pairs; shared policy facts are expected and not themselves duplicate messages.

Message near-duplicate screening flagged sequence ratio >=0.8 **or** character-trigram Jaccard >=0.55. Content hashes invalidated stale pair decisions after edits. The final cross-split pair `dev_052` / `test_085` was accepted as distinct: the former states a removed tag and is ineligible; the latter omits tag status and requires review. This similarity is recorded, not treated as zero near-duplicates. Natural apparel “标签” wording was inspected rather than automatically classified as label leakage.

These controls reduce observable leakage/duplication, but do not prove absence of subtle cues or shared generator style. See [blueprint overlap](returnguard_synth_v1/overlap_report.json) and [pair-review history](returnguard_synth_v1/construction/near_pair_review_history.json).

## Two-stage freeze and authority

The author approved only snapshot `6bc97f310cffef6b62c32e473455bb7c60766479521d6d1d96758db94681977a`. Final splits/audit/provenance/review bytes were prepared without changing reviewed cases, then committed in data commit `28095bd3c9f407d15eca4fe28a4d6e2775b9fffb`. Committed bytes were verified before the [freeze manifest](returnguard_synth_v1/freeze_manifest.json) was created in separate commit `6531604a4d4347d40e89ec2ded6fc63da13c9383`.

| Canonical split | SHA-256 |
|---|---|
| `dev.jsonl` | `39943bdf053298dc3a9e6c45b58d6b6d06fb136fc1e5c30519b5de62e6c14c70` |
| `test.jsonl` | `9b3fe0451253d089923c42ca5071684ad3c9d1d5ce3ab6814a0af9bc9a511933` |

The manifest also hashes audit/review, provenance, blueprints and matrix/overlap reports. [Dataset-level approval](returnguard_synth_v1/dataset_level_approval.json) and the manifest establish freeze authority. Older `human_review_status: pending`, approval-stage handoffs and “no evaluation yet” fields describe earlier stages; they do not override later approval, freeze or the [closed evaluation](../results/README.md).

## Canonical files and inspection

| Files | Role |
|---|---|
| [dev.jsonl](returnguard_synth_v1/dev.jsonl), [test.jsonl](returnguard_synth_v1/test.jsonl) | Frozen reviewed cases used in evaluation |
| `freeze_manifest.json`, `dataset_level_approval.json` | Approval and committed-byte identities |
| `provenance_*.json`, `structured_reviews.json`, `audit_report.json` | Construction lineage and final review/audit |
| `blueprints_*.jsonl`, `matrix_report.json`, `overlap_report.json` | Design intent and quotas/overlap |
| `construction/` | Historical drafts, raw generations, repairs, review UI and pair history |
| [Phase 3 projections](../results/phase3/) | Input-only inference records; gold remains in canonical data |

From the repository root, `python scripts/generate_blueprints.py --check` and `python scripts/sanitize_phase3_public.py verify-public` inspect existing files without API calls or writes. The [root quick start](../README.md#ta-quick-start-offline-no-api-key) provides setup. Regeneration, review-packet preparation and freeze scripts are historical tooling, not commands to create a new dataset version in this phase.

This small balanced synthetic sample is a controlled course benchmark. It does not represent production class frequencies, customer language diversity or real policy disputes, and cannot establish production generalization.
