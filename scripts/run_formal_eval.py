"""Prepare/verify committed locks, collect dev, then score offline. Test is gated."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from returnguard import formal_eval as f
from returnguard.eval_metrics import apply_threshold, join_gold, metrics, support_diagnostic, threshold_table
from returnguard.keyword_baseline import load_patterns, run_baseline
from returnguard.policy import Policy
from returnguard.schemas import Extraction

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/phase3"


def prepare() -> None:
    f.verify_freeze(ROOT)
    f.assert_no_test_outputs(OUT)
    if (OUT / "dev_run_start.json").exists():
        raise f.HardStop("prepare forbidden after formal run starts")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    for name in f.BASELINE_FILES + f.EVAL_FILES:
        if (ROOT / name).read_bytes() != f.git_bytes(ROOT, commit, name):
            raise f.HardStop("commit implementation before preparing baseline/config locks")
    lock = {"baseline_version": "keyword_rules_v1.0", "pattern_file_sha256": f.file_hash(ROOT / f.BASELINE_FILES[0]),
            "implementation_commit": commit, "policy_version": "policy_v1.0",
            "schema_value_space": "four frozen semantic values; baseline fields contain value and evidence only",
            "no_confidence_score": True, "no_threshold": True,
            "source_sha256": {p: f.file_hash(ROOT / p) for p in f.BASELINE_FILES}, "created_at": f.now()}
    if (OUT / "baseline_lock_v1.json").exists():
        lock = f.read_json(OUT / "baseline_lock_v1.json")
    f.write_once(OUT / "baseline_lock_v1.json", f.encode(lock))
    # Test bytes are verified, but Phase 3A prepares/consumes only the dev projection.
    inputs = f.project_inputs(f.read_rows(ROOT / "data/returnguard_synth_v1/dev.jsonl"), "dev")
    f.write_once(OUT / "dev_inputs.jsonl", f.jsonl(inputs))
    config = {"eval_config_version": "formal_eval_v1.0", "gateway": "OpenRouter", "model_id": f.MODEL,
              "prompt_version": "extraction_v1", "prompt_sha256": f.file_hash(ROOT / "prompts/extraction_v1.md"),
              "schema_version": "case_v1.0", "policy_version": "policy_v1.0", "acceptance_version": "acceptance_v1.0",
              "dataset_version": "ReturnGuard-Synth-v1", "freeze_data_commit": f.DATA_COMMIT,
              "freeze_manifest_commit": f.MANIFEST_COMMIT, "dev_sha256": f.DEV_HASH, "test_sha256": f.TEST_HASH,
              "temperature": "omitted", "top_p": "omitted", "seed": "omitted", "tools": [],
              "retry_policy": "infrastructure_only_max_3_attempts", "case_order": "ascending_case_id",
              "candidate_collection_threshold": 0.0, "candidate_collection_is_operating_result": False,
              "baseline_lock_sha256": f.file_hash(OUT / "baseline_lock_v1.json"),
              "dev_inputs_sha256": f.file_hash(OUT / "dev_inputs.jsonl"),
              "implementation_commit": commit,
              "implementation_sha256": {p: f.file_hash(ROOT / p) for p in f.EVAL_FILES + f.CORE_FILES},
              "structured_schema_sha256": f.digest(f.encode(Extraction.model_json_schema())),
              "dependency_versions": {p: importlib.metadata.version(p) for p in ("openai", "pydantic", "httpx")},
              "created_at": f.now()}
    if (OUT / "eval_config_v1.json").exists():
        config = f.read_json(OUT / "eval_config_v1.json")
    f.write_once(OUT / "eval_config_v1.json", f.encode(config))
    f.write_once(OUT / "eval_config_v1.sha256", (f.file_hash(OUT / "eval_config_v1.json") + "\n").encode())
    requirements = "".join(f"{p}=={v}\n" for p,v in config["dependency_versions"].items())
    f.write_once(OUT / "requirements_lock.txt", requirements.encode())
    f.verify_config(ROOT, OUT, committed=False)
    print("Prepared config, baseline lock and 90 input-only dev projections. Commit before live calls.")


def preflight(split: str = "dev") -> dict:
    config, _ = f.verify_config(ROOT, OUT)
    if split == "dev":
        f.assert_no_test_outputs(OUT)
    else:
        f.verify_test_authorization(OUT, config)
    print(f"{split} preflight passed; no model calls made.")
    return config


def aggregate_usage(rows: list[dict]) -> dict:
    costs = [r["reported_usage_cost_usd"] for r in rows if r.get("reported_usage_cost_usd") is not None]
    return {"model_request_attempts": sum(r["request_attempts"] for r in rows),
            "content_response_n": sum(r["evaluation_status"] != "execution_failure" for r in rows),
            "input_tokens": sum((r["token_usage"].get("input_tokens") or 0) for r in rows),
            "output_tokens": sum((r["token_usage"].get("output_tokens") or 0) for r in rows),
            "token_usage_available_n": sum(r["token_usage"].get("input_tokens") is not None for r in rows),
            "reported_api_cost_usd": sum(costs) if costs else None,
            "cost_available_n": len(costs), "cost_complete": len(costs) == len(rows),
            "cost_note": "Sum of reported response costs only; unavailable if absent; no pricing estimate.",
            "latency_seconds_total": sum(r["latency_seconds"] or 0 for r in rows),
            "returned_model_ids": sorted({r["model_id_returned"] for r in rows if r.get("model_id_returned")}),
            "upstream_providers": sorted({r["upstream_provider"] for r in rows if r.get("upstream_provider")})}


def analyze_dev() -> None:
    cfg = preflight()
    raw_path = OUT / "dev_predictions_raw.jsonl"
    frozen = f.read_json(OUT / "dev_prediction_freeze.json")
    if frozen["case_n"] != 90 or frozen["predictions_sha256"] != f.file_hash(raw_path):
        raise f.HardStop("raw predictions must be finalized and hashed before gold join")
    predictions = f.read_rows(raw_path)
    if any("gold" in r for r in predictions):
        raise f.HardStop("gold contamination in raw predictions")
    rows = join_gold(predictions, f.read_rows(ROOT / "data/returnguard_synth_v1/dev.jsonl"))
    diagnostic = support_diagnostic(rows)
    table, selected = threshold_table(rows)
    f.write_once(OUT / "dev_support_score_diagnostic.json", f.encode(diagnostic))
    f.write_once(OUT / "dev_threshold_table.json", f.encode({"selector_version": "threshold_selector_v1.0",
                 "acceptance_rule": "score >= threshold", "dev_n": 90, "points": table}))
    baseline = [run_baseline(row, Policy(), load_patterns()) for row in f.read_rows(OUT / "dev_inputs.jsonl")]
    f.write_once(OUT / "baseline_dev_predictions.jsonl", f.jsonl(baseline))
    bm = metrics(join_gold(baseline, f.read_rows(ROOT / "data/returnguard_synth_v1/dev.jsonl")))
    bm["error_capture"] = {"value": None, "display": "N/A: deterministic baseline has no confidence threshold"}
    f.write_once(OUT / "baseline_dev_metrics.json", f.encode(bm))
    usage = aggregate_usage(predictions)
    f.write_once(OUT / "dev_usage_summary.json", f.encode(usage))
    if selected is None:
        scored = rows
        dm = metrics(scored)
        dm["status"] = "NO_FEASIBLE_DEV_THRESHOLD"
        dm["operating_point"] = "candidate diagnostics only; no selected operating threshold"
    else:
        lock_path = OUT / "threshold_lock_v1.json"
        lock = {"threshold_version": "threshold_v1.0", "status": "provisional_locked_from_dev",
                "value": selected["threshold"],
                "selection_rule": "max coverage subject to selective_accuracy >= 0.90; tie higher accuracy; then higher threshold",
                "acceptance_rule": "score >= threshold", "dev_n": 90,
                "accepted_n": selected["accepted_n"], "correct_accepted_n": selected["correct_accepted_n"],
                "selective_accuracy": selected["selective_accuracy"], "coverage": selected["coverage"],
                "dev_dataset_sha256": f.DEV_HASH, "dev_predictions_sha256": f.file_hash(raw_path),
                "eval_config_sha256": f.file_hash(OUT / "eval_config_v1.json"), "prompt_sha256": cfg["prompt_sha256"],
                "baseline_lock_sha256": cfg["baseline_lock_sha256"],
                "selector_version": "threshold_selector_v1.0", "created_at": f.now()}
        if lock_path.exists():
            prior = f.read_json(lock_path)
            lock["created_at"] = prior["created_at"]
        f.write_once(lock_path, f.encode(lock))
        scored = [apply_threshold(r, selected["threshold"]) for r in rows]
        dm = metrics(scored, dev_selected=True)
        dm.update(status="DEV_COMPLETE_PENDING_GATE_3A_APPROVAL", provisional_threshold=selected["threshold"])
    f.write_once(OUT / "dev_predictions_scored.jsonl", f.jsonl(scored))
    f.write_once(OUT / "dev_metrics.json", f.encode(dm))
    f.assert_no_test_outputs(OUT)
    generate_handoff(dm, bm, usage, diagnostic, selected)
    print(json.dumps({"status": dm["status"], "selected": selected, "usage": usage}, ensure_ascii=False))


def show_proportion(p: dict) -> str:
    if p["value"] is None:
        return f"{p['numerator']}/{p['denominator']} (N/A)"
    interval = p["wilson_95"]
    return f"{p['numerator']}/{p['denominator']} ({100*p['value']:.2f}%; descriptive Wilson 95% {100*interval[0]:.2f}–{100*interval[1]:.2f}%)"


def generate_handoff(dm: dict, bm: dict, usage: dict, diagnostic: dict, selected: dict | None) -> None:
    artifacts = [p for p in sorted(OUT.rglob("*")) if p.is_file()]
    hashes = {str(p.relative_to(ROOT)): f.file_hash(p) for p in artifacts}
    f.write_once(OUT / "phase3a_artifact_hashes.json", f.encode(hashes)) if not (OUT / "phase3a_artifact_hashes.json").exists() else None
    d = dm["diagnostics"]
    text = f"""# Phase 3A development evaluation handoff

