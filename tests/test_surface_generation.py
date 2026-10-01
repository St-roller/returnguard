import json
from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError

from returnguard.blueprints import generate_blueprints
from returnguard.surface_generation import DeepSeekGenerator, LABEL_PATTERN, MODEL_ID, SETTINGS, request_body


def test_all_generation_requests_exclude_policy_targets_and_ids():
    for bp in generate_blueprints():
        body = request_body(bp, SETTINGS)
        text = json.dumps(body["messages"], ensure_ascii=False)
        assert not LABEL_PATTERN.search(text)
        assert bp.blueprint_id not in text
        payload = json.loads(body["messages"][1]["content"])
        assert set(payload) == {"order_facts", "facts", "reason_family", "issue_family", "uncertainty_expression", "language"}
        assert body["model"] == MODEL_ID
        assert body["temperature"] == 0.7 and body["top_p"] == 0.9
        assert "seed" not in body


def test_bad_surface_is_preserved_without_quality_retry():
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(model=MODEL_ID, model_extra={"provider": "test-provider"},
            choices=[SimpleNamespace(message=SimpleNamespace(content="{truncated"))],
            model_dump=lambda **kwargs: {"id": "fixture-only", "model": MODEL_ID})
    generator = DeepSeekGenerator(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    record = generator.generate(generate_blueprints()[0], SETTINGS, "fixture-not-a-live-run")
    assert len(calls) == 1
    assert record["generation_status"] == "needs_revision"
    assert record["raw_response"]["id"] == "fixture-only"
    assert record["generation_provenance"]["upstream_provider"] == "test-provider"


def test_infrastructure_failure_has_only_two_retries(monkeypatch):
    monkeypatch.setattr("returnguard.surface_generation.time.sleep", lambda seconds: None)
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        raise APIConnectionError(request=httpx.Request("POST", "https://example.invalid"))
    generator = DeepSeekGenerator(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    result = generator.generate(generate_blueprints()[0], SETTINGS, "fixture-only")
    assert len(calls) == 3
    assert result["generation_status"] == "api_failure"
    assert result["infrastructure_attempts"] == 3
