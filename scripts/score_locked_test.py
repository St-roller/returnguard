"""Offline Phase 3B scoring/handoff. Uses the unchanged locked inference runner."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from returnguard import formal_eval as f
from returnguard import heldout_scoring as h
from returnguard.eval_metrics import join_gold
from returnguard.keyword_baseline import load_patterns,run_baseline
from returnguard.policy import Policy

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"results/phase3"


def rate(p):
    if p["value"] is None:return f"{p['numerator']}/{p['denominator']} (N/A)"
    lo,hi=p["wilson_95"]
    return f"{p['numerator']}/{p['denominator']} ({100*p['value']:.2f}%; Wilson 95% {100*lo:.2f}–{100*hi:.2f}%)"


def preflight():
    cfg,baseline,auth=h.verify_locks(ROOT,OUT)
    print("Phase 3B authorization, all approved hashes, immutable Phase 3A files, scorer lock and 90-case projection verified; model calls: 0.")
    return cfg,baseline,auth


def score():
    cfg,baseline_lock,auth=preflight()
    raw=h.verified_raw(OUT,auth)
    raw_hash=f.file_hash(OUT/"test_predictions_raw.jsonl")
    start_path=OUT/"test_scoring_start.json"
    binding={"raw_predictions_sha256":raw_hash,"eval_config_sha256":auth["eval_config_sha256"],
             "threshold_lock_sha256":auth["threshold_lock_sha256"],"baseline_lock_sha256":auth["baseline_lock_sha256"],
             "test_authorization_sha256":f.file_hash(OUT/"test_authorization.json"),"scorer_version":h.VERSION}
    if start_path.exists():
        if any(f.read_json(start_path).get(k)!=v for k,v in binding.items()):raise f.HardStop("scoring binding changed")
    else:f.write_once(start_path,f.encode({**binding,"started_at":f.now(),"raw_frozen_before_gold_join":True}))
    # First gold join occurs only after the persisted raw-file freeze has passed.
    cases=f.read_rows(ROOT/"data/returnguard_synth_v1/test.jsonl")
    scored=join_gold(raw,cases)
    f.write_once(OUT/"test_predictions_scored.jsonl",f.jsonl(scored))
    tm=h.heldout_metrics(scored)
    f.write_once(OUT/"test_metrics.json",f.encode(tm))
    inputs=f.read_rows(OUT/"test_inputs.jsonl")
    baseline=[run_baseline(r,Policy(),load_patterns()) for r in inputs]
    f.write_once(OUT/"baseline_test_predictions.jsonl",f.jsonl(baseline))
    baseline_scored=join_gold(baseline,cases)
    bm=h.heldout_metrics(baseline_scored,baseline=True)
    f.write_once(OUT/"baseline_test_metrics.json",f.encode(bm))
    # Error analysis runs after both sets of locked metrics are computed/persisted.
    errors=h.error_analysis(scored,inputs,baseline_scored)
    f.write_once(OUT/"error_analysis.json",f.encode(errors))
    test_usage=h.aggregate_usage(raw)
    dev_usage=h.aggregate_usage(f.read_rows(OUT/"dev_predictions_raw.jsonl"))
    total_usage=h.aggregate_usage(f.read_rows(OUT/"dev_predictions_raw.jsonl")+raw)
    f.write_once(OUT/"test_usage_summary.json",f.encode(test_usage))
    comparison=h.compare_baseline(tm,bm)
    hashes={name:f.file_hash(OUT/name) for name in (
        "eval_config_v1.json","threshold_lock_v1.json","baseline_lock_v1.json","test_authorization.json",
        "phase3b_scorer_lock.json","dev_inputs.jsonl","test_inputs.jsonl","dev_predictions_raw.jsonl",
        "dev_predictions_scored.jsonl","test_predictions_raw.jsonl","test_predictions_scored.jsonl",
        "baseline_dev_predictions.jsonl","baseline_test_predictions.jsonl","dev_metrics.json","test_metrics.json",
        "baseline_dev_metrics.json","baseline_test_metrics.json","error_analysis.json")}
    summary={"status":"PHASE_3_FORMAL_EVALUATION_CLOSED","gate_3b":"TEST_COMPLETE",
        "scorer_version":h.VERSION,"dataset_version":"ReturnGuard-Synth-v1", "dev_dataset_sha256":f.DEV_HASH,
        "test_dataset_sha256":f.TEST_HASH,"eval_config_sha256":auth["eval_config_sha256"],
        "model_id":cfg["model_id"],"gateway":cfg["gateway"],"prompt_version":cfg["prompt_version"],"prompt_sha256":cfg["prompt_sha256"],
        "threshold_value":auth["locked_threshold_value"],"threshold_status":"provisional_locked_from_dev",
        "threshold_lock_sha256":auth["threshold_lock_sha256"],"baseline_lock_sha256":auth["baseline_lock_sha256"],
        "test_authorization_sha256":hashes["test_authorization.json"],
        "dev_metrics":f.read_json(OUT/"dev_metrics.json"),"test_metrics":tm,
        "baseline_dev_metrics":f.read_json(OUT/"baseline_dev_metrics.json"),"baseline_test_metrics":bm,
        "baseline_comparison":comparison,"test_target_outcomes":{
            "selective_accuracy_90_percent":"met" if tm["selective_accuracy_constraint_met"] else "not_met",
            "coverage_60_percent":"met" if tm["coverage_target_60_percent_met"] else "not_met",
            "safe_baseline_coverage_gain_10_pp":"met" if comparison["safe_coverage_gain_target_met"] else "not_met",
            "baseline_gain_comparison_applicable":comparison["baseline_safety_constraint_met"]},
        "usage":{"dev":dev_usage,"test":test_usage,"total":total_usage},"prediction_and_artifact_hashes":hashes,
        "test_run_provenance":f.read_json(OUT/"test_run_start.json"),
        "error_analysis_counts":{k:len(errors[k]) for k in (
            "auto_routing_error_ids","validation_failure_ids","execution_failure_ids","gold_manual_auto_routed_ids",
            "field_value_error_ids","over_abstention_ids","low_confidence_abstention_ids")},
        "test_prompt_model_policy_schema_baseline_threshold_retuned":False,
        "final_report_readme_dataset_docs_demo_updated":False,
        "limitations":["Small synthetic balanced 90-case splits; intervals are descriptive; no statistical significance claim.",
                       "Dev threshold selected on the same dev cases; dev intervals are optimistic with respect to selection.",
                       "Support scores are self-assessments for ranking/abstention, not calibrated probabilities.",
                       "Returned model alias may not identify an immutable upstream revision; provider recorded only where exposed."]}
    f.write_once(OUT/"phase3_summary.json",f.encode(summary))
    write_handoff(summary,errors)
    # Close with a final immutability check; scoring is never allowed to retune locks.
    h.verify_locks(ROOT,OUT)
    if f.file_hash(OUT/"test_predictions_raw.jsonl")!=raw_hash:raise f.HardStop("raw predictions changed during scoring")
    print(json.dumps({"status":summary["status"],"test_coverage":tm["coverage"],"test_selective_accuracy":tm["selective_accuracy"],
                     "baseline_comparison":comparison,"test_usage":test_usage},ensure_ascii=False))


def write_handoff(summary,errors):
    tm,bm=summary["test_metrics"],summary["baseline_test_metrics"]
    comp=summary["baseline_comparison"];u=summary["usage"];d=tm["diagnostics"]
    text=f"""# ReturnGuard Phase 3 formal evaluation handoff

