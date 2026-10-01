"""Freeze guards and append-only formal inference, separate from gold scoring."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from .extractor import ExtractionResponse, OpenRouterExtractor
from .pipeline import run_case
from .policy import Policy
from .schemas import Extraction
from .validation import validate_input

ROOT = Path(__file__).resolve().parents[2]
DATA_COMMIT = "28095bd3c9f407d15eca4fe28a4d6e2775b9fffb"
MANIFEST_COMMIT = "6531604a4d4347d40e89ec2ded6fc63da13c9383"
BRANCH_POINT = "35ea848b2da3d0b1a6245d18edb33f5dcf49e708"
MODEL = "openai/gpt-5.6-luna"
DEV_HASH = "39943bdf053298dc3a9e6c45b58d6b6d06fb136fc1e5c30519b5de62e6c14c70"
TEST_HASH = "9b3fe0451253d089923c42ca5071684ad3c9d1d5ce3ab6814a0af9bc9a511933"
SNAPSHOT_HASH = "6bc97f310cffef6b62c32e473455bb7c60766479521d6d1d96758db94681977a"
CORE_FILES = ("prompts/extraction_v1.md", "policies/policy_v1.json", "src/returnguard/schemas.py",
              "src/returnguard/validation.py", "src/returnguard/policy.py", "src/returnguard/acceptance.py",
              "src/returnguard/pipeline.py", "src/returnguard/extractor.py")
EVAL_FILES = ("src/returnguard/formal_eval.py", "src/returnguard/eval_metrics.py", "scripts/run_formal_eval.py")
BASELINE_FILES = ("baselines/keyword_rules_v1.json", "src/returnguard/keyword_baseline.py")


class HardStop(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str:
    return digest(path.read_bytes())


def encode(obj: object) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def jsonl(rows: list[dict]) -> bytes:
    return ("".join(json.dumps(r, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n" for r in rows)).encode()


def write_once(path: Path, data: bytes) -> None:
    """Identical repeat is harmless; changing a persisted record is a hard stop."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise HardStop(f"refusing to overwrite {path}")
        return
    with path.open("xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def read_json(path: Path) -> dict:
    return json.loads(path.read_bytes())


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_bytes().splitlines() if line.strip()]


