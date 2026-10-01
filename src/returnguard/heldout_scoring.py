"""Additive, offline-only Phase 3B scoring under the approved Phase 3A locks."""
from __future__ import annotations

from fractions import Fraction

from . import formal_eval as f
from .eval_metrics import FIELDS, ROUTES, apply_threshold, metrics

VERSION = "heldout_scoring_v1.0"
APPROVED = {
    "data/returnguard_synth_v1/test.jsonl": f.TEST_HASH,
    "results/phase3/eval_config_v1.json": "164ad582216ccb7a571f179eb7622e8274ff2e2506f9aefff668a4992ac5eddf",
    "results/phase3/threshold_lock_v1.json": "8be8a8084d288561c2e939631e03edfd78dd7fd3a05373a92d36ec6ce18b9e93",
    "results/phase3/baseline_lock_v1.json": "63aacdbd263cae2c8a597401c60189d9c3e7b66b87faf01976e8c33f104bb2cf",
}
SCORER_FILES = ("src/returnguard/heldout_scoring.py", "scripts/score_locked_test.py",
                ".github/workflows/phase3-test-eval.yml")


def verify_locks(root, out, *, committed=True):
    f.verify_file_map(root, APPROVED)
    cfg, baseline = f.verify_config(root, out, committed=committed)
    auth = f.verify_test_authorization(out, cfg)
    if auth["locked_threshold_value"] != .86:
        raise f.HardStop("approved threshold must remain exactly 0.86")
    f.verify_file_map(root, f.read_json(out / "phase3a_package_manifest.json")["sha256"])
    scorer_lock = f.read_json(out / "phase3b_scorer_lock.json")
    if f.file_hash(out / "phase3b_scorer_lock.json") != auth["scorer_lock_sha256"]:
        raise f.HardStop("pre-test scorer lock mismatch")
    f.verify_file_map(root, scorer_lock["source_sha256"])
    if f.file_hash(out / "test_inputs.jsonl") != auth["test_inputs_sha256"]:
        raise f.HardStop("test projection hash mismatch")
    inputs = f.read_rows(out / "test_inputs.jsonl")
    if inputs != f.project_inputs(inputs, "test"):
        raise f.HardStop("test projection metadata contamination")
    if committed:
        for path in (out / "test_authorization.json", out / "test_inputs.jsonl", out / "phase3b_scorer_lock.json"):
            if path.read_bytes() != f.git_bytes(root, "HEAD", str(path.relative_to(root))):
                raise f.HardStop("test authorization/projection/scorer lock must be committed")
    return cfg, baseline, auth


def verified_raw(out, auth, *, expected_n=90):
    """Hard stop before gold may be opened unless raw predictions are complete/frozen."""
    path = out / "test_predictions_raw.jsonl"
    freeze_path = out / "test_prediction_freeze.json"
    if not path.exists() or not freeze_path.exists():
        raise f.HardStop("test raw predictions must be persisted and frozen before gold scoring")
    frozen = f.read_json(freeze_path)
    if frozen["case_n"] != expected_n or frozen["predictions_sha256"] != f.file_hash(path):
        raise f.HardStop("frozen raw prediction count/hash mismatch")
    if frozen["eval_config_sha256"] != auth["eval_config_sha256"]:
        raise f.HardStop("test prediction/config binding mismatch")
    rows = f.read_rows(path)
    if [r["case_id"] for r in rows] != [f"test_{i:03d}" for i in range(1, expected_n+1)]:
        raise f.HardStop("raw predictions must cover test cases exactly once in ascending order")
    for row in rows:
        if "gold" in row or row["split"] != "test" or row["eval_config_sha256"] != auth["eval_config_sha256"]:
            raise f.HardStop("gold/split/config contamination in raw test predictions")
        if row["dataset_file_sha256"] != auth["test_dataset_sha256"]:
            raise f.HardStop("prediction dataset binding mismatch")
        if row["model_id_requested"] != f.MODEL or row.get("model_id_returned") not in {None, f.MODEL, "gpt-5.6-luna"}:
            raise f.HardStop("test model identity mismatch")
        if not 1 <= row["request_attempts"] <= 3:
            raise f.HardStop("request attempt cap exceeded")
        replay = apply_threshold(row, auth["locked_threshold_value"])
        if any(row[k] != replay[k] for k in ("final_route", "review_reason")):
            raise f.HardStop("raw test final route does not follow the locked threshold")
        if row["evaluation_status"] != "execution_failure" and row.get("threshold_value") != auth["locked_threshold_value"]:
            raise f.HardStop("test record threshold mismatch")
    return rows


