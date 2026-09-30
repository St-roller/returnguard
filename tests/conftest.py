import json
from pathlib import Path

import pytest

from returnguard.extractor import ExtractionResponse
from returnguard.policy import Policy
from returnguard.schemas import CaseRecord


@pytest.fixture(scope="session")
def policy():
    return Policy()


@pytest.fixture(scope="session")
def smoke_cases():
    path = Path(__file__).parent / "fixtures" / "smoke_cases.jsonl"
    return [CaseRecord.model_validate(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines()]


class FixtureExtractor:
    """Wiring fixture, never a substitute for live model accuracy validation."""

    def __init__(self, gold_extraction):
        self.gold_extraction = gold_extraction
        self.calls = []

    def extract(self, customer_message):
        self.calls.append(customer_message)
        return ExtractionResponse(
            raw={
                name: ({**field, "support_score": 0.95} if isinstance(field, dict) else field)
                for name, field in self.gold_extraction.items()
            },
            model_name="fixture-not-a-model",
            model_version=None,
        )
