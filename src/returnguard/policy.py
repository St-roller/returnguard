"""Apply the frozen, ordered machine-readable Policy v1 rules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import CaseInput, DerivedFacts, Extraction, PolicyDecision

DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[2] / "policies" / "policy_v1.json"
RULE_IDS = (
    "MR01_QUALITY", "MR03_REASON", "IN01_CUSTOM", "IN02_LATE",
    "IN03_NOT_INTACT", "MR02_CONDITION", "EL01_7DAY", "EL02_BRAND14",
)


class PolicyError(RuntimeError):
    pass


class Policy:
    def __init__(self, path: Path | str = DEFAULT_POLICY_PATH):
        self.path = Path(path)
        self.definition = json.loads(self.path.read_text(encoding="utf-8"))
        if self.definition.get("policy_version") != "policy_v1.0":
            raise PolicyError("unexpected policy version")
        rules = self.definition.get("rules", [])
        if [rule.get("rule_id") for rule in rules] != list(RULE_IDS):
            raise PolicyError("rule IDs or priority order changed from specification")
        if [rule.get("priority") for rule in rules] != list(range(1, 9)):
            raise PolicyError("policy priorities must be exactly 1 through 8")
        self.rules = rules

    @property
    def version(self) -> str:
        return self.definition["policy_version"]

    @staticmethod
    def _matches(condition: dict[str, Any], facts: dict[str, Any]) -> bool:
        field, op, expected = condition["field"], condition["op"], condition["value"]
        if field not in facts:
            raise PolicyError(f"unknown policy field: {field}")
        actual = facts[field]
        if op == "eq":
            return actual == expected
        if op == "in":
            return actual in expected
        if op == "gt":
            return actual > expected
        if op == "between_inclusive":
            return expected[0] <= actual <= expected[1]
        raise PolicyError(f"unsupported policy operator: {op}")

    def decide(
        self, case: CaseInput, extraction: Extraction, derived: DerivedFacts
    ) -> PolicyDecision:
        facts = {
            "return_reason": extraction.return_reason.value,
            "is_custom_made": case.order_facts.is_custom_made,
            "days_since_receipt": derived.days_since_receipt,
            "condition_status": derived.condition_status,
        }
        for rule in self.rules:
            if all(self._matches(condition, facts) for condition in rule["all"]):
                return PolicyDecision(
                    candidate_route=rule["route"],
                    candidate_rule_id=rule["rule_id"],
                    candidate_review_reason=rule["review_reason"],
                )
        raise PolicyError("valid case matched no Policy v1 rule")