def heldout_metrics(rows, *, baseline=False):
    result = metrics(rows)
    coverage_met = result.pop("dev_coverage_target_60_percent_met")
    result.update(split="test", scorer_version=VERSION, coverage_target_60_percent_met=coverage_met)
    if baseline:
        result["error_capture"] = {"value": None, "display": "N/A: deterministic baseline has no confidence threshold"}
    else:
        result["locked_threshold"] = .86
        result["threshold_status"] = "provisional_locked_from_dev"
    return result


def compare_baseline(returnguard, baseline):
    safe_r = returnguard["selective_accuracy_constraint_met"]
    safe_b = baseline["selective_accuracy_constraint_met"]
    r = Fraction(returnguard["auto_routed_n"], returnguard["n"])
    b = Fraction(baseline["auto_routed_n"], baseline["n"])
    difference = r-b
    return {
        "baseline_safety_constraint_met": safe_b,
        "returnguard_safety_constraint_met": safe_r,
        "coverage_difference_percentage_points": float(difference*100) if safe_b else None,
        "descriptive_raw_coverage_difference_percentage_points": float(difference*100),
        "safe_comparison_valid": safe_b and safe_r,
        "coverage_gap_target_10_pp_met": difference >= Fraction(1,10) if safe_b else None,
        "safe_coverage_gain_target_met": safe_b and safe_r and difference >= Fraction(1,10),
        "statement": (
            "The Keyword+Rules baseline met the 90% selective-accuracy constraint; coverage was therefore compared at the predefined safety requirement."
            if safe_b else
            "The Keyword+Rules baseline did not satisfy the predefined 90% selective-accuracy constraint at its conservative operating point. Its raw coverage and accuracy are descriptive; no equivalent safe operating point or post-hoc threshold is claimed."
        ),
        "returnguard_safety_note": "ReturnGuard also met the safety constraint." if safe_r else "ReturnGuard did not meet the safety constraint; a raw coverage gap is not a safe superiority claim.",
    }


def raw_values(raw):
    return {name: raw.get(name, {}).get("value") if isinstance(raw,dict) and isinstance(raw.get(name),dict) else None for name in FIELDS}