Status: **{dm['status']}**. Only the frozen development split was evaluated. No held-out test inference, scoring, baseline test outputs or test authorization exist. Stop at Gate 3A for design approval.

Authority: `docs/ReturnGuard_Phase3_Formal_Evaluation_Specification_v1.0.md`, particularly §33. Branch `phase3-evaluation-v1` originates at `{f.BRANCH_POINT}`. Frozen dataset snapshot `{f.SNAPSHOT_HASH}` and all committed freeze bytes were verified before live calls.

## Locked experiment provenance

Gateway OpenRouter; requested model `{f.MODEL}`; returned identities `{usage['returned_model_ids']}`. Prompt `extraction_v1`, strict `Extraction.model_json_schema()`, tools `[]`. Temperature/top_p/seed omitted. Cases processed in ascending case_id order with independent requests; only customer_message sent to the model. Trusted order facts enter deterministic Policy v1 after extraction. No prompt, core policy/schema/acceptance or dataset changes.

Configuration, baseline patterns, baseline lock and input-only dev projection were committed before the first dev call. `dev_run_start.json` binds that commit and the configuration/lock hashes. Every attempt has a started/outcome record; gateway responses were persisted before parsing, validation or gold scoring. Predictions were finalized and SHA-256 recorded in `dev_prediction_freeze.json` before the separate gold join. SDK automatic retries disabled; only infrastructure retries up to three attempts; no content resampling. On ambiguous in-flight requests resume hard-stops.