def git_bytes(root: Path, ref: str, relative: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{ref}:{relative}"], cwd=root)


def verify_freeze(root: Path = ROOT) -> dict:
    base = root / "data/returnguard_synth_v1"
    manifest = read_json(base / "freeze_manifest.json")
    if manifest["git_commit"] != DATA_COMMIT or manifest["dev_sha256"] != DEV_HASH or manifest["test_sha256"] != TEST_HASH:
        raise HardStop("freeze identity mismatch")
    if manifest["project_level_approval"]["dataset_snapshot_sha256"] != SNAPSHOT_HASH:
        raise HardStop("approved snapshot mismatch")
    if (base / "freeze_manifest.json").read_bytes() != git_bytes(root, MANIFEST_COMMIT, "data/returnguard_synth_v1/freeze_manifest.json"):
        raise HardStop("manifest committed bytes mismatch")
    for name, expected in manifest["sha256"].items():
        path = base / name
        if file_hash(path) != expected or path.read_bytes() != git_bytes(root, DATA_COMMIT, str(path.relative_to(root))):
            raise HardStop(f"frozen bytes mismatch: {name}")
    for relative in CORE_FILES:
        if (root / relative).read_bytes() != git_bytes(root, BRANCH_POINT, relative):
            raise HardStop(f"frozen core changed: {relative}")
    return manifest


def project_inputs(rows: list[dict], split: str) -> list[dict]:
    projected = [{"case_id": r["case_id"], "split": split,
                  "input": {"order_facts": r["input"]["order_facts"],
                            "customer_message": r["input"]["customer_message"]}} for r in rows]
    projected.sort(key=lambda r: r["case_id"])
    for row in projected:
        validate_input(row["input"])
    if [r["case_id"] for r in projected] != [f"{split}_{i:03d}" for i in range(1, 91)]:
        raise HardStop("projection must contain the 90 expected case IDs exactly")
    return projected


def assert_no_test_outputs(out: Path) -> None:
    prohibited = [p for p in out.rglob("*") if p.is_file() and
                  (p.name.startswith(("test_predictions", "test_metrics", "baseline_test", "test_authorization"))
                   or "test_cases" in p.parts or "test_attempts" in p.parts)]
    if prohibited:
        raise HardStop("test formal outputs/authorization exist during Phase 3A")


def verify_file_map(root: Path, hashes: dict) -> None:
    for name, expected in hashes.items():
        if file_hash(root / name) != expected:
            raise HardStop(f"locked hash changed: {name}")


def verify_started_bindings(start: dict, config_hash: str, baseline_hash: str) -> None:
    if start["eval_config_sha256"] != config_hash or start["baseline_lock_sha256"] != baseline_hash:
        raise HardStop("config/baseline changed after first formal call")


def verify_config(root: Path, out: Path, *, committed: bool = True) -> tuple[dict, dict]:
    verify_freeze(root)
    config_path = out / "eval_config_v1.json"
    cfg = read_json(config_path)
    expected_hash = (out / "eval_config_v1.sha256").read_text().strip()
    if file_hash(config_path) != expected_hash:
        raise HardStop("eval config hash changed")
    required = {"eval_config_version": "formal_eval_v1.0", "gateway": "OpenRouter", "model_id": MODEL,
                "prompt_version": "extraction_v1", "schema_version": "case_v1.0", "policy_version": "policy_v1.0",
                "acceptance_version": "acceptance_v1.0", "dataset_version": "ReturnGuard-Synth-v1",
                "freeze_data_commit": DATA_COMMIT, "freeze_manifest_commit": MANIFEST_COMMIT,
                "dev_sha256": DEV_HASH, "test_sha256": TEST_HASH,
                "temperature": "omitted", "top_p": "omitted", "seed": "omitted", "tools": [],
                "retry_policy": "infrastructure_only_max_3_attempts", "case_order": "ascending_case_id"}
    if any(cfg.get(k) != v for k, v in required.items()):
        raise HardStop("formal request configuration mismatch")
    if file_hash(root / "prompts/extraction_v1.md") != cfg["prompt_sha256"]:
        raise HardStop("prompt hash mismatch")
    verify_file_map(root, cfg["implementation_sha256"])
    if cfg["structured_schema_sha256"] != digest(encode(Extraction.model_json_schema())):
        raise HardStop("structured schema runtime mismatch")
    for package, version in cfg["dependency_versions"].items():
        if importlib.metadata.version(package) != version:
            raise HardStop(f"dependency runtime mismatch: {package}")
    lock_path = out / "baseline_lock_v1.json"
    lock = read_json(lock_path)
    if file_hash(lock_path) != cfg["baseline_lock_sha256"] or lock.get("no_confidence_score") is not True:
        raise HardStop("baseline lock mismatch")
    verify_file_map(root, lock["source_sha256"])
    for name in BASELINE_FILES:
        if (root / name).read_bytes() != git_bytes(root, lock["implementation_commit"], name):
            raise HardStop("baseline implementation commit mismatch")
    if lock["pattern_file_sha256"] != file_hash(root / BASELINE_FILES[0]):
        raise HardStop("baseline pattern lock mismatch")
    if committed:
        for path in (config_path, out / "eval_config_v1.sha256", lock_path, out / "dev_inputs.jsonl"):
            if path.read_bytes() != git_bytes(root, "HEAD", str(path.relative_to(root))):
                raise HardStop("pre-call configuration/projection must be committed")
    inputs = read_rows(out / "dev_inputs.jsonl")
    if file_hash(out / "dev_inputs.jsonl") != cfg["dev_inputs_sha256"]:
        raise HardStop("input projection hash changed")
    if len(inputs) != 90 or inputs != project_inputs(inputs, "dev"):
        raise HardStop("input projection malformed or metadata-contaminated")
    start_path = out / "dev_run_start.json"
    if start_path.exists():
        start = read_json(start_path)
        verify_started_bindings(start, expected_hash, cfg["baseline_lock_sha256"])
    return cfg, lock


def verify_test_authorization(out: Path, cfg: dict) -> dict:
    path = out / "test_authorization.json"
    if not path.exists():
        raise HardStop("explicit locked-test authorization missing")
    auth = read_json(path)
    threshold = read_json(out / "threshold_lock_v1.json")
    expected = {"decision": "approved_for_locked_test", "test_dataset_sha256": TEST_HASH,
                "eval_config_sha256": file_hash(out / "eval_config_v1.json"),
                "threshold_lock_sha256": file_hash(out / "threshold_lock_v1.json"),
                "baseline_lock_sha256": file_hash(out / "baseline_lock_v1.json"),
                "locked_threshold_value": threshold["value"]}
    if any(auth.get(k) != v for k, v in expected.items()) or threshold["status"] != "provisional_locked_from_dev":
        raise HardStop("locked-test authorization binding mismatch")
    if threshold["eval_config_sha256"] != expected["eval_config_sha256"] or cfg["baseline_lock_sha256"] != expected["baseline_lock_sha256"]:
        raise HardStop("test config/lock mismatch")
    if not auth.get("authorization_source") or not auth.get("authorized_at"):
        raise HardStop("test authorization provenance missing")
    return auth


def retryable(exc: Exception) -> bool:
    import openai
    if isinstance(exc, (openai.APIConnectionError, openai.APITimeoutError, TimeoutError, ConnectionError)):
        return True
    code = getattr(exc, "status_code", None)
    return code == 429 or isinstance(code, int) and 500 <= code < 600


def dump_response(response: object) -> dict:
    if hasattr(response, "model_dump"):
        return response.model_dump(mode="json")
    return {"model": getattr(response, "model", None), "output_text": getattr(response, "output_text", None)}


class FormalCaller:
    """Use the existing adapter's request builder; persist response before parsing/scoring."""
    def __init__(self, client: object, prompt: Path, out: Path, sleep=time.sleep):
        self.client, self.prompt, self.out, self.sleep = client, prompt, out, sleep

    def collect(self, row: dict) -> tuple[ExtractionResponse | None, list[dict]]:
        case_id = row["case_id"]
        message = row["input"]["customer_message"]
        attempts = []
        request_binding = digest(encode({"model": MODEL, "prompt_sha256": file_hash(self.prompt),
                                         "message": message, "schema": Extraction.model_json_schema(),
                                         "tools": [], "sampling": "omitted"}))
        for attempt in range(1, 4):
            prefix = self.out / f"{row['split']}_attempts" / f"{case_id}_{attempt}"
            started_path = prefix.with_suffix(".started.json")
            outcome_path = prefix.with_suffix(".outcome.json")
            if outcome_path.exists():
                outcome = read_json(outcome_path)
                if outcome["request_binding_sha256"] != request_binding:
                    raise HardStop("resume request binding mismatch")
            else:
                if started_path.exists():
                    raise HardStop(f"ambiguous in-flight attempt {case_id}/{attempt}; do not resample")
                start = {"case_id": case_id, "attempt": attempt, "timestamp": now(),
                         "request_binding_sha256": request_binding}
                write_once(started_path, encode(start))
                begun = time.perf_counter()
                captured = {}
                def create(**kwargs):
                    response = self.client.responses.create(**kwargs)
                    payload = dump_response(response)
                    captured.update({**start, "status": "content_response", "response": payload,
                                     "output_text": getattr(response, "output_text", ""),
                                     "latency_seconds": time.perf_counter() - begun, "completed_at": now()})
                    write_once(outcome_path, encode(captured))
                    return response
                adapter = OpenRouterExtractor(prompt_path=self.prompt,
                              client=SimpleNamespace(responses=SimpleNamespace(create=create)))
                try:
                    adapter.extract(message)
                    outcome = captured
                except Exception as exc:
                    if outcome_path.exists():
                        # A response was durably stored, including unusable/refusal content.
                        outcome = read_json(outcome_path)
                    else:
                        outcome = {**start, "status": "infrastructure_error" if retryable(exc) else "fatal_error",
                                   "error_type": type(exc).__name__, "http_status": getattr(exc, "status_code", None),
                                   "latency_seconds": time.perf_counter() - begun, "completed_at": now()}
                        write_once(outcome_path, encode(outcome))
            attempts.append({k: v for k, v in outcome.items() if k not in {"response", "output_text"}})
            if outcome["status"] == "content_response":
                payload = outcome["response"]
                returned = payload.get("model")
                if returned not in {MODEL, "gpt-5.6-luna"}:
                    raise HardStop(f"model identity mismatch: requested {MODEL}, returned {returned}")
                text = outcome.get("output_text")
                try:
                    raw = json.loads(text)
                except (TypeError, json.JSONDecodeError):
                    raw = text
                usage = payload.get("usage") or {}
                return ExtractionResponse(raw=raw, model_name=MODEL, model_version=returned,
                     latency_seconds=outcome["latency_seconds"], input_tokens=usage.get("input_tokens"),
                     output_tokens=usage.get("output_tokens")), attempts
            if outcome["status"] == "fatal_error":
                raise HardStop(f"non-retryable gateway error at {case_id}: {outcome['error_type']} HTTP {outcome['http_status']}")
            if attempt < 3:
                self.sleep(attempt)
        return None, attempts


def predict(row: dict, caller: FormalCaller, cfg: dict, config_hash: str, run_id: str, *, threshold: float = 0.0) -> dict:
    # Projection validation and inference never open a dataset/gold file.
    if set(row) != {"case_id", "split", "input"} or set(row["input"]) != {"order_facts", "customer_message"}:
        raise HardStop("inference accepts input-only projections")
    validate_input(row["input"])
    response, attempts = caller.collect(row)
    provenance = {"case_id": row["case_id"], "split": row["split"], "formal_run_id": run_id,
                  "dataset_version": cfg["dataset_version"], "dataset_file_sha256": cfg[f"{row['split']}_sha256"],
                  "eval_config_version": cfg["eval_config_version"], "eval_config_sha256": config_hash,
                  "gateway": "OpenRouter", "model_id_requested": MODEL,
                  "prompt_version": "extraction_v1", "prompt_sha256": cfg["prompt_sha256"],
                  "request_attempts": len(attempts), "attempts": attempts,
                  "sampling_parameters": {"temperature": "omitted", "top_p": "omitted", "seed": "omitted"}}
    if response is None:
        return {**provenance, "model_id_returned": None, "upstream_provider": None,
                "evaluation_status": "execution_failure", "raw_structured_extraction": None,
                "validated_extraction": None, "derived_facts": None,
                "candidate_route": None, "candidate_rule_id": None, "candidate_review_reason": None,
                "case_support_score": None, "final_route": "manual_review", "review_reason": "execution_failure",
                "latency_seconds": sum(a["latency_seconds"] for a in attempts),
                "token_usage": {"input_tokens": None, "output_tokens": None},
                "reported_usage_cost_usd": None, "timestamp": attempts[-1]["completed_at"],
                "operating_point": "candidate_collection_only"}
    class StoredExtractor:
        def extract(self, message):
            return response
    record = run_case(row["input"], StoredExtractor(), Policy(), case_id=row["case_id"], threshold=threshold)
    prefix = caller.out / f"{row['split']}_attempts" / f"{row['case_id']}_{len(attempts)}.outcome.json"
    outcome = read_json(prefix)
    payload = outcome["response"]
    usage = payload.get("usage") or {}
    metadata = payload.get("metadata") or {}
    record.update(provenance, model_id_returned=response.model_version,
                  upstream_provider=payload.get("provider") or payload.get("provider_name") or metadata.get("provider"),
                  response_id=payload.get("id"), raw_gateway_response_file=str(prefix.relative_to(caller.out)),
                  reported_usage_cost_usd=usage.get("cost", payload.get("cost")),
                  evaluation_status="completed" if record["validated_extraction"] is not None else "validation_failure",
                  timestamp=outcome["completed_at"], latency_seconds=sum(a["latency_seconds"] for a in attempts),
                  operating_point="candidate_collection_only" if row["split"] == "dev" else "locked_test_threshold")
    return record


def collect_split(root: Path, out: Path, cfg: dict, *, split: str = "dev", client=None) -> None:
    verify_config(root, out)
    threshold = 0.0
    if split == "test":
        verify_test_authorization(out, cfg)
        threshold = read_json(out / "threshold_lock_v1.json")["value"]
    else:
        assert_no_test_outputs(out)
    config_hash = file_hash(out / "eval_config_v1.json")
    start_path = out / f"{split}_run_start.json"
    if not start_path.exists():
        write_once(start_path, encode({"formal_run_id": f"phase3_{split}_v1_{now()}", "started_at": now(),
                   "eval_config_sha256": config_hash, "baseline_lock_sha256": cfg["baseline_lock_sha256"],
                   "implementation_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
                   "github_run_id": os.environ.get("GITHUB_RUN_ID"),
                   "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
                   "dependency_versions": {p: importlib.metadata.version(p) for p in ("openai", "pydantic", "httpx")} }))
    start = read_json(start_path)
    if start["eval_config_sha256"] != config_hash:
        raise HardStop("config changed after formal run started")
    inputs = read_rows(out / f"{split}_inputs.jsonl")
    if split == "test" and inputs != project_inputs(inputs, "test"):
        raise HardStop("test projection contaminated")
    if client is None:
        from openai import OpenAI
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise HardStop("OPENROUTER_API_KEY missing")
        client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1", max_retries=0, timeout=120.0)
    caller = FormalCaller(client, root / "prompts/extraction_v1.md", out)
    for row in inputs:
        path = out / f"{split}_cases" / f"{row['case_id']}.json"
        if path.exists():
            existing = read_json(path)
            if existing["case_id"] != row["case_id"] or existing["eval_config_sha256"] != config_hash:
                raise HardStop("persisted prediction binding mismatch")
        else:
            record = predict(row, caller, cfg, config_hash, start["formal_run_id"], threshold=threshold)
            write_once(path, encode(record))
        print(f"persisted {row['case_id']}", flush=True)
    predictions = [read_json(out / f"{split}_cases" / f"{r['case_id']}.json") for r in inputs]
    raw_path = out / f"{split}_predictions_raw.jsonl"
    write_once(raw_path, jsonl(predictions))
    freeze_path = out / f"{split}_prediction_freeze.json"
    binding = {"case_n": len(predictions), "predictions_sha256": file_hash(raw_path), "eval_config_sha256": config_hash}
    if freeze_path.exists():
        if any(read_json(freeze_path).get(k) != v for k, v in binding.items()):
            raise HardStop("prediction freeze changed")
    else:
        write_once(freeze_path, encode({**binding, "created_at": now()}))
