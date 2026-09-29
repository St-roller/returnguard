"""Frozen input, extraction and policy-facing structures for Phase 1."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReturnReason = Literal[
    "ordinary_return", "quality_or_fulfillment_issue", "not_stated", "conflicting"
]
TagStatus = Literal["attached", "removed", "unknown", "conflicting"]
DamageStatus = Literal["absent", "present", "unknown", "conflicting"]
UseStatus = Literal["no", "yes", "unknown", "conflicting"]
Route = Literal["eligible", "ineligible", "manual_review"]
ReviewReason = Literal["policy_required", "low_confidence", "validation_failure"]
ConditionStatus = Literal["intact", "not_intact", "unknown", "conflicting"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OrderFacts(StrictModel):
    receipt_date: date
    request_date: date
    is_custom_made: bool


class CaseInput(StrictModel):
    order_facts: OrderFacts
    customer_message: str = Field(min_length=1)


class CaseRecord(StrictModel):
    case_id: str
    split: Literal["dev", "test", "smoke"]
    schema_version: Literal["case_v1.0"]
    policy_version: Literal["policy_v1.0"]
    input: CaseInput
    gold: dict | None = None
    review_metadata: dict | None = None


class ExtractionField(StrictModel):
    value: str
    evidence: list[str]
    support_score: float = Field(ge=0, le=1, allow_inf_nan=False)


class ReturnReasonField(ExtractionField):
    value: ReturnReason


class TagStatusField(ExtractionField):
    value: TagStatus


class DamageStatusField(ExtractionField):
    value: DamageStatus


class UseStatusField(ExtractionField):
    value: UseStatus


class Extraction(StrictModel):
    return_reason: ReturnReasonField
    tag_status: TagStatusField
    damage_or_stain: DamageStatusField
    use_beyond_inspection: UseStatusField


class DerivedFacts(StrictModel):
    days_since_receipt: int
    condition_status: ConditionStatus
    missing_condition_fields: list[str]
    explicit_uncertainty_fields: list[str]
    conflicting_fields: list[str]


class PolicyDecision(StrictModel):
    candidate_route: Route
    candidate_rule_id: str
    candidate_review_reason: Literal["policy_required"] | None