Model request attempts: **{usage['model_request_attempts']}**. Processed cases: **{dm['n']}**. Content responses: **{usage['content_response_n']}**. Validated/completed cases: **{d['evidence_valid_case_n']}**. Execution failures: **{d['execution_failure_n']}**. Hard validation failures: **{d['hard_validation_failure_n']}**. Evidence-valid cases: **{d['evidence_valid_case_n']}**. All failures remain in N=90.

## Extraction and candidate diagnostics

| Metric | Raw count and percentage |
|---|---|
"""
    for name, p in d["field_value_accuracy"].items():
        text += f"| {name} value accuracy | {p['numerator']}/{p['denominator']} ({100*p['value']:.2f}%) |\n"
    for label, p in (("All-four exact values", d["all_four_value_exact_accuracy"]),
                     ("Candidate route accuracy", d["candidate_route_accuracy"]),
                     ("Candidate rule-ID accuracy", d["candidate_rule_accuracy"])):
        text += f"| {label} | {p['numerator']}/{p['denominator']} ({100*p['value']:.2f}%) |\n"
    text += f"\nCandidate policy-required manual: {d['candidate_policy_required_manual_n']}; candidate auto routes: {d['candidate_auto_route_n']}. Missing candidates are not scored as correct. Value diagnostics use raw parsed values; hard-validation failures are reported separately. Exact evidence equality to gold is not an accuracy criterion.\n\n## Dev support-score diagnostic\n\nOnly auto-route candidates; descriptive ranking, not calibration or probability.\n\n| Score bin | n | Candidate errors | Error rate |\n|---|---:|---:|---:|\n"
    for b in diagnostic["bins"]:
        rate = f"{100*b['error_rate']:.2f}%" if b["error_rate"] is not None else "N/A"
        text += f"| {b['bin']} | {b['n']} | {b['candidate_route_errors']} | {rate} |\n"
    text += f"\nMedian scores: correct {diagnostic['median_correct']}; incorrect {diagnostic['median_incorrect']}. Range {diagnostic['min_score']}–{diagnostic['max_score']}; unique scores {diagnostic['unique_scores_n']}; correctness AUROC {diagnostic['auroc_correctness']}. No confidence model was fitted.\n\n## Provisional operating point\n\n"
    if selected:
        text += f"A provisional acceptance threshold **{selected['threshold']}** was selected on the 90-case development split by maximizing coverage subject to at least 90% selective accuracy, then locked before held-out evaluation. Acceptance is `score >= threshold`, without epsilon; ties resolve by higher accuracy and then higher threshold. The full unique-score table is in `dev_threshold_table.json`. Candidate collection at 0.0 is not the operating result.\n\n"
        for label, key in (("Coverage", "coverage"), ("Selective accuracy", "selective_accuracy"),
                           ("Manual-review recall", "manual_review_recall"), ("Three-class route accuracy", "route_accuracy")):
            text += f"- {label}: {show_proportion(dm[key])}.\n"
        text += f"\nDev 60% coverage target: {'met' if dm['dev_coverage_target_60_percent_met'] else 'not met'} (separate from threshold selection). Gold-manual cases auto-routed: {dm['gold_manual_auto_routed_n']}. Error capture: {dm['error_capture']['display']}; definition excludes policy/validation/execution abstentions from forced-choice candidates.\n\n"
        text += "Dev Wilson intervals are descriptive and optimistic because the threshold was selected on the same dev data. The threshold is provisional, not production-calibrated. No held-out success or project success is claimed.\n\n"
    else:
        text += "**NO_FEASIBLE_DEV_THRESHOLD**. No nonempty unique-score threshold achieved 90% selective accuracy. No threshold lock was created. Gate 3A does not pass; held-out test stays blocked. See the full threshold table. Candidate metrics are diagnostics, not a selected operating result.\n\n"
    text += "Abstention decomposition (count / 90):\n\n"
    for reason, count in dm["abstentions"].items():
        text += f"- {reason}: {count['n']}/90 ({100*count['rate']:.2f}%).\n"
    text += "\nFinal confusion matrix (gold rows, predicted columns):\n\n| Gold | eligible | ineligible | manual_review |\n|---|---:|---:|---:|\n"
    for route, values in dm["confusion_matrix_gold_rows_final_columns"].items():
        text += f"| {route} | {values['eligible']} | {values['ineligible']} | {values['manual_review']} |\n"
    text += "\n## Locked Keyword+Rules dev baseline\n\nOne conservative deterministic operating point, no confidence score or threshold, exact-span evidence validator, unchanged Policy v1. Patterns come from the specification; no test-aware or LLM-aware tuning.\n\n"
    for label, key in (("Coverage", "coverage"), ("Selective accuracy", "selective_accuracy"),
                       ("Route accuracy", "route_accuracy"), ("Manual recall", "manual_review_recall")):
        text += f"- {label}: {show_proportion(bm[key])}.\n"
    text += f"\nBaseline gold-manual auto-routed: {bm['gold_manual_auto_routed_n']}; abstentions {json.dumps(bm['abstentions'])}. Full confusion matrix and diagnostics are in `baseline_dev_metrics.json`. This is dev only; the predefined held-out comparison rule is reserved for Phase 3B.\n\n## Usage and reproducibility\n\nReported input/output tokens: {usage['input_tokens']}/{usage['output_tokens']} (available for {usage['token_usage_available_n']}/90). Reported API cost USD: {usage['reported_api_cost_usd']} (available for {usage['cost_available_n']}/90; complete={usage['cost_complete']}). No fresh pricing estimate substituted. Provider metadata, where exposed: {usage['upstream_providers']}. Model identity is an alias and does not prove an immutable underlying revision. Dependency versions are recorded in the pre-call config.\n\nAll raw/scored predictions, attempts, locks and metrics are in `results/phase3/`. `phase3a_artifact_hashes.json` lists exact SHA-256 values. Key hashes:\n\n"
    for name in ("eval_config_v1.json", "baseline_lock_v1.json", "dev_inputs.jsonl", "dev_predictions_raw.jsonl", "dev_predictions_scored.jsonl", "threshold_lock_v1.json"):
        if (OUT / name).exists():
            text += f"- `{name}`: `{f.file_hash(OUT / name)}`\n"
    text += "\n## Gate 3A review\n\nVerify run provenance, immutable config/prompt/baseline, support diagnostic, complete threshold table, provisional threshold lock, counts/metrics and absence of test outputs. Work has stopped here. No test_authorization.json is created by Phase 3A. The test runner requires explicit matching authorization before a model call.\n"
    f.write_once(ROOT / "docs/Phase3A_Dev_Evaluation_Handoff.md", text.encode())


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("prepare", "preflight", "dev", "analyze-dev", "test"))
    args = p.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command == "preflight":
        preflight()
    elif args.command == "dev":
        cfg = preflight()
        f.collect_split(ROOT, OUT, cfg)
    elif args.command == "analyze-dev":
        analyze_dev()
    else:
        # Hard gate before even preparing a held-out input projection.
        cfg = preflight("test")
        projection = f.project_inputs(f.read_rows(ROOT / "data/returnguard_synth_v1/test.jsonl"), "test")
        f.write_once(OUT / "test_inputs.jsonl", f.jsonl(projection))
        f.collect_split(ROOT, OUT, cfg, split="test")


if __name__ == "__main__":
    main()
