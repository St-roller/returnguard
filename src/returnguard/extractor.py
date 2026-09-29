"""One-call LLM extractor; the pipeline can inject a fixture extractor for tests."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from . import PROMPT_VERSION
from .schemas import Extraction

DEFAULT_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "extraction_v1.md"


@dataclass(frozen=True)
class ExtractionResponse:
    raw: object
    model_name: str
    model_version: str | None = None
    latency_seconds: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


class Extractor(Protocol):
    def extract(self, customer_message: str) -> ExtractionResponse: ...


class OpenAIExtractor:
    """Responses API Structured Outputs with no tools or order/gold metadata."""

    def __init__(
        self,
        model: str = "gpt-5.6-luna",
        prompt_path: Path | str = DEFAULT_PROMPT_PATH,
        client: object | None = None,
    ):
        if client is None:
            from openai import OpenAI

            client = OpenAI()
        self.client = client
        self.model = model
        self.prompt_version = PROMPT_VERSION
        self.instructions = Path(prompt_path).read_text(encoding="utf-8")

    def extract(self, customer_message: str) -> ExtractionResponse:
        started = time.perf_counter()
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": self.instructions},
                {"role": "user", "content": customer_message},
            ],
            text={"format": {
                "type": "json_schema",
                "name": "returnguard_extraction_v1",
                "strict": True,
                "schema": Extraction.model_json_schema(),
            }},
            tools=[],
        )
        elapsed = time.perf_counter() - started
        raw_text = response.output_text
        try:
            raw = json.loads(raw_text)
        except (TypeError, json.JSONDecodeError):
            # The pipeline classifies missing, truncated or non-JSON output as
            # validation_failure, preserving the raw response for inspection.
            raw = raw_text
        usage = getattr(response, "usage", None)
        return ExtractionResponse(
            raw=raw,
            model_name=self.model,
            model_version=getattr(response, "model", None),
            latency_seconds=elapsed,
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
        )
