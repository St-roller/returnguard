from types import SimpleNamespace

import pytest

from returnguard.acceptance import case_support_score
from returnguard.extractor import OpenAIExtractor
from returnguard.pipeline import run_case
from returnguard.schemas import Extraction

from conftest import FixtureExtractor


@pytest.mark.parametrize("index", range(5))
def test_five_smoke_cases_with_one_injected_call(policy, smoke_cases, index):
    case = smoke_cases[index]
    extractor = FixtureExtractor(case.gold["extraction"])
    record = run_case(case.input.model_dump(mode="json"), extractor, policy, case_id=case.case_id)
    assert extractor.calls == [case.input.customer_message]
    assert record["validated_extraction"] is not None
    assert record["candidate_rule_id"] == case.gold["decision"]["rule_id"]
    assert record["final_route"] == case.gold["decision"]["route"]
    assert record["review_reason"] == case.gold["decision"]["review_reason"]
    assert record["acceptance_version"] == "smoke_unlocked"
    assert case.review_metadata["english_annotation"] not in repr(extractor.calls)


def test_three_review_reasons(policy, smoke_cases):
    case = smoke_cases[0]
    input_data = case.input.model_dump(mode="json")
    low = run_case(input_data, FixtureExtractor(case.gold["extraction"]), policy, threshold=0.96)
    assert (low["candidate_route"], low["final_route"], low["review_reason"]) == (
        "eligible", "manual_review", "low_confidence"
    )
    quality = smoke_cases[3]
    required = run_case(quality.input.model_dump(mode="json"), FixtureExtractor(quality.gold["extraction"]), policy, threshold=1.0)
    assert (required["final_route"], required["review_reason"]) == ("manual_review", "policy_required")
    assert required["case_support_score"] is None
    invalid = run_case(input_data, FixtureExtractor({**case.gold["extraction"], "route": "eligible"}), policy)
    assert (invalid["final_route"], invalid["review_reason"]) == ("manual_review", "validation_failure")
    assert invalid["candidate_route"] is None


def test_invalid_trusted_input_does_not_call_extractor(policy, smoke_cases):
    case = smoke_cases[0]
    raw = case.input.model_dump(mode="json")
    raw["order_facts"]["request_date"] = "2026-08-31"
    extractor = FixtureExtractor(case.gold["extraction"])
    result = run_case(raw, extractor, policy)
    assert extractor.calls == []
    assert result["review_reason"] == "validation_failure"


def test_minimum_and_decisive_maximum_scores(policy, smoke_cases):
    case = smoke_cases[0]
    raw = {name: {**field, "support_score": score} for (name, field), score in zip(
        case.gold["extraction"].items(), [0.99, 0.96, 0.71, 0.95]
    )}
    class OneResponse:
        def extract(self, message):
            from returnguard.extractor import ExtractionResponse
            return ExtractionResponse(raw=raw, model_name="fixture-not-a-model")
    result = run_case(case.input.model_dump(mode="json"), OneResponse(), policy)
    assert result["case_support_score"] == 0.71
    case = smoke_cases[2]
    raw = {name: {**field, "support_score": score} for (name, field), score in zip(
        case.gold["extraction"].items(), [0.90, 0.76, 0.99, 0.86]
    )}
    extraction = Extraction.model_validate(raw)
    from returnguard.schemas import PolicyDecision
    decision = PolicyDecision(candidate_route="ineligible", candidate_rule_id="IN03_NOT_INTACT", candidate_review_reason=None)
    assert case_support_score(decision, extraction) == 0.86


def test_openai_adapter_only_sends_chinese_message(smoke_cases):
    case = smoke_cases[0]
    captured = []
    parsed = Extraction.model_validate({
        name: {**field, "support_score": 0.95} for name, field in case.gold["extraction"].items()
    })
    def create(**kwargs):
        captured.append(kwargs)
        return SimpleNamespace(
            output_text=parsed.model_dump_json(), model="gpt-5.6-luna",
            usage=SimpleNamespace(input_tokens=100, output_tokens=40),
        )
    fake_client = SimpleNamespace(responses=SimpleNamespace(create=create))
    result = OpenAIExtractor(client=fake_client).extract(case.input.customer_message)
    assert len(captured) == 1
    assert captured[0]["input"][1] == {"role": "user", "content": case.input.customer_message}
    assert captured[0]["tools"] == []
    assert captured[0]["text"]["format"]["strict"] is True
    assert list(captured[0]["text"]["format"]["schema"]["properties"]) == list(Extraction.model_fields)
    assert case.review_metadata["english_annotation"] not in repr(captured[0])
    assert "EL01_7DAY" not in repr(captured[0])
    assert result.input_tokens == 100


def test_non_json_model_output_becomes_validation_failure(policy, smoke_cases):
    case = smoke_cases[0]
    fake_client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(
        output_text="{truncated", model="gpt-5.6-luna", usage=None,
    )))
    result = run_case(case.input.model_dump(mode="json"), OpenAIExtractor(client=fake_client), policy)
    assert result["final_route"] == "manual_review"
    assert result["review_reason"] == "validation_failure"
    assert result["raw_structured_extraction"] == "{truncated"