Status: **PHASE_3_FORMAL_EVALUATION_CLOSED — TEST_COMPLETE**. This is the formal evaluation handoff, not a rewrite of the course final report, README, dataset documentation or demo. Those materials remain deferred under the latest user instruction.

The 90-case held-out split was evaluated once under the locked model, prompt, policy, schema, acceptance aggregation and threshold. Gate 3A was explicitly approved by the user on 1 October 2026. `test_authorization.json` binds the four approved hashes and threshold 0.86; `test_run_start.json` binds the execution commit, run ID and dependency versions. `test_scoring_start.json` records the finalized raw prediction hash before gold joining.

A provisional acceptance threshold was selected on the 90-case development split by maximizing coverage subject to at least 90% selective accuracy, then locked before held-out evaluation. The threshold remains **0.86**, acceptance `score >= threshold`, without epsilon. No threshold selection was performed on test.

Gateway OpenRouter; model `{summary['model_id']}`; exact `extraction_v1` prompt hash `{summary['prompt_sha256']}`. Strict extraction schema; tools `[]`; temperature/top_p/seed omitted. Ascending case_id, independent requests, model receives Chinese customer_message only. Trusted order facts enter deterministic code after extraction. Input projections contain no gold/English/review/design metadata. Only infrastructure failures are retried, at most 3 attempts; content/validation failures never trigger resampling. Every attempt and raw gateway response is retained before parsing/scoring. Completed content responses are immutable.

