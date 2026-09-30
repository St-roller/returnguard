"""Check reproducibility, quota integrity, and policy-independent targets."""

import json
from pathlib import Path

import pytest

from returnguard.blueprints import Blueprint, BlueprintError, generate_blueprints, validate_blueprints

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
