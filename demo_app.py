"""One-page local recorded replay of the existing ReturnGuard pipeline."""

from datetime import date
import json
from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from returnguard.extractor import ExtractionResponse
from returnguard.pipeline import run_case
from returnguard.policy import Policy

EXAMPLES = {
    "Eligible — test_001": "test_001",
    "Ineligible — test_031": "test_031",
    "Manual review — test_061": "test_061",
    "Manual review (low confidence) — test_079": "test_079",
}
FIELDS = ("return_reason", "tag_status", "damage_or_stain", "use_beyond_inspection")


class RecordedExtractor:
    """Supply the saved extraction for its original message, without a model client."""

    def __init__(self, message, saved):
        self.message = message
        self.saved = saved

    def extract(self, customer_message):
        if customer_message != self.message:
            raise ValueError("Recorded extraction requires the original frozen message.")
        return ExtractionResponse(
            raw=self.saved["raw_structured_extraction"],
            model_name=self.saved["model_name"],
            model_version=self.saved["model_version"],
        )


def main():
    st.set_page_config(page_title="ReturnGuard recorded demo", layout="centered")
    st.title("ReturnGuard")
    st.info("Recorded Demo · offline replay — no new model call")
    st.caption("Choose a frozen example. Inputs are read-only; staff confirm the triage recommendation.")
    case_id = EXAMPLES[st.selectbox("Recorded example", list(EXAMPLES))]
    artifacts = ROOT / "results" / "phase3"
    try:
        case = next(
            item for line in (artifacts / "test_inputs.jsonl").read_text(encoding="utf-8").splitlines()
            if (item := json.loads(line))["case_id"] == case_id
        )
        saved = json.loads((artifacts / "test_cases" / f"{case_id}.json").read_text(encoding="utf-8"))
        threshold = json.loads((artifacts / "threshold_lock_v1.json").read_text(encoding="utf-8"))["value"]
        if threshold != 0.86:
            raise ValueError("The demo requires the locked threshold 0.86.")
    except (OSError, ValueError, KeyError, StopIteration) as exc:
        st.error(f"Cannot load the frozen recorded example: {exc}")
        return

    data = case["input"]
    facts = data["order_facts"]
    st.text_area("Customer message", data["customer_message"], disabled=True, key=f"message_{case_id}")
    receipt, request = st.columns(2)
    receipt.date_input("Receipt date", date.fromisoformat(facts["receipt_date"]), disabled=True, key=f"receipt_{case_id}")
    request.date_input("Request date", date.fromisoformat(facts["request_date"]), disabled=True, key=f"request_{case_id}")
    st.checkbox("Custom-made", facts["is_custom_made"], disabled=True, key=f"custom_{case_id}")
    if not st.button("Replay recorded case", type="primary"):
        return

    try:
        result = run_case(data, RecordedExtractor(data["customer_message"], saved), Policy(), case_id=case_id, threshold=threshold)
        unchanged = (
            "raw_structured_extraction", "validated_extraction", "derived_facts",
            "candidate_route", "candidate_rule_id", "final_route", "review_reason",
            "case_support_score", "threshold_value",
        )
        if any(result[field] != saved[field] for field in unchanged):
            raise ValueError("Replay differs from the frozen result; display stopped.")
    except (ValueError, KeyError, RuntimeError) as exc:
        st.error(f"Cannot replay the frozen result: {exc}")
        return

    st.caption(f"Recorded source: results/phase3/test_cases/{case_id}.json")
    route, rule = st.columns(2)
    route.metric("Final route", result["final_route"])
    rule.metric("Matched rule ID", result["candidate_rule_id"])
    support, locked = st.columns(2)
    score = result["case_support_score"]
    support.metric("Case support score", "N/A" if score is None else f"{score:.2f}")
    locked.metric("Locked threshold", f"{threshold:.2f}")
    st.write("Review reason: " + (result["review_reason"] or "None"))
    st.caption("Support is an evidence-support score, not a calibrated probability. Policy-required manual review bypasses the threshold and has no case support score.")
    st.subheader("Extracted fields and exact Chinese evidence")
    extraction = result["validated_extraction"]
    st.table([
        {"Field": field, "Value": extraction[field]["value"],
         "Exact Chinese evidence": "\n".join(extraction[field]["evidence"])}
        for field in FIELDS
    ])


if __name__ == "__main__":
    main()