def error_analysis(rows, inputs, baseline_rows):
    """All critical failures + fixed representative selection; no model judge."""
    inputs_by_id = {r["case_id"]: r["input"] for r in inputs}
    auto_errors = []
    validation = []
    execution = []
    unsafe = []
    low = []
    mismatch = []
    over = []
    inspected = []
    representatives = {name: [] for name in FIELDS}
    for row in rows:
        case_id = row["case_id"]
        predicted = raw_values(row.get("raw_structured_extraction"))
        expected = {name: row["gold"]["extraction"][name]["value"] for name in FIELDS}
        fields = [name for name in FIELDS if predicted[name] != expected[name]]
        gold_route = row["gold"]["decision"]["route"]
        is_auto_error = row["final_route"] in ROUTES[:2] and row["final_route"] != gold_route
        is_unsafe = gold_route == "manual_review" and row["final_route"] in ROUTES[:2]
        is_over = gold_route in ROUTES[:2] and row["final_route"] == "manual_review"
        if is_auto_error: auto_errors.append(case_id)
        if is_unsafe: unsafe.append(case_id)
        if is_over: over.append(case_id)
        if row["evaluation_status"] == "validation_failure": validation.append(case_id)
        if row["evaluation_status"] == "execution_failure": execution.append(case_id)
        if row["review_reason"] == "low_confidence": low.append(case_id)
        if fields:
            mismatch.append(case_id)
            for name in fields:
                if len(representatives[name])<3: representatives[name].append(case_id)
        if not (is_auto_error or is_unsafe or is_over or fields or row["evaluation_status"] != "completed" or row["review_reason"] == "low_confidence"):
            continue
        categories=[]
        if row["evaluation_status"] == "execution_failure": categories.append("API execution failure")
        elif row["evaluation_status"] == "validation_failure": categories.append("evidence/validation failure")
        else:
            categories += [{"return_reason":"return_reason extraction error", "tag_status":"tag extraction error", "damage_or_stain":"damage/stain extraction error", "use_beyond_inspection":"use extraction error"}[name] for name in fields]
            if fields and row.get("candidate_rule_id") != row["gold"]["decision"]["rule_id"]:
                categories.append("policy consequence of extraction error")
        if is_unsafe: categories.append("unsafe automation of gold manual case")
        if is_over:
            if row["review_reason"] == "low_confidence" and row["candidate_route"] == gold_route:
                categories.append("over-abstention / low-confidence false alarm")
            elif row["review_reason"] == "policy_required":
                categories.append("over-abstention / policy manual decision")
        if row["review_reason"] == "low_confidence" and row["candidate_route"] != gold_route:
            categories.append("candidate error captured by low-confidence abstention")
        inspected.append({"case_id":case_id,"input":inputs_by_id[case_id],
            "gold_route":gold_route,"gold_rule_id":row["gold"]["decision"]["rule_id"],
            "candidate_route":row.get("candidate_route"),"candidate_rule_id":row.get("candidate_rule_id"),
            "final_route":row["final_route"],"review_reason":row["review_reason"],
            "case_support_score":row.get("case_support_score"), "locked_threshold":.86,
            "evaluation_status":row["evaluation_status"],"field_value_mismatches":fields,
            "predicted_values":predicted,"gold_values":expected,
            "predicted_extraction":row.get("raw_structured_extraction"),
            "gold_extraction":row["gold"]["extraction"],"derived_facts":row.get("derived_facts"),
            "validation_error":row.get("validation_error"),"categories":categories,
            "label_method":"deterministic frozen-gold value/route/rule comparisons; descriptive case inspection only; no model judge"})
    baseline_errors = [{"case_id":r["case_id"],"final_route":r["final_route"],"gold_route":r["gold"]["decision"]["route"],
                        "input":inputs_by_id[r["case_id"]],"predicted_extraction":r["raw_structured_extraction"],
                        "gold_extraction":r["gold"]["extraction"],"candidate_rule_id":r["candidate_rule_id"],
                        "gold_rule_id":r["gold"]["decision"]["rule_id"]}
                       for r in baseline_rows if r["final_route"] in ROUTES[:2] and r["final_route"] != r["gold"]["decision"]["route"]]
    return {"scope":"test only; descriptive after finalized raw predictions and metrics; no corrections or retuning",
            "selection_rule":"all auto-route errors, all validation/execution failures, all unsafe gold-manual auto routes, all field-value mismatches and all over-abstentions; low-confidence sample first 5 ascending IDs; first 3 mismatches per field are representatives",
            "auto_routing_error_ids":auto_errors,"validation_failure_ids":validation,"execution_failure_ids":execution,
            "gold_manual_auto_routed_ids":unsafe,"over_abstention_ids":over,"field_value_error_ids":mismatch,
            "low_confidence_abstention_ids":low,"low_confidence_sample_ids":low[:5],
            "representative_field_error_ids":representatives,"inspected_cases":inspected,
            "baseline_auto_routing_errors":baseline_errors,"model_judge_calls":0,"results_altered":False}


def aggregate_usage(rows):
    costs = [r["reported_usage_cost_usd"] for r in rows if r.get("reported_usage_cost_usd") is not None]
    return {"model_request_attempts":sum(r["request_attempts"] for r in rows),
            "content_response_n":sum(r["evaluation_status"]!="execution_failure" for r in rows),
            "execution_failure_n":sum(r["evaluation_status"]=="execution_failure" for r in rows),
            "validation_failure_n":sum(r["evaluation_status"]=="validation_failure" for r in rows),
            "infrastructure_retry_n":sum(r["request_attempts"]-1 for r in rows),
            "input_tokens":sum(r["token_usage"].get("input_tokens") or 0 for r in rows),
            "output_tokens":sum(r["token_usage"].get("output_tokens") or 0 for r in rows),
            "token_usage_available_n":sum(r["token_usage"].get("input_tokens") is not None for r in rows),
            "reported_api_cost_usd":sum(costs) if costs else None,"cost_available_n":len(costs),
            "content_response_cost_complete":len(costs)==sum(r["evaluation_status"]!="execution_failure" for r in rows),
            "cost_complete":len(costs)==len(rows) and all(r["request_attempts"]==1 for r in rows),
            "cost_note":"Only directly returned response costs; infrastructure attempts without usage metadata have unknown cost; no price estimate substituted.",
            "latency_seconds_total":sum(r.get("latency_seconds") or 0 for r in rows),
            "returned_model_ids":sorted({r["model_id_returned"] for r in rows if r.get("model_id_returned")}),
            "upstream_providers":sorted({r["upstream_provider"] for r in rows if r.get("upstream_provider")})}
