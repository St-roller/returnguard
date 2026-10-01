import copy
from pathlib import Path

import pytest

from returnguard import formal_eval as f
from returnguard import heldout_scoring as h


def row(case_id="test_001", *, score=.9, candidate="eligible", gold="eligible", final=None, reason=None, status="completed"):
    fields={name:{"value":v,"evidence":[],"support_score":score} for name,v in zip(
        ("return_reason","tag_status","damage_or_stain","use_beyond_inspection"),
        ("ordinary_return","attached","absent","no"))}
    return {"case_id":case_id,"split":"test","evaluation_status":status,"raw_structured_extraction":fields,
        "validated_extraction":fields if status=="completed" else None,
        "candidate_route":candidate if status=="completed" else None,"candidate_rule_id":"EL01_7DAY",
        "candidate_review_reason":None,"case_support_score":score,
        "final_route":final or candidate,"review_reason":reason,"threshold_value":.86,
        "gold":{"decision":{"route":gold,"rule_id":"EL01_7DAY"},"extraction":fields},
        "dataset_file_sha256":f.TEST_HASH,"eval_config_sha256":"config","model_id_requested":f.MODEL,
        "model_id_returned":f.MODEL,"request_attempts":1,"token_usage":{"input_tokens":10,"output_tokens":20},
        "reported_usage_cost_usd":.01,"latency_seconds":1}


def operating(n,accepted,correct):
    return {"n":n,"auto_routed_n":accepted,"correct_auto_n":correct,
            "selective_accuracy_constraint_met":bool(accepted) and correct*10>=accepted*9}


def test_test_metrics_use_locked_point_and_correct_split_name():
    rows=[row(),row("test_002",score=.8,final="manual_review",reason="low_confidence"),
          row("test_003",candidate="ineligible",gold="manual_review")]
    m=h.heldout_metrics(rows)
    assert m["split"]=="test" and m["locked_threshold"]==.86
    assert "dev_coverage_target_60_percent_met" not in m
    assert m["coverage"]["numerator"]==2 and m["selective_accuracy"]["numerator"]==1
    assert m["gold_manual_auto_routed_n"]==1


def test_baseline_below_safety_has_no_equivalent_safe_gap_or_threshold():
    c=h.compare_baseline(operating(90,60,58),operating(90,30,26))
    assert c["coverage_difference_percentage_points"] is None
    assert c["descriptive_raw_coverage_difference_percentage_points"]==pytest.approx(100/3)
    assert c["coverage_gap_target_10_pp_met"] is None and not c["safe_comparison_valid"]
    assert "post-hoc threshold" in c["statement"]


def test_baseline_safety_and_ten_pp_boundary_are_exact():
    c=h.compare_baseline(operating(90,54,54),operating(90,45,45))
    assert c["coverage_difference_percentage_points"]==10
    assert c["safe_coverage_gain_target_met"]
    assert not h.compare_baseline(operating(90,53,53),operating(90,45,45))["coverage_gap_target_10_pp_met"]


def test_returnguard_safety_failure_cannot_be_claimed_safe_superiority():
    c=h.compare_baseline(operating(90,60,53),operating(90,30,30))
    assert c["coverage_gap_target_10_pp_met"]
    assert not c["safe_coverage_gain_target_met"] and not c["safe_comparison_valid"]


def raw_fixture(tmp_path, r):
    raw=copy.deepcopy(r);raw.pop("gold",None)
    path=tmp_path/"test_predictions_raw.jsonl"
    f.write_once(path,f.jsonl([raw]))
    f.write_once(tmp_path/"test_prediction_freeze.json",f.encode({"case_n":1,"predictions_sha256":f.file_hash(path),"eval_config_sha256":"config"}))
    return {"eval_config_sha256":"config","test_dataset_sha256":f.TEST_HASH,"locked_threshold_value":.86}


def test_gold_scoring_requires_finalized_frozen_raw_predictions(tmp_path):
    with pytest.raises(f.HardStop,match="persisted and frozen"):
        h.verified_raw(tmp_path,{})
    a=raw_fixture(tmp_path,row())
    assert len(h.verified_raw(tmp_path,a,expected_n=1))==1
    (tmp_path/"test_predictions_raw.jsonl").write_text('{}\n')
    with pytest.raises(f.HardStop,match="count/hash"):
        h.verified_raw(tmp_path,a,expected_n=1)


def test_scoring_refuses_raw_prediction_at_wrong_threshold(tmp_path):
    a=raw_fixture(tmp_path,row(score=.8))
    with pytest.raises(f.HardStop,match="locked threshold"):
        h.verified_raw(tmp_path,a,expected_n=1)


def test_scoring_never_writes_or_changes_threshold_lock(tmp_path):
    lock=tmp_path/"threshold_lock_v1.json"
    f.write_once(lock,f.encode({"value":.86}))
    before=lock.read_bytes()
    m=h.heldout_metrics([row()])
    h.compare_baseline(m,m)
    assert lock.read_bytes()==before


def test_error_analysis_covers_all_critical_cases_and_fixed_samples():
    rows=[row("test_001",gold="manual_review"),
          row("test_002",score=.8,final="manual_review",reason="low_confidence"),
          row("test_003",gold="ineligible",status="validation_failure",final="manual_review",reason="validation_failure"),
          row("test_004",status="execution_failure",final="manual_review",reason="execution_failure")]
    inputs=[{"case_id":r["case_id"],"input":{"customer_message":"中文固定测试","order_facts":{}}} for r in rows]
    e=h.error_analysis(rows,inputs,[])
    assert e["auto_routing_error_ids"]==["test_001"] and e["gold_manual_auto_routed_ids"]==["test_001"]
    assert e["validation_failure_ids"]==["test_003"] and e["execution_failure_ids"]==["test_004"]
    assert e["low_confidence_sample_ids"]==["test_002"] and e["model_judge_calls"]==0
    assert "over-abstention / low-confidence false alarm" in e["inspected_cases"][1]["categories"]


def test_field_error_labels_compare_values_not_gold_evidence_spans():
    a=row();a["gold"]=copy.deepcopy(a["gold"])
    a["gold"]["extraction"]["tag_status"]["evidence"]=["another valid span"]
    inputs=[{"case_id":a["case_id"],"input":{"customer_message":"中文测试","order_facts":{}}}]
    assert h.error_analysis([a],inputs,[])["field_value_error_ids"]==[]
    a["gold"]["extraction"]["tag_status"]["value"]="unknown"
    assert h.error_analysis([a],inputs,[])["field_value_error_ids"]==["test_001"]


def test_no_errors_produces_na_error_capture_and_empty_error_lists():
    r=row();m=h.heldout_metrics([r])
    assert m["error_capture"]["display"]=="N/A"
    e=h.error_analysis([r],[{"case_id":r["case_id"],"input":{}}],[])
    assert e["inspected_cases"]==[] and e["auto_routing_error_ids"]==[]


def test_usage_is_direct_reported_sum_with_partial_cost_marked():
    a=row();b=row("test_002");b["reported_usage_cost_usd"]=None;b["request_attempts"]=3
    u=h.aggregate_usage([a,b])
    assert u["model_request_attempts"]==4 and u["infrastructure_retry_n"]==2
    assert u["input_tokens"]==20 and u["reported_api_cost_usd"]==.01
    assert not u["cost_complete"] and u["cost_available_n"]==1
