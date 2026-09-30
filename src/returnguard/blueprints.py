"""Deterministic Phase 2A design blueprints; no model or message generation."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Literal

from pydantic import Field

from .policy import Policy
from .schemas import (
    CaseInput, DamageStatus, Extraction, OrderFacts, ReturnReason, Route,
    StrictModel, TagStatus, UseStatus,
)
from .validation import derive_facts, validate_input

BLUEPRINT_VERSION = "blueprint_v1.0"
DATASET_VERSION = "ReturnGuard-Synth-v1"
GENERATOR_VERSION = "deterministic_blueprints_v1"
SPLITS = ("dev", "test")
RULE_QUOTAS = {
    "EL01_7DAY": ("eligible", (5, 5, 5)),
    "EL02_BRAND14": ("eligible", (5, 5, 5)),
    "IN01_CUSTOM": ("ineligible", (4, 3, 3)),
    "IN02_LATE": ("ineligible", (4, 3, 3)),
    "IN03_NOT_INTACT": ("ineligible", (3, 4, 3)),
    "MR01_QUALITY": ("manual_review", (3, 4, 3)),
    "MR03_REASON": ("manual_review", (3, 3, 4)),
    "MR02_CONDITION": ("manual_review", (3, 3, 4)),
}
REASON_FAMILIES = (
    "size_fit", "colour_style", "changed_mind", "no_longer_needed",
    "duplicate_purchase", "preference_mismatch",
)
TONES = ("neutral", "colloquial", "polite_conversational", "frustrated_complaint")
LENGTHS = ("short", "medium", "long")
DIFFICULTIES = ("easy", "medium", "hard")
BOUNDARIES = {0, 7, 8, 14, 15}


class BlueprintError(ValueError):
    """A blueprint or its design quota differs from the locked specification."""


class Target(StrictModel):
    route: Route
    rule_id: Literal[
        "EL01_7DAY", "EL02_BRAND14", "IN01_CUSTOM", "IN02_LATE",
        "IN03_NOT_INTACT", "MR01_QUALITY", "MR03_REASON", "MR02_CONDITION",
    ]


class IntendedExtraction(StrictModel):
    return_reason: ReturnReason
    tag_status: TagStatus
    damage_or_stain: DamageStatus
    use_beyond_inspection: UseStatus


class GenerationConstraints(StrictModel):
    reason_family: str
    difficulty: Literal["easy", "medium", "hard"]
    message_length: Literal["short", "medium", "long"]
    tone: Literal["neutral", "colloquial", "polite_conversational", "frustrated_complaint"]
    linguistic_features: list[str] = Field(min_length=1)
    boundary_day: int | None
    composition_tag: str
    issue_family: str | None = None


class BlueprintProvenance(StrictModel):
    blueprint_generator: Literal["deterministic_python"]
    generator_version: Literal["deterministic_blueprints_v1"]
    blueprint_batch_id: Literal["dev_blueprints_v1", "test_blueprints_v1"]


class Blueprint(StrictModel):
    blueprint_id: str
    split: Literal["dev", "test"]
    blueprint_version: Literal["blueprint_v1.0"]
    policy_version: Literal["policy_v1.0"]
    target: Target
    trusted_order_facts: OrderFacts
    intended_extraction: IntendedExtraction
    generation_constraints: GenerationConstraints
    provenance: BlueprintProvenance


def _difficulty(rule_id: str, index: int) -> str:
    _, quotas = RULE_QUOTAS[rule_id]
    pattern = [DIFFICULTIES[i] for i in range(3)] * 3
    if quotas == (5, 5, 5):
        return (["easy", "medium", "hard"] * 5)[index]
    pattern.append(DIFFICULTIES[quotas.index(4)])
    return pattern[index]


def _design(rule_id: str, i: int) -> tuple[int, bool, IntendedExtraction, str, str | None]:
    """Return day, custom flag, facts, composition tag, issue family."""
    day = 3
    custom = False
    reason = "ordinary_return"
    tag, damage, use = "attached", "absent", "no"
    composition = "base"
    issue = None
    if rule_id == "EL01_7DAY":
        day = [0, 1, 0, 2, 7, 7, 7, 3, 4, 5, 6, 1, 2, 4, 6][i]
    elif rule_id == "EL02_BRAND14":
        day = [8, 8, 8, 9, 10, 11, 12, 13, 9, 10, 11, 12, 14, 14, 14][i]
    elif rule_id == "IN01_CUSTOM":
        custom = True
        if i < 6:
            day, composition = [0, 1, 4, 7, 8, 14][i], "custom_only"
        elif i < 8:
            day, composition = [15, 23][i - 6], "also_late"
        else:
            day, composition = [7, 8][i - 8], "also_not_intact"
            if i == 8:
                tag = "removed"
            else:
                damage = "present"
    elif rule_id == "IN02_LATE":
        day = [15, 15, 15, 15, 16, 20, 25, 30, 31, 45][i]
        if i in (6, 7):
            tag = "unknown"
        elif i == 8:
            damage = "present"
        elif i == 9:
            use = "yes"
        composition = "late"
    elif rule_id == "IN03_NOT_INTACT":
        day = [0, 2, 4, 6, 7, 8, 10, 12, 13, 14][i]
        if i < 3:
            tag, composition = "removed", "tag_removed"
        elif i < 6:
            damage, composition = "present", "damage_present"
        elif i < 9:
            use, composition = "yes", "use_beyond_inspection"
        else:
            tag, damage, composition = "removed", "present", "multiple_negative"
    elif rule_id == "MR01_QUALITY":
        reason = "quality_or_fulfillment_issue"
        issue = (["pre_existing_defect"] * 4 + ["wrong_item_fulfillment"] * 3
                 + ["shipping_damage"] * 3)[i]
        day = [15, 7, 8, 3, 18, 14, 2, 7, 40, 0][i]
        custom = i in (2, 7)
        if issue != "wrong_item_fulfillment":
            damage = "present"
        composition = "quality_issue"
    elif rule_id == "MR03_REASON":
        reason = "not_stated"
        day = [0, 7, 8, 14, 7, 15, 16, 1, 7, 14][i]
        custom = i == 4
        composition = (["otherwise_intact"] * 4 + ["custom_or_late"] * 3
                       + ["irrelevant_detail"] * 3)[i]
    elif rule_id == "MR02_CONDITION":
        day = [0, 3, 5, 6, 7, 8, 9, 11, 13, 14][i]
        composition = [
            "missing_information", "explicit_uncertainty", "contradiction",
            "missing_information", "contradiction", "explicit_uncertainty",
            "contradiction", "missing_information", "explicit_uncertainty",
            "contradiction",
        ][i]
        if composition in ("missing_information", "explicit_uncertainty"):
            tag = "unknown"
        elif i in (2, 9):
            tag = "conflicting"
        elif i == 4:
            damage = "conflicting"
        else:
            use = "conflicting"
    else:
        raise BlueprintError(f"unknown rule: {rule_id}")
    return day, custom, IntendedExtraction(
        return_reason=reason, tag_status=tag, damage_or_stain=damage,
        use_beyond_inspection=use,
    ), composition, issue


def _features(difficulty: str, i: int, composition: str) -> list[str]:
    if difficulty == "easy":
        result = ["direct_wording"]
    elif difficulty == "medium":
        result = [["colloquial_wording"], ["evidence_spread_across_sentences"],
                  ["one_irrelevant_detail"], ["non_trivial_negation"]][i % 4].copy()
    else:
        pool = ("self_correction", "complex_negation", "indirect_expression",
                "awkward_wording", "irrelevant_detail")
        result = [pool[i % 5], pool[(i + 2) % 5]]
    if composition == "irrelevant_detail":
        result.append("substantial_irrelevant_detail")
    elif composition == "missing_information":
        result.append("omit_one_condition_fact")
    elif composition == "explicit_uncertainty":
        result.append("explicit_condition_uncertainty")
    elif composition == "contradiction":
        result.append("two_distinct_conflicting_condition_spans")
    return list(dict.fromkeys(result))


def generate_blueprints() -> list[Blueprint]:
    blueprints = []
    for split_index, split in enumerate(SPLITS):
        serial = 0
        route_offsets = defaultdict(int)
        for rule_index, (rule_id, (route, difficulty_quota)) in enumerate(RULE_QUOTAS.items()):
            n = sum(difficulty_quota)
            for i in range(n):
                serial += 1
                day, custom, facts, composition, issue = _design(rule_id, i)
                receipt = date(2026, 5 + split_index, 1) + timedelta(
                    days=(i * 7 + rule_index * 3 + split_index) % 24
                )
                route_index = route_offsets[route]
                route_offsets[route] += 1
                difficulty = _difficulty(rule_id, i)
                family = (
                    REASON_FAMILIES[(i + 2 * rule_index + split_index) % 6]
                    if facts.return_reason == "ordinary_return" else
                    (issue if issue is not None else "not_stated")
                )
                length_index = (i * 2 + rule_index) % 3
                # The MR03 case requiring substantial irrelevant detail needs
                # room for it; exchange one length target within the rule.
                if rule_id == "MR03_REASON" and i in (4, 9):
                    length_index = (9 * 2 + rule_index) % 3 if i == 4 else (4 * 2 + rule_index) % 3
                blueprints.append(Blueprint(
                    blueprint_id=f"{split}_bp_{serial:03d}", split=split,
                    blueprint_version=BLUEPRINT_VERSION, policy_version="policy_v1.0",
                    target=Target(route=route, rule_id=rule_id),
                    trusted_order_facts=OrderFacts(
                        receipt_date=receipt, request_date=receipt + timedelta(days=day),
                        is_custom_made=custom,
                    ),
                    intended_extraction=facts,
                    generation_constraints=GenerationConstraints(
                        reason_family=family, difficulty=difficulty,
                        message_length=LENGTHS[length_index],
                        tone=TONES[(route_index + split_index) % 4],
                        linguistic_features=_features(difficulty, i, composition),
                        boundary_day=day if day in BOUNDARIES else None,
                        composition_tag=composition, issue_family=issue,
                    ),
                    provenance=BlueprintProvenance(
                        blueprint_generator="deterministic_python",
                        generator_version=GENERATOR_VERSION,
                        blueprint_batch_id=f"{split}_blueprints_v1",
                    ),
                ))
    return blueprints


def _check(actual: object, expected: object, description: str) -> None:
    if actual != expected:
        raise BlueprintError(f"{description}: expected {expected!r}, got {actual!r}")


def _count(values) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _condition_status(bp: Blueprint) -> str:
    facts = bp.intended_extraction
    values = (facts.tag_status, facts.damage_or_stain, facts.use_beyond_inspection)
    if "conflicting" in values:
        return "conflicting"
    if facts.tag_status == "removed" or facts.damage_or_stain == "present" or facts.use_beyond_inspection == "yes":
        return "not_intact"
    if values == ("attached", "absent", "no"):
        return "intact"
    return "unknown"


def _validate_rule_composition(rule: str, rows: list[Blueprint]) -> dict:
    days = [(b.trusted_order_facts.request_date - b.trusted_order_facts.receipt_date).days for b in rows]
    tags = _count(b.generation_constraints.composition_tag for b in rows)
    conditions = _count(_condition_status(b) for b in rows)
    if rule == "EL01_7DAY":
        _check((days.count(0), sum(1 <= d <= 6 for d in days), days.count(7)), (2, 10, 3), rule)
        _check(conditions, {"intact": 15}, rule)
    elif rule == "EL02_BRAND14":
        _check((days.count(8), sum(9 <= d <= 13 for d in days), days.count(14)), (3, 9, 3), rule)
        _check(conditions, {"intact": 15}, rule)
    elif rule == "IN01_CUSTOM":
        _check(tags, {"also_late": 2, "also_not_intact": 2, "custom_only": 6}, rule)
        _check(sum(d > 14 for d in days), 2, rule)
        _check(conditions, {"intact": 8, "not_intact": 2}, rule)
        _check(sum(b.trusted_order_facts.is_custom_made for b in rows), 10, rule)
        for b, day in zip(rows, days):
            tag = b.generation_constraints.composition_tag
            expected = {
                "custom_only": (day <= 14 and _condition_status(b) == "intact"),
                "also_late": (day > 14 and _condition_status(b) == "intact"),
                "also_not_intact": (day <= 14 and _condition_status(b) == "not_intact"),
            }
            _check(expected[tag], True, b.blueprint_id)
    elif rule == "IN02_LATE":
        _check((days.count(15), sum(16 <= d <= 30 for d in days), sum(d > 30 for d in days)), (4, 4, 2), rule)
        _check(conditions, {"intact": 6, "not_intact": 2, "unknown": 2}, rule)
    elif rule == "IN03_NOT_INTACT":
        _check(tags, {"damage_present": 3, "multiple_negative": 1, "tag_removed": 3, "use_beyond_inspection": 3}, rule)
        _check((sum(0 <= d <= 7 for d in days), sum(8 <= d <= 14 for d in days)), (5, 5), rule)
        _check(conditions, {"not_intact": 10}, rule)
        for b in rows:
            f = b.intended_extraction
            negatives = [f.tag_status == "removed", f.damage_or_stain == "present", f.use_beyond_inspection == "yes"]
            expected = {"tag_removed": 0, "damage_present": 1, "use_beyond_inspection": 2}
            tag = b.generation_constraints.composition_tag
            if tag in expected:
                _check(negatives, [j == expected[tag] for j in range(3)], b.blueprint_id)
            else:
                _check(sum(negatives) >= 2, True, b.blueprint_id)
    elif rule == "MR01_QUALITY":
        _check(_count(b.generation_constraints.issue_family for b in rows), {
            "pre_existing_defect": 4, "shipping_damage": 3, "wrong_item_fulfillment": 3,
        }, rule)
        _check((sum(d > 14 for d in days), sum(b.trusted_order_facts.is_custom_made for b in rows)), (3, 2), rule)
        for b in rows:
            issue = b.generation_constraints.issue_family
            _check(b.generation_constraints.reason_family, issue, b.blueprint_id)
            _check(b.intended_extraction.return_reason, "quality_or_fulfillment_issue", b.blueprint_id)
            _check(b.intended_extraction.damage_or_stain,
                   "absent" if issue == "wrong_item_fulfillment" else "present", b.blueprint_id)
    elif rule == "MR03_REASON":
        _check(tags, {"custom_or_late": 3, "irrelevant_detail": 3, "otherwise_intact": 4}, rule)
        _check(_count(b.intended_extraction.return_reason for b in rows), {"not_stated": 10}, rule)
        for b in rows:
            tag = b.generation_constraints.composition_tag
            if tag == "otherwise_intact":
                day = (b.trusted_order_facts.request_date - b.trusted_order_facts.receipt_date).days
                _check((_condition_status(b), b.trusted_order_facts.is_custom_made, day <= 14),
                       ("intact", False, True), b.blueprint_id)
            elif tag == "custom_or_late":
                day = (b.trusted_order_facts.request_date - b.trusted_order_facts.receipt_date).days
                _check(b.trusted_order_facts.is_custom_made or day > 14, True, b.blueprint_id)
            else:
                _check("substantial_irrelevant_detail" in b.generation_constraints.linguistic_features, True, b.blueprint_id)
    elif rule == "MR02_CONDITION":
        _check(tags, {"contradiction": 4, "explicit_uncertainty": 3, "missing_information": 3}, rule)
        _check((sum(0 <= d <= 7 for d in days), sum(8 <= d <= 14 for d in days)), (5, 5), rule)
        _check(conditions, {"conflicting": 4, "unknown": 6}, rule)
        for b in rows:
            tag, facts = b.generation_constraints.composition_tag, b.intended_extraction
            _check(("conflicting" in (facts.tag_status, facts.damage_or_stain, facts.use_beyond_inspection)) == (tag == "contradiction"), True, b.blueprint_id)
            if tag != "contradiction":
                _check((facts.tag_status, facts.damage_or_stain, facts.use_beyond_inspection),
                       ("unknown", "absent", "no"), b.blueprint_id)
            feature = {"missing_information": "omit_one_condition_fact", "explicit_uncertainty": "explicit_condition_uncertainty", "contradiction": "two_distinct_conflicting_condition_spans"}[tag]
            _check(feature in b.generation_constraints.linguistic_features, True, b.blueprint_id)
    return {"composition_tags": tags, "condition_status": conditions,
            "day_counts": {str(day): count for day, count in sorted(Counter(days).items())}}


def validate_blueprints(blueprints: list[Blueprint], policy: Policy | None = None) -> dict:
    """Validate loaded blueprints, all quotas, and each target against Policy v1."""
    policy = policy or Policy()
    _check(policy.version, "policy_v1.0", "policy version")
    _check(len(blueprints), 180, "total blueprints")
    ids = [b.blueprint_id for b in blueprints]
    _check(len(set(ids)), len(ids), "unique blueprint IDs")
    report: dict = {
        "dataset_version": DATASET_VERSION, "blueprint_version": BLUEPRINT_VERSION,
        "generator_version": GENERATOR_VERSION, "policy_version": policy.version,
        "total_n": len(blueprints), "splits": {},
        "validation": {"policy_recomputed_matches": 0, "valid_trusted_dates": 0, "unique_ids": True},
    }
    for split in SPLITS:
        rows = [b for b in blueprints if b.split == split]
        _check(len(rows), 90, f"{split} size")
        _check([b.blueprint_id for b in rows], [f"{split}_bp_{i:03d}" for i in range(1, 91)], f"{split} IDs")
        _check({b.provenance.blueprint_batch_id for b in rows}, {f"{split}_blueprints_v1"}, f"{split} batch")
        for b in rows:
            _check(b.policy_version, policy.version, b.blueprint_id)
            _check(b.blueprint_version, BLUEPRINT_VERSION, b.blueprint_id)
            _check(b.generation_constraints.boundary_day, (
                (b.trusted_order_facts.request_date - b.trusted_order_facts.receipt_date).days
                if (b.trusted_order_facts.request_date - b.trusted_order_facts.receipt_date).days in BOUNDARIES else None
            ), f"{b.blueprint_id} boundary tag")
            # No Chinese realization exists in Phase 2A. The placeholder only
            # allows trusted-date validation and is never sent to an LLM.
            case = validate_input(CaseInput(order_facts=b.trusted_order_facts, customer_message="BLUEPRINT_ONLY"))
            report["validation"]["valid_trusted_dates"] += 1
            values = b.intended_extraction.model_dump()
            extraction = Extraction.model_validate({
                name: {"value": value, "evidence": [], "support_score": 1.0}
                for name, value in values.items()
            })
            decision = policy.decide(case, extraction, derive_facts(case, extraction))
            _check((decision.candidate_route, decision.candidate_rule_id),
                   (b.target.route, b.target.rule_id), b.blueprint_id)
            report["validation"]["policy_recomputed_matches"] += 1
        _check(_count(b.target.route for b in rows), {"eligible": 30, "ineligible": 30, "manual_review": 30}, f"{split} route")
        _check(_count(b.generation_constraints.difficulty for b in rows), {"easy": 30, "hard": 30, "medium": 30}, f"{split} difficulty")
        _check(_count(b.generation_constraints.message_length for b in rows), {"long": 30, "medium": 30, "short": 30}, f"{split} length")
        rule_rows = {rule: [b for b in rows if b.target.rule_id == rule] for rule in RULE_QUOTAS}
        rule_report = {}
        for rule, (route, (easy, medium, hard)) in RULE_QUOTAS.items():
            subset = rule_rows[rule]
            _check(len(subset), easy + medium + hard, f"{split} {rule} n")
            _check(_count(b.generation_constraints.difficulty for b in subset),
                   {"easy": easy, "medium": medium, "hard": hard}, f"{split} {rule} difficulty")
            _check(_count(b.target.route for b in subset), {route: len(subset)}, f"{split} {rule} route")
            for b in subset:
                if b.intended_extraction.return_reason == "ordinary_return":
                    _check(b.generation_constraints.reason_family in REASON_FAMILIES, True, b.blueprint_id)
            if rule in {"EL01_7DAY", "EL02_BRAND14", "IN01_CUSTOM", "IN02_LATE", "IN03_NOT_INTACT", "MR02_CONDITION"}:
                _check(set(b.generation_constraints.reason_family for b in subset), set(REASON_FAMILIES), f"{split} {rule} reason spread")
            rule_report[rule] = {
                "n": len(subset), "route": route,
                "difficulty": _count(b.generation_constraints.difficulty for b in subset),
                "message_length": _count(b.generation_constraints.message_length for b in subset),
                "reason_family": _count(b.generation_constraints.reason_family for b in subset),
                **_validate_rule_composition(rule, subset),
            }
        tone_by_route = {route: _count(b.generation_constraints.tone for b in rows if b.target.route == route)
                         for route in ("eligible", "ineligible", "manual_review")}
        length_by_route = {route: _count(b.generation_constraints.message_length for b in rows if b.target.route == route)
                           for route in ("eligible", "ineligible", "manual_review")}
        for route, counts in tone_by_route.items():
            _check(set(counts), set(TONES), f"{split} {route} tones")
            _check(max(counts.values()) - min(counts.values()) <= 1, True, f"{split} {route} tone balance")
            _check(length_by_route[route], {"long": 10, "medium": 10, "short": 10}, f"{split} {route} length balance")
        boundaries = {str(day): {
            "n": sum(b.generation_constraints.boundary_day == day for b in rows),
            "difficulty": _count(b.generation_constraints.difficulty for b in rows if b.generation_constraints.boundary_day == day),
        } for day in sorted(BOUNDARIES)}
        for day, detail in boundaries.items():
            _check(detail["n"] >= 2, True, f"{split} day {day} multiple cases")
            _check(len(detail["difficulty"]) >= 2, True, f"{split} day {day} difficulty spread")
        report["splits"][split] = {
            "n": len(rows), "route_counts": _count(b.target.route for b in rows),
            "difficulty_counts": _count(b.generation_constraints.difficulty for b in rows),
            "message_length_counts": _count(b.generation_constraints.message_length for b in rows),
            "tone_by_route": tone_by_route, "message_length_by_route": length_by_route,
            "boundary_days": boundaries, "rules": rule_report,
        }
    _check(report["validation"]["policy_recomputed_matches"], 180, "policy recomputations")
    return report
