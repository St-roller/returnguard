"""Validate the exact Chinese evidence contract and derive facts in code."""

from __future__ import annotations

from pydantic import ValidationError

from .schemas import CaseInput, DerivedFacts, Extraction


class ValidationFailure(ValueError):
    """A benchmark input or model response failed a hard validation rule."""


def validate_input(raw: object) -> CaseInput:
    try:
        case = CaseInput.model_validate(raw)
    except ValidationError as exc:
        raise ValidationFailure(f"invalid case input: {exc}") from exc
    if case.order_facts.request_date < case.order_facts.receipt_date:
        raise ValidationFailure("request_date precedes receipt_date")
    return case


def validate_extraction(raw: object, customer_message: str) -> Extraction:
    try:
        extraction = Extraction.model_validate(raw)
    except ValidationError as exc:
        raise ValidationFailure(f"invalid extraction schema: {exc}") from exc

    for name in Extraction.model_fields:
        field = getattr(extraction, name)
        for span in field.evidence:
            if not span or span not in customer_message:
                raise ValidationFailure(f"{name}: non-verbatim or empty evidence span")
        if field.value == "conflicting":
            if len(set(field.evidence)) < 2:
                raise ValidationFailure(f"{name}: conflicting requires two distinct spans")
        elif field.value not in {"unknown", "not_stated"} and not field.evidence:
            raise ValidationFailure(f"{name}: definitive value requires evidence")
    return extraction


def derive_facts(case: CaseInput, extraction: Extraction) -> DerivedFacts:
    names = ("tag_status", "damage_or_stain", "use_beyond_inspection")
    fields = {name: getattr(extraction, name) for name in names}
    values = {name: field.value for name, field in fields.items()}
    if "conflicting" in values.values():
        status = "conflicting"
    elif (
        values["tag_status"] == "removed"
        or values["damage_or_stain"] == "present"
        or values["use_beyond_inspection"] == "yes"
    ):
        status = "not_intact"
    elif (
        values["tag_status"] == "attached"
        and values["damage_or_stain"] == "absent"
        and values["use_beyond_inspection"] == "no"
    ):
        status = "intact"
    else:
        status = "unknown"
    return DerivedFacts(
        days_since_receipt=(case.order_facts.request_date - case.order_facts.receipt_date).days,
        condition_status=status,
        missing_condition_fields=[
            name for name, field in fields.items() if field.value == "unknown" and not field.evidence
        ],
        explicit_uncertainty_fields=[
            name for name, field in fields.items() if field.value == "unknown" and field.evidence
        ],
        conflicting_fields=[
            name for name in Extraction.model_fields if getattr(extraction, name).value == "conflicting"
        ],
    )
