"""Locked DeepSeek surface generation; no policy targets in model requests."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from .blueprints import Blueprint
from .schemas import StrictModel

MODEL_ID = "deepseek/deepseek-v4-pro-0813"
PROMPT_VERSION = "dataset_generation_v1"
SETTINGS = {"temperature": 0.7, "top_p": 0.9}
ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = ROOT / "prompts" / "dataset_generation_v1.md"
LABEL_PATTERN = re.compile(r"eligible|ineligible|manual_review|(?:EL0[12]|IN0[123]|MR0[123])|gold_route|rule_id|正确答案|规则编号|应判定为", re.I)


class ProposedEvidence(StrictModel):
    return_reason: list[str]
    tag_status: list[str]
    damage_or_stain: list[str]
    use_beyond_inspection: list[str]


class SurfaceOutput(StrictModel):
    customer_message: str
    english_annotation: str
    proposed_evidence: ProposedEvidence


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generation_payload(bp: Blueprint) -> dict:
    """Whitelist a factual projection; IDs, targets and composition stay local."""
    c = bp.generation_constraints
    uncertainty = "explicit" if c.composition_tag == "explicit_uncertainty" else "omit"
    payload = {
        "order_facts": bp.trusted_order_facts.model_dump(mode="json"),
        "facts": bp.intended_extraction.model_dump(),
        "reason_family": c.reason_family,
        "issue_family": c.issue_family,
        "uncertainty_expression": uncertainty,
        "language": {"difficulty": c.difficulty, "tone": c.tone,
                     "length_target_characters": {"short": [15, 35], "medium": [36, 70], "long": [71, 130]}[c.message_length],
                     "features": c.linguistic_features},
    }
    if LABEL_PATTERN.search(json.dumps(payload, ensure_ascii=False)):
        raise ValueError("label-bearing generation payload")
    return payload


def request_body(bp: Blueprint, settings: dict) -> dict:
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    if LABEL_PATTERN.search(prompt):
        raise ValueError("label-bearing generation instructions")
    return {
        "model": MODEL_ID,
        "messages": [{"role": "system", "content": prompt},
                     {"role": "user", "content": json.dumps(generation_payload(bp), ensure_ascii=False)}],
        **settings, "max_tokens": 4096,
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "returnguard_surface_v1", "strict": True,
            "schema": SurfaceOutput.model_json_schema(),
        }},
        "extra_body": {"provider": {"require_parameters": True}},
    }


class DeepSeekGenerator:
    def __init__(self, client=None):
        if client is None:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ["OPENROUTER_API_KEY"],
                            base_url="https://openrouter.ai/api/v1", max_retries=0, timeout=120)
        self.client = client

    def generate(self, bp: Blueprint, settings: dict, batch_id: str) -> dict:
        from openai import APIConnectionError, APIStatusError, APITimeoutError

        body = request_body(bp, settings)
        errors = []
        response = None
        started = time.perf_counter()
        for attempt in range(3):  # initial attempt plus at most two infrastructure retries
            try:
                response = self.client.chat.completions.create(**body)
                break
            except (APIConnectionError, APITimeoutError, APIStatusError) as exc:
                status = getattr(exc, "status_code", None)
                retryable = status is None or status in (408, 409, 429) or status >= 500
                errors.append({"attempt": attempt + 1, "status_code": status,
                               "error_type": type(exc).__name__, "message": str(exc)[:1000]})
                if not retryable or attempt == 2:
                    break
                time.sleep(0.5 * 2 ** attempt)
        provenance = {
            "gateway_provider": "OpenRouter", "model_id": MODEL_ID,
            "model_version": getattr(response, "model", None),
            "upstream_provider": (getattr(response, "model_extra", None) or {}).get("provider"),
            "prompt_version": PROMPT_VERSION, "prompt_sha256": sha256(PROMPT_PATH),
            "temperature": settings.get("temperature"), "top_p": settings.get("top_p"),
            "seed": None, "request_settings": {**settings, "max_tokens": 4096, "require_parameters": True},
            "generation_batch_id": batch_id, "split": bp.split, "blueprint_id": bp.blueprint_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "latency_seconds": time.perf_counter() - started,
        }
        raw = response.model_dump(mode="json") if response is not None else None
        record = {"blueprint_id": bp.blueprint_id, "split": bp.split, "request": body,
                  "raw_response": raw, "generation_provenance": provenance,
                  "infrastructure_attempts": len(errors) + (response is not None),
                  "errors": errors, "generation_status": "api_failure", "surface": None}
        if response is not None:
            try:
                surface = SurfaceOutput.model_validate_json(response.choices[0].message.content)
                if not surface.customer_message.strip() or not surface.english_annotation.strip():
                    raise ValueError("empty message/annotation")
                record.update(generation_status="generated", surface=surface.model_dump())
            except (ValueError, TypeError, IndexError) as exc:
                record.update(generation_status="needs_revision", parse_error=str(exc))
        return record