## Test operating point and targets

Raw counts are reported alongside percentages because the development and held-out samples are small. Wilson 95% intervals are descriptive, not significance tests. Dev intervals remain optimistic with respect to threshold selection on the same data.

| Test metric | ReturnGuard | Locked Keyword+Rules |
|---|---|---|
"""
    for label,key in (("Coverage","coverage"),("Selective accuracy","selective_accuracy"),
                      ("Three-class route accuracy","route_accuracy"),("Manual-review recall","manual_review_recall")):
        text+=f"| {label} | {rate(tm[key])} | {rate(bm[key])} |\n"
    text+=f"\nGold-manual cases auto-routed: ReturnGuard **{tm['gold_manual_auto_routed_n']}**, baseline **{bm['gold_manual_auto_routed_n']}**. Error capture: **{tm['error_capture']['display']}** (captured low-confidence candidate errors / all validation-passed, execution-completed auto-candidate errors; policy/validation/execution abstentions are not forced through).\n\n"
    text+=f"- 90% selective-accuracy constraint: **{summary['test_target_outcomes']['selective_accuracy_90_percent']}**.\n- 60% held-out coverage target: **{summary['test_target_outcomes']['coverage_60_percent']}**.\n\n"
    text+=comp["statement"]+" "+comp["returnguard_safety_note"]+"\n\n"
    if comp["baseline_safety_constraint_met"]:
        text+=f"Coverage difference: **{comp['coverage_difference_percentage_points']:.2f} percentage points**. Coverage gap >=10 pp: {comp['coverage_gap_target_10_pp_met']}; combined safe coverage gain target: {comp['safe_coverage_gain_target_met']}. A safe comparison also requires ReturnGuard to meet the safety constraint.\n\n"
    else:
        text+=f"Raw coverage difference (descriptive only): {comp['descriptive_raw_coverage_difference_percentage_points']:.2f} pp. No post-hoc baseline threshold or alternative safe point was introduced.\n\n"
    text+="Abstention decomposition (counts / 90):\n\n| Reason | ReturnGuard | Keyword+Rules |\n|---|---:|---:|\n"
    for key in tm["abstentions"]:
        text+=f"| {key} | {tm['abstentions'][key]['n']}/90 ({100*tm['abstentions'][key]['rate']:.2f}%) | {bm['abstentions'][key]['n']}/90 ({100*bm['abstentions'][key]['rate']:.2f}%) |\n"
    for label,m in (("ReturnGuard",tm),("Keyword+Rules",bm)):
        text+=f"\n{label} final confusion matrix (gold rows, final columns):\n\n| Gold | eligible | ineligible | manual_review |\n|---|---:|---:|---:|\n"
        for g,v in m["confusion_matrix_gold_rows_final_columns"].items():
            text+=f"| {g} | {v['eligible']} | {v['ineligible']} | {v['manual_review']} |\n"
    text+="\n## Extraction and candidate diagnostics\n\n| Metric | Count / 90 |\n|---|---|\n"
    for name,p in d["field_value_accuracy"].items():text+=f"| {name} value accuracy | {p['numerator']}/90 ({100*p['value']:.2f}%) |\n"
    for label,key in (("All-four values exact","all_four_value_exact_accuracy"),("Candidate route accuracy","candidate_route_accuracy"),("Candidate rule-ID accuracy","candidate_rule_accuracy")):
        p=d[key];text+=f"| {label} | {p['numerator']}/90 ({100*p['value']:.2f}%) |\n"
    text+=f"\nEvidence-valid cases {d['evidence_valid_case_n']}/90; hard validation failures {d['hard_validation_failure_n']}/90; execution failures {d['execution_failure_n']}/90. Candidate auto routes {d['candidate_auto_route_n']}; candidate policy manual routes {d['candidate_policy_required_manual_n']}. Missing candidates do not count as correct. Exact gold evidence equality is not a primary accuracy metric.\n\n"
    text+="Support scores were treated as model self-assessments for ranking and abstention, not as calibrated probabilities. The support-score diagnostic and threshold table were dev-only and remain unchanged. See `dev_support_score_diagnostic.json` and `dev_threshold_table.json`; no test confidence fitting or test threshold enumeration occurred.\n\n"
    text+="## Descriptive error analysis\n\nAll automatic-routing errors, validation failures, execution failures, unsafe gold-manual auto routes, extraction-value mismatches and over-abstentions are captured in `error_analysis.json`, with exact Chinese input, predicted/gold values and evidence, route/rule consequences and deterministic category labels. Low-confidence sample selection is the first five ascending IDs; field representatives are the first three mismatches per field. No LLM judge was used as authoritative labeler.\n\n"
    for key in ("auto_routing_error_ids","validation_failure_ids","execution_failure_ids","gold_manual_auto_routed_ids","over_abstention_ids","field_value_error_ids","low_confidence_sample_ids"):
        text+=f"- {key}: {len(errors[key])}; {', '.join(errors[key]) or 'none'}.\n"
    text+="\nNo benchmark repair, label change, prompt change, baseline tuning, response resampling or threshold retuning occurred after observing test. Descriptive explanations do not change metrics.\n\n## Usage and reproducibility\n\n| Split | Request attempts | Content responses | Input tokens | Output tokens | Reported response cost USD |\n|---|---:|---:|---:|---:|---:|\n"
    for split,v in u.items():
        cost=f"{v['reported_api_cost_usd']:.8f}" if v["reported_api_cost_usd"] is not None else "unavailable"
        text+=f"| {split} | {v['model_request_attempts']} | {v['content_response_n']} | {v['input_tokens']} | {v['output_tokens']} | {cost} |\n"
    text+=f"\nTest infrastructure retries {u['test']['infrastructure_retry_n']}; validation failures {u['test']['validation_failure_n']}; execution failures {u['test']['execution_failure_n']}. Test cost available for {u['test']['cost_available_n']} content responses; full returned-cost coverage={u['test']['cost_complete']}. Failed infrastructure attempts without billing metadata have unknown cost. No fresh pricing estimate is substituted.\n\nReturned model identities: {u['total']['returned_model_ids']}; exposed upstream providers: {u['total']['upstream_providers'] or 'unavailable'}. The alias does not establish an immutable underlying revision.\n\n"
    dm=summary["dev_metrics"]
    text+=f"Dev remains: coverage {rate(dm['coverage'])}, selective accuracy {rate(dm['selective_accuracy'])}, manual recall {rate(dm['manual_review_recall'])}. Original Phase 3A predictions, metrics, locks, handoff and package hashes are preserved verbatim as historical Gate 3A records.\n\nKey hashes:\n\n"
    for name,sha in summary["prediction_and_artifact_hashes"].items():text+=f"- `{name}`: `{sha}`\n"
    text+="\n`phase3_summary.json` contains all dev/test/baseline counts, metrics, target outcomes, uncertainty, abstentions, error capture and separate/total usage. Raw case/attempt files remain available in `results/phase3/`. Scoring/source/projection/authorization hashes are verified against their committed pre-test locks.\n\n## Closure\n\nGate 3B: TEST_COMPLETE. Formal evaluation has stopped. No final report, README, dataset documentation or demo material is updated in this phase. Instructor deliverable clarification remains deferred to the subsequent reporting task.\n"
    f.write_once(ROOT/"docs/Phase3_Formal_Evaluation_Handoff.md",text.encode())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("command",choices=("preflight","score"))
    args=p.parse_args()
    if args.command=="preflight":preflight()
    else:score()


if __name__=="__main__":main()
