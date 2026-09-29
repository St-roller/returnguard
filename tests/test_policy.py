from copy import deepcopy

import pytest

from returnguard.schemas import CaseInput
from returnguard.validation import derive_facts, validate_extraction


def decide(policy, base_case, *, reason=None, custom=None, request_date=None, condition=None):
    raw = base_case.input.model_dump(mode="json")
    gold = deepcopy(base_case.gold["extraction"])
    if reason is not None:
        gold["return_reason"] = reason
    if custom is not None:
        raw["order_facts"]["is_custom_made"] = custom
    if request_date is not None:
        raw["order_facts"]["request_date"] = request_date
    if condition is not None:
        gold.update(condition)
    extraction = validate_extraction(
        {name: {**field, "support_score": 0.95} for name, field in gold.items()},
        raw["customer_message"],
    )
    case = CaseInput.model_validate(raw)
    return policy.decide(case, extraction, derive_facts(case, extraction))


def test_all_eight_rules(policy, smoke_cases):
    by_id = {c.case_id: c for c in smoke_cases}
    expected = {
        "smoke_001": "EL01_7DAY",
        "smoke_002": "EL02_BRAND14",
        "smoke_003": "IN03_NOT_INTACT",
        "smoke_004": "MR01_QUALITY",
        "smoke_005": "MR02_CONDITION",
    }
    for case_id, rule_id in expected.items():
        assert decide(policy, by_id[case_id]).candidate_rule_id == rule_id

    base = by_id["smoke_001"]
    assert decide(policy, base, custom=True).candidate_rule_id == "IN01_CUSTOM"
    assert decide(policy, base, request_date="2026-09-16").candidate_rule_id == "IN02_LATE"
    assert decide(policy, base, reason={"value": "not_stated", "evidence": []}).candidate_rule_id == "MR03_REASON"


@pytest.mark.parametrize(
    "case_id,kwargs,expected",
    [
        ("smoke_004", {}, "MR01_QUALITY"),  # quality + >14 days
        ("smoke_004", {"custom": True}, "MR01_QUALITY"),
        ("smoke_001", {"reason": {"value": "not_stated", "evidence": []}, "custom": True}, "MR03_REASON"),
        ("smoke_003", {}, "IN03_NOT_INTACT"),
        ("smoke_005", {}, "MR02_CONDITION"),
    ],
)
def test_precedence(policy, smoke_cases, case_id, kwargs, expected):
    case = next(c for c in smoke_cases if c.case_id == case_id)
    assert decide(policy, case, **kwargs).candidate_rule_id == expected


@pytest.mark.parametrize(
    "request_date,rule_id",
    [
        ("2026-09-01", "EL01_7DAY"),
        ("2026-09-08", "EL01_7DAY"),
        ("2026-09-09", "EL02_BRAND14"),
        ("2026-09-15", "EL02_BRAND14"),
        ("2026-09-16", "IN02_LATE"),
    ],
)
def test_calendar_day_boundaries(policy, smoke_cases, request_date, rule_id):
    assert decide(policy, smoke_cases[0], request_date=request_date).candidate_rule_id == rule_id
