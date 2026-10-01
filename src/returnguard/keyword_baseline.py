"""One fixed conservative regex operating point, using unchanged Policy v1."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from .policy import Policy
from .validation import derive_facts, validate_input

DEFAULT_PATTERNS = Path(__file__).resolve().parents[2] / "baselines/keyword_rules_v1.json"
VALUES = {
    "return_reason": {"quality_or_fulfillment_issue", "ordinary_return", "not_stated", "conflicting"},
    "tag_status": {"attached", "removed", "unknown", "conflicting"},
    "damage_or_stain": {"absent", "present", "unknown", "conflicting"},
    "use_beyond_inspection": {"no", "yes", "unknown", "conflicting"},
}


@dataclass(frozen=True)
class BaselineField:
    value: str
    evidence: list[str]


def validate_evidence(extraction: dict, message: str) -> SimpleNamespace:
    if set(extraction) != set(VALUES):
        raise ValueError("baseline field mismatch")
    for name, field in extraction.items():
        if set(field) != {"value", "evidence"} or field["value"] not in VALUES[name]:
            raise ValueError("baseline value-space violation or synthetic confidence")
        if not isinstance(field["evidence"], list) or any(not s or s not in message for s in field["evidence"]):
            raise ValueError("baseline evidence must be verbatim")
        if field["value"] == "conflicting" and len(set(field["evidence"])) < 2:
            raise ValueError("baseline conflicting requires distinct spans")
        if field["value"] not in {"unknown", "not_stated", "conflicting"} and not field["evidence"]:
            raise ValueError("baseline definitive value requires evidence")
    return SimpleNamespace(model_fields=VALUES, **{k: BaselineField(**v) for k, v in extraction.items()})


def hits(message: str, patterns: list[str]) -> list[re.Match]:
    return sorted((m for p in patterns for m in re.finditer(p, message)), key=lambda m: (m.start(), m.end()))


def overlaps(hit: re.Match, masks: list[re.Match]) -> bool:
    return any(hit.start() < m.end() and m.start() < hit.end() for m in masks)


def spans(matches: list[re.Match]) -> list[str]:
    return list(dict.fromkeys(m.group() for m in matches))


def uncertainty(message: str, terms: list[str], topics: str) -> list[re.Match]:
    term = "(?:" + "|".join(map(re.escape, terms)) + ")"
    topic = "(?:" + topics + ")"
    gap = r"[^，。！？；\n]{0,8}"
    return hits(message, [topic + gap + term, term + gap + topic])


def extract(message: str, patterns: dict) -> dict:
    reason = patterns["return_reason"]
    quality, ordinary = hits(message, reason["quality"]), hits(message, reason["ordinary"])
    out = {"return_reason": {"value": "quality_or_fulfillment_issue" if quality else "ordinary_return" if ordinary else "not_stated",
                              "evidence": spans(quality or ordinary)}}
    for name, pos, neg in (("tag_status", "attached", "removed"),
                           ("damage_or_stain", "absent", "present"),
                           ("use_beyond_inspection", "no", "yes")):
        family = patterns[name]
        uncertain = uncertainty(message, patterns["uncertainty"], family["topics"])
        positive = [m for m in hits(message, family[pos]) if not overlaps(m, uncertain)]
        masks = positive + hits(message, family["negative_mask"]) + uncertain
        negative = [m for m in hits(message, family[neg]) if not overlaps(m, masks)]
        if positive and negative:
            value, evidence = "conflicting", spans(positive + negative)
        elif positive:
            value, evidence = pos, spans(positive)
        elif negative:
            value, evidence = neg, spans(negative)
        else:
            value, evidence = "unknown", spans(uncertain)
        out[name] = {"value": value, "evidence": evidence}
    validate_evidence(out, message)
    return out


def run_baseline(row: dict, policy: Policy, patterns: dict) -> dict:
    case = validate_input(row["input"])
    raw = extract(case.customer_message, patterns)
    record = {"case_id": row["case_id"], "split": row["split"], "baseline_version": "keyword_rules_v1.0",
              "raw_structured_extraction": raw, "validated_extraction": None,
              "candidate_route": None, "candidate_rule_id": None,
              "candidate_review_reason": None, "evaluation_status": "validation_failure",
              "final_route": "manual_review", "review_reason": "validation_failure"}
    try:
        extraction = validate_evidence(raw, case.customer_message)
    except ValueError as exc:
        record["validation_error"] = str(exc)
        return record
    derived = derive_facts(case, extraction)
    decision = policy.decide(case, extraction, derived)
    record.update(validated_extraction=raw, derived_facts=derived.model_dump(),
                  evaluation_status="completed", **decision.model_dump(),
                  final_route=decision.candidate_route, review_reason=decision.candidate_review_reason)
    return record


def load_patterns(path: Path = DEFAULT_PATTERNS) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
