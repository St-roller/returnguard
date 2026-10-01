# ReturnGuard Phase 2B — structured case review

The filename is retained for existing links. This document now describes the revised `structured_case_review_v1.1` workflow.

All 180 generated cases undergo individual substantive review against the 13-item checklist, including the 124 cases with no automated preflight alarm. Review records include versioned method provenance, case-specific findings, repairs, exact evidence, timestamps, source hashes and the hash of the reviewed message/annotation/evidence. No personal reviewer identity is invented. The project author owns the final dataset-level approval.

## Current review artifacts

- `construction/structured_reviews.json`: the 180 explicit case-level decisions and current audit/pair decisions.
- `construction/reviewed_candidate_dev.jsonl` and `reviewed_candidate_test.jsonl`: reviewed candidates, 90 each; not frozen benchmark files.
- `construction/final_review_audit.json`: current duplicate/leakage/format findings and deterministic validation.
- `construction/review_summary.json`: overlapping repair counts and readiness status.
- `construction/representative_cases.json`: 10 complete before/after examples.
- `construction/near_pair_review_history.json`: original and intermediate pair outcomes; stale hashes are historical only.
- `construction/preserved_source_hashes.json`: hashes of the original raw responses, provenance, draft audit, approved blueprints, policy and schema.
- `construction/structured_review.html`: optional offline inspector for the review packet.
- `docs/Phase2B_Review_Approval_Package.md`: project-level go/no-go package.

`human_review.html` and `draft_audit_report.json` remain historical source artifacts from the original generation branch. Their old pending/named-human workflow does not govern this continuation.

## Check a reviewed packet

```bash
python scripts/check_review_readiness.py --reviews data/returnguard_synth_v1/construction/structured_reviews.json
python scripts/prepare_dataset_review.py --reviews data/returnguard_synth_v1/construction/structured_reviews.json
```

The first command validates existing explicit decisions, checks preserved sources and length intent, recomputes unchanged Policy v1 and writes approval-stage artifacts under `construction/`. It does not infer semantic approval from preflight. The second command builds the optional offline inspector and a current review audit, preserving the original draft audit.

Message/evidence edits invalidate the case content hash. Message/annotation edits also change the dataset audit snapshot and near-pair IDs; rerun the audits and substantively recheck affected cases/pairs before approval. `unknown + []` is missing information, `unknown + evidence` is explicit uncertainty, and `conflicting` requires distinct unresolved incompatible spans about the same current item.

## Separate freeze approval

The current task stops at `READY_FOR_DATASET_LEVEL_APPROVAL`. The project author/design authority must approve the concrete snapshot first. No root `dev.jsonl`, `test.jsonl` or freeze manifest is created during this continuation.

Only after that approval, supply a real approval record containing `decision: approved_for_freeze`, the approved `dataset_snapshot_sha256`, `approved_at` and a truthful `approval_source`:

```bash
python scripts/freeze_dataset.py --reviews REVIEW_PACKET --approval APPROVAL_RECORD
```

The existing dedicated-data-commit/committed-byte verification procedure then applies; `--freeze-commit SHA` records the manifest in a subsequent metadata step. Formal GPT-5.6 Luna evaluation and threshold selection remain later phases.
