# ReturnGuard

Phase 1 core for a Simplified Chinese apparel-return triage prototype. One model call extracts four facts and verbatim Chinese evidence. Deterministic code validates the extraction, derives item condition and calendar days, and applies the ordered rules in `policies/policy_v1.json`. The output is for human confirmation and takes no operational action.

## Run the Phase 1 tests

Python 3.11+ is required. From the repository root:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

On Windows, activate with `.venv\Scripts\activate` instead. The automated smoke tests use a fixture extractor to test the complete validation and routing path without an API key; they do **not** establish the live model's extraction accuracy.

## Run five live smoke inputs

Set `OPENAI_API_KEY` in your shell without committing it, then run:

```bash
python scripts/run_smoke.py
```

This makes one `gpt-5.6-luna` Responses API call per case and prints route, rule ID, review reason, score and whether the fixture's expected route and rule matched. A live failure remains a failure to investigate; the script does not edit the fixtures or policy. The actual model version, latency and token counts are in each in-memory prediction record. No API key is included in the repository.

## Phase 1 boundaries

- The five Chinese smoke messages and their gold decisions are in `tests/fixtures/smoke_cases.jsonl`. Adjacent English annotations help a reader understand the demonstration. English, gold labels, order facts and case IDs never enter the model prompt; only the original Chinese message does.
- The output schema contains four extraction fields with field-level support scores. Scores are ranking signals, not calibrated probabilities. `threshold=None` runs a clearly marked `smoke_unlocked` mode; no acceptance threshold has been selected yet. Do not report smoke-mode routes as held-out evaluation results.
- A `manual_review` output distinguishes `policy_required`, `low_confidence` and `validation_failure`. The threshold applies only to an otherwise automatic policy decision.
- The policy is a simplified project policy, including a 14-day brand goodwill extension. It is not a complete returns policy or a consumer-facing legal decision.
- Phase 1 includes no 180-case dataset, baseline, Streamlit UI, threshold tuning or held-out results.
