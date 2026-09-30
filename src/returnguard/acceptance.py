"""Calculate support ranking and apply one explicit threshold when locked."""

from __future__ import annotations

from .schemas import Extraction, PolicyDecision


def case_support_score(decision: PolicyDecision, extraction: Extraction) -> float | None:
    rule_id = decision.candidate_rule_id
    if decision.candidate_route == "manual_review":
        return None
    reason = extraction.return_reason.support_score
    if rule_id in {"EL01_7DAY", "EL02_BRAND14"}:
        return min(
            reason,
            extraction.tag_status.support_score,
            extraction.damage_or_stain.support_score,
            extraction.use_beyond_inspection.support_score,
        )
    if rule_id in {"IN01_CUSTOM", "IN02_LATE"}:
        return reason
    if rule_id == "IN03_NOT_INTACT":
        decisive = [
            field.support_score
            for field, negative in (
                (extraction.tag_status, "removed"),
                (extraction.damage_or_stain, "present"),
                (extraction.use_beyond_inspection, "yes"),
            )
            if field.value == negative
        ]
        if not decisive:
            raise ValueError("IN03_NOT_INTACT requires a decisive negative condition")
        return min(reason, max(decisive))
    raise ValueError(f"unexpected auto-route rule ID: {rule_id}")


def accept(score: float, threshold: float) -> bool:
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must lie in [0, 1]")
    return score >= threshold
