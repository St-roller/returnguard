"""Exercise the recorded UI without permitting a model client."""

from datetime import date
import json
from pathlib import Path

import openai
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def no_model_client(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "offline-demo-test-key")
    def blocked(*args, **kwargs):
        raise AssertionError("Recorded Demo must never construct a model client")
    monkeypatch.setattr(openai, "OpenAI", blocked)


@pytest.mark.parametrize("label,case_id,route,rule,score,reason", [
    ("Eligible — test_001", "test_001", "eligible", "EL01_7DAY", "0.96", "None"),
    ("Ineligible — test_031", "test_031", "ineligible", "IN01_CUSTOM", "0.98", "None"),
    ("Manual review — test_061", "test_061", "manual_review", "MR01_QUALITY", "N/A", "policy_required"),
    ("Manual review (low confidence) — test_079", "test_079", "manual_review", "EL01_7DAY", "0.82", "low_confidence"),
])
def test_recorded_routes_and_evidence(no_model_client, label, case_id, route, rule, score, reason):
    artifacts = ROOT / "results" / "phase3"
    saved = json.loads((artifacts / "test_cases" / f"{case_id}.json").read_text(encoding="utf-8"))
    inputs = [json.loads(line) for line in (artifacts / "test_inputs.jsonl").read_text(encoding="utf-8").splitlines()]
    data = next(case["input"] for case in inputs if case["case_id"] == case_id)
    app = AppTest.from_file(str(ROOT / "demo_app.py"), default_timeout=15).run()
    app.selectbox[0].select(label).run()
    assert not app.exception and not app.error
    assert "no new model call" in app.info[0].value
    assert app.text_area[0].disabled
    assert app.text_area[0].value == data["customer_message"]
    assert all(widget.disabled for widget in app.date_input)
    assert [widget.value for widget in app.date_input] == [
        date.fromisoformat(data["order_facts"][key]) for key in ("receipt_date", "request_date")
    ]
    assert app.checkbox[0].disabled
    assert app.checkbox[0].value == data["order_facts"]["is_custom_made"]
    app.button[0].click().run()
    assert not app.exception and not app.error
    assert [metric.value for metric in app.metric] == [route, rule, score, "0.86"]
    assert any(item.value == f"Review reason: {reason}" for item in app.markdown)
    rows = app.table[0].value.to_dict("records")
    assert len(rows) == 4
    for row in rows:
        field = saved["validated_extraction"][row["Field"]]
        assert row["Value"] == field["value"]
        assert row["Exact Chinese evidence"] == "\n".join(field["evidence"])
        assert all(span in data["customer_message"] for span in field["evidence"])


def test_switching_example_clears_previous_result(no_model_client):
    app = AppTest.from_file(str(ROOT / "demo_app.py"), default_timeout=15).run()
    app.button[0].click().run()
    assert app.metric[0].value == "eligible"
    app.selectbox[0].select("Ineligible — test_031").run()
    assert not app.metric
    app.button[0].click().run()
    assert not app.exception and not app.error
    assert app.metric[0].value == "ineligible"
