from copy import deepcopy

import pytest

from returnguard.schemas import CaseInput
from returnguard.validation import ValidationFailure, derive_facts, validate_extraction, validate_input


def data(smoke_cases):
    c = smoke_cases[0]
    return c.input.customer_message, {
        name: {**field, "support_score": 0.95}
        for name, field in deepcopy(c.gold["extraction"]).items()
    }


def test_exact_evidence_and_schema(smoke_cases):
    message, raw = data(smoke_cases)
    raw["tag_status"]["evidence"] = ["吊牌仍然在"]
    with pytest.raises(ValidationFailure, match="non-verbatim"):
        validate_extraction(raw, message)
    _, raw = data(smoke_cases)
    raw["route"] = "eligible"
    with pytest.raises(ValidationFailure, match="schema"):
        validate_extraction(raw, message)


def test_definitive_and_conflicting_evidence(smoke_cases):
    message, raw = data(smoke_cases)
    raw["tag_status"]["evidence"] = []
    with pytest.raises(ValidationFailure, match="definitive"):
        validate_extraction(raw, message)
    _, raw = data(smoke_cases)
    raw["tag_status"] = {"value": "conflicting", "evidence": ["吊牌还在"], "support_score": 0.2}
    with pytest.raises(ValidationFailure, match="two distinct"):
        validate_extraction(raw, message)


@pytest.mark.parametrize("score", [-0.1, 1.1, float("nan")])
def test_invalid_score(smoke_cases, score):
    message, raw = data(smoke_cases)
    raw["return_reason"]["support_score"] = score
    with pytest.raises(ValidationFailure, match="schema"):
        validate_extraction(raw, message)


def test_absent_and_explicit_uncertainty(smoke_cases):
    c = smoke_cases[4]
    extraction = validate_extraction(
        {name: {**field, "support_score": 0.9} for name, field in c.gold["extraction"].items()},
        c.input.customer_message,
    )
    derived = derive_facts(c.input, extraction)
    assert derived.condition_status == "unknown"
    assert set(derived.explicit_uncertainty_fields) == {
        "tag_status", "damage_or_stain", "use_beyond_inspection"
    }
    assert derived.missing_condition_fields == []
    c = smoke_cases[3]
    extraction = validate_extraction(
        {name: {**field, "support_score": 0.9} for name, field in c.gold["extraction"].items()},
        c.input.customer_message,
    )
    assert derive_facts(c.input, extraction).missing_condition_fields == [
        "tag_status", "use_beyond_inspection"
    ]


def test_conflict_precedes_negative_condition():
    case = CaseInput.model_validate({
        "order_facts": {"receipt_date": "2026-09-01", "request_date": "2026-09-02", "is_custom_made": False},
        "customer_message": "吊牌剪了。吊牌还在。我穿出去上班。",
    })
    extraction = validate_extraction({
        "return_reason": {"value": "not_stated", "evidence": [], "support_score": 0.8},
        "tag_status": {"value": "conflicting", "evidence": ["吊牌剪了", "吊牌还在"], "support_score": 0.2},
        "damage_or_stain": {"value": "unknown", "evidence": [], "support_score": 0.8},
        "use_beyond_inspection": {"value": "yes", "evidence": ["穿出去上班"], "support_score": 0.9},
    }, case.customer_message)
    assert derive_facts(case, extraction).condition_status == "conflicting"


def test_invalid_order_input(smoke_cases):
    raw = smoke_cases[0].input.model_dump(mode="json")
    raw["order_facts"]["request_date"] = "2026-08-31"
    with pytest.raises(ValidationFailure, match="precedes"):
        validate_input(raw)
    del raw["order_facts"]["receipt_date"]
    with pytest.raises(ValidationFailure, match="invalid case input"):
        validate_input(raw)
