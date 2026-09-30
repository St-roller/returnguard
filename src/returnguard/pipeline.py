"""One input, one extractor call, validated facts, ordered policy, one output."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import ACCEPTANCE_VERSION, PROMPT_VERSION, SCHEMA_VERSION
from .acceptance import accept, case_support_score
from .extractor import Extractor
from .policy import Policy
from .validation import ValidationFailure, derive_facts, validate_extraction, validate_input


def run_case(
    input_data: object,
    extractor: Extractor,
    policy: Policy,
    *,
    case_id: str | None = None,
    threshold: float | None = None,
) -> dict[str, Any]:
    """Run one case. None means Phase 1 smoke mode, before threshold selection.

    Smoke mode surfaces the policy candidate for integration testing; it must not be
    reported as a thresholded evaluation result. A locked threshold is required for
    the later development/test evaluation phase.
    """
    if threshold is not None and not 0 <= threshold <= 1:
        raise ValueError("threshold must lie in [0, 1]")
    record: dict[str, Any] = {
        "case_id": case_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "schema_version": SCHEMA_VERSION,
        "policy_version": policy.version,
        "prompt_version": PROMPT_VERSION,
        "model_name": None,
        "model_version": None,
        "raw_structured_extraction": None,
        "validated_extraction": None,
        "derived_facts": None,
        "candidate_route": None,
        "candidate_rule_id": None,
        "candidate_review_reason": None,
        "case_support_score": None,
        "acceptance_version": ACCEPTANCE_VERSION if threshold is not None else "smoke_unlocked",
        "threshold_version": ACCEPTANCE_VERSION if threshold is not None else None,
        "threshold_value": threshold,
        "final_route": "manual_review",
        "review_reason": "validation_failure",
        "latency_seconds": None,
        "token_usage": {"input_tokens": None, "output_tokens": None},
        "validation_error": None,
    }
    try:
        case = validate_input(input_data)
    except ValidationFailure as exc:
        record["validation_error"] = str(exc)
        return record

    # The extractor receives exactly the Chinese message. Order facts, gold data,
    # English annotation, case ID and split are never passed to its input method.
    response = extractor.extract(case.customer_message)
    record["model_name"] = response.model_name
    record["model_version"] = response.model_version
    record["raw_structured_extraction"] = response.raw
    record["latency_seconds"] = response.latency_seconds
    record["token_usage"] = {
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
    }
    try:
        extraction = validate_extraction(response.raw, case.customer_message)
    except ValidationFailure as exc:
        record["validation_error"] = str(exc)
        return record

    record["validated_extraction"] = extraction.model_dump()
    derived = derive_facts(case, extraction)
    record["derived_facts"] = derived.model_dump()
    decision = policy.decide(case, extraction, derived)
    record["candidate_route"] = decision.candidate_route
    record["candidate_rule_id"] = decision.candidate_rule_id
    record["candidate_review_reason"] = decision.candidate_review_reason
    if decision.candidate_route == "manual_review":
        record["review_reason"] = decision.candidate_review_reason
        return record

    score = case_support_score(decision, extraction)
    if score is None:
        raise RuntimeError("auto-route decision has no support score")
    record["case_support_score"] = score
    if threshold is None or accept(score, threshold):
        record["final_route"] = decision.candidate_route
        record["review_reason"] = None
    else:
        record["review_reason"] = "low_confidence"
    return record
