"""Run exactly the five frozen Chinese smoke fixtures through live extraction."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from returnguard.extractor import OpenAIExtractor
from returnguard.pipeline import run_case
from returnguard.policy import Policy
from returnguard.schemas import CaseRecord


def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("Set OPENAI_API_KEY locally before running live smoke cases.")
    path = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "smoke_cases.jsonl"
    cases = [CaseRecord.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines()]
    extractor = OpenAIExtractor()
    policy = Policy()
    all_matched = True
    for case in cases:
        result = run_case(case.input.model_dump(mode="json"), extractor, policy, case_id=case.case_id)
        expected = case.gold["decision"]
        matched = (result["final_route"], result["candidate_rule_id"]) == (
            expected["route"], expected["rule_id"]
        )
        all_matched &= matched
        print(json.dumps({
            "case_id": case.case_id,
            "route": result["final_route"],
            "rule_id": result["candidate_rule_id"],
            "review_reason": result["review_reason"],
            "support_score": result["case_support_score"],
            "model_name": result["model_name"],
            "model_version": result["model_version"],
            "latency_seconds": result["latency_seconds"],
            "token_usage": result["token_usage"],
            "matches_fixture": matched,
            "zh": case.input.customer_message,
            "en_annotation_only": case.review_metadata["english_annotation"],
        }, ensure_ascii=False))
    if not all_matched:
        raise SystemExit("One or more live smoke cases did not match the frozen fixture.")


if __name__ == "__main__":
    main()
