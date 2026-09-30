"""Check reproducibility, quota integrity, and policy-independent targets."""

import json
from pathlib import Path

import pytest

from returnguard.blueprints import Blueprint, BlueprintError, generate_blueprints, validate_blueprints
from returnguard.blueprints import quota_signature, structural_overlap_report

ROOT = Path(__file__).resolve().parents[1]


def test_committed_blueprints_match_generator_and_policy(policy):
    first = generate_blueprints()
    assert first == generate_blueprints()
    assert len(first) == 180
    loaded = [
        Blueprint.model_validate_json(line)
        for split in ("dev", "test")
        for line in (ROOT / "data" / "returnguard_synth_v1" / f"blueprints_{split}.jsonl")
        .read_text(encoding="utf-8").splitlines()
    ]
    assert loaded == first
    report = validate_blueprints(loaded, policy)
    saved = json.loads((ROOT / "data" / "returnguard_synth_v1" / "matrix_report.json").read_text(encoding="utf-8"))
    assert {key: saved[key] for key in report} == report
    assert report["validation"]["policy_recomputed_matches"] == 180
    assert report["validation"]["valid_trusted_dates"] == 180
    assert report["splits"]["dev"]["route_counts"] == {
        "eligible": 30, "ineligible": 30, "manual_review": 30,
    }
    samples = json.loads((ROOT / "data" / "returnguard_synth_v1" / "review_samples.json").read_text(encoding="utf-8"))
    assert len(samples["blueprints"]) == 5
    assert len({row["target"]["rule_id"] for row in samples["blueprints"]}) == 5
    assert all(Blueprint.model_validate(row) in loaded for row in samples["blueprints"])


@pytest.mark.parametrize("change", ("route", "date", "duplicate_id", "composition"))
def test_validator_rejects_corrupted_blueprints(policy, change):
    raw = [b.model_dump(mode="json") for b in generate_blueprints()]
    if change == "route":
        raw[0]["target"]["rule_id"] = "EL02_BRAND14"
    elif change == "date":
        raw[0]["trusted_order_facts"]["request_date"] = "2026-01-01"
    elif change == "duplicate_id":
        raw[1]["blueprint_id"] = raw[0]["blueprint_id"]
    else:
        raw[30]["generation_constraints"]["composition_tag"] = "also_late"
    with pytest.raises(BlueprintError):
        validate_blueprints([Blueprint.model_validate(row) for row in raw], policy)


def test_test_reassignment_preserves_marginals_and_dev_bytes(monkeypatch):
    import returnguard.blueprints as module

    revised = generate_blueprints()
    monkeypatch.setattr(module, "independent_test_assignment", lambda rows: None)
    original = generate_blueprints()
    assert [b for b in revised if b.split == "dev"] == [b for b in original if b.split == "dev"]
    assert quota_signature([b for b in revised if b.split == "test"]) == quota_signature([
        b for b in original if b.split == "test"
    ])
    overlap = structural_overlap_report(revised)
    assert overlap["same_index_core_twins"] == 0
    assert overlap["same_index_full_twins"] == 0
    assert overlap["all_cross_split_pairs_compared"] == 8100


def test_structural_audit_ignores_dates_ids_and_provenance(policy):
    from datetime import timedelta

    rows = generate_blueprints()
    dev = [b for b in rows if b.split == "dev"]
    twins = []
    for b in dev:
        twin = b.model_copy(deep=True)
        twin.split = "test"
        twin.blueprint_id = b.blueprint_id.replace("dev_", "test_")
        twin.provenance.blueprint_batch_id = "test_blueprints_v1"
        twin.trusted_order_facts.receipt_date += timedelta(days=60)
        twin.trusted_order_facts.request_date += timedelta(days=60)
        features = twin.generation_constraints.linguistic_features
        twin.generation_constraints.linguistic_features = list(reversed(features)) + features[:1]
        twins.append(twin)
    overlap = structural_overlap_report(dev + twins)
    assert overlap["same_index_core_twins"] == 90
    assert overlap["same_index_full_twins"] == 90
    with pytest.raises(BlueprintError, match="same-index core structural twins"):
        validate_blueprints(dev + twins, policy)
