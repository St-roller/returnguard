# Phase 3 sanitized public evaluation package

Gate 3B was approved and formal evaluation closed by the user on 1 October 2026. Publication to the public `St-roller/returnguard` repository is authorized only for this deterministic sanitized package. No new model call is authorized or performed. PR #4 remains draft for review.

The complete original package is retained separately, outside this repository's public files. Its SHA-256 is `375026564d47e37c7bf1683e52820bc20014494608fc5bddb948d2d60a661bc4`. The public commit contains no copy of that archive.

## Fixed publication rules

- For all 180 dev/test attempt outcomes, retain attempt timestamps, request-binding hashes, exact output_text, latency and status. Replace the provider response envelope with an allowlist containing hashed response ID, model, status, creation/completion time and numeric token/cost usage. Remove the output array entirely, including reasoning items, encrypted reasoning content, internal provider metadata, headers and credential fields.
- Replace response IDs in dev/test case files and raw/scored prediction records with `sha256:` followed by SHA-256 of the original UTF-8 identifier. No semantic prediction field is changed.
- Preserve all other original Phase 3 files byte for byte. In particular, frozen inputs, structured extractions, evidence spans, gold, routes, rules, scores, abstention reasons, threshold 0.86, locks, metrics, error analysis, token counts, latency and cost remain unchanged.

The allowlist discards unknown provider fields rather than trying to recognize every possible hidden payload. Numeric reasoning-token counts in usage are retained; reasoning objects and content are excluded. Response IDs are opaque audit hashes, not reusable provider identifiers.

## Equivalence and hashes

`sanitization_equivalence_v1.json` records deterministic private-to-public equivalence for every original file, before and after SHA-256 for transformed files, and counts. All 360 dev/test raw/scored prediction rows have identical fields except the explicitly permitted ID transform. All 180 individual case records preserve those same semantic fields. Exact structured output_text is preserved across 180 provider-envelope projections. Both 90-case splits remain complete.

Gold joins and metrics were recomputed offline with the already locked acceptance point; the development split applies its existing locked 0.86 threshold to its historical candidate records. No threshold was selected, enumerated or retuned. The unchanged Keyword+Rules predictions reproduce byte for byte, and test error analysis reproduces exactly. Original metrics, error analysis, config/threshold/baseline locks and authorization records are byte-identical to the private archive.

`public_artifact_manifest.json` hashes the current sanitized files, frozen dev/test data, locked evaluation source, baseline, sanitizer and its tests. The manifest excludes itself. Historical `phase3a_*`/`phase3b_*` manifests, prediction-freeze records and hash fields in the original handoff/summary remain original provenance records: hashes of private original bytes. They are not substituted with public hashes. Use the new public manifest for current public bytes; use the original hashes when auditing the preserved private package. Historical original handoffs remain unchanged, with this document supplying the publication overlay.

## Verification commands

From the existing clone with locked dependencies:

```bash
python scripts/sanitize_phase3_public.py verify-public
python scripts/sanitize_phase3_public.py check --private-package /path/to/private/full-package.zip
python -m pytest -q
```

`verify-public` requires only the public files. The second command additionally needs the private archive and proves equivalence without editing artifacts or calling a model. The sanitizer does not import a live model client. The formal evaluation runners are historical locked sources and must not be used for a new evaluation.

This publication cleans the current Phase 3 files; it does not rewrite repository history or remove earlier Actions artifacts. Earlier public dev commits are historical records. The current sanitized package and its manifest define the reviewed publication boundary. No final report, README, dataset documentation or demo material was rewritten.
