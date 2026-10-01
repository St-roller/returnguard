"""Exercise approval gates with fixtures; fixture reviews never approve live data."""
from copy import deepcopy

import pytest

from returnguard.blueprints import generate_blueprints
from returnguard.dataset_review import candidate_gold, audit_messages, approved_records, digest
from returnguard.schemas import CaseRecord


def example(bp):
    phrases = {
        "ordinary_return": ["尺码不合适"], "quality_or_fulfillment_issue": ["收到时就有破损"],
        "not_stated": [], "attached": ["吊牌还完整挂着"], "removed": ["吊牌已剪掉"],
        "absent": ["没有破损或污渍"], "present": ["收到后保管时蹭脏了"],
        "no": ["只在家试穿，没有穿出门"], "yes": ["已经穿出门一天"],
    }
    conflicts = {"tag_status": ["吊牌还完整挂着", "但吊牌已剪掉"],
                 "damage_or_stain": ["没有破损或污渍", "但有破损"],
                 "use_beyond_inspection": ["没有穿出门", "但已经穿出门一天"]}
    ex = {}
    for name, value in bp.intended_extraction.model_dump().items():
        spans = conflicts[name] if value == "conflicting" else (
            ["我不确定这个状态"] if value == "unknown" and bp.generation_constraints.composition_tag == "explicit_uncertainty"
            else [] if value == "unknown" else phrases[value])
        ex[name] = {"value": value, "evidence": spans}
    msg = "想申请退货。" + "，".join(span for f in ex.values() for span in f["evidence"]) + "。"
    return msg, ex


def test_all_blueprint_gold_recomputes_without_changing_schema():
    for bp in generate_blueprints():
        message, ex = example(bp)
        gold = candidate_gold(bp, message, ex)
        assert gold["decision"]["rule_id"] == bp.target.rule_id
        assert all("support_score" not in f for f in gold["extraction"].values())
        CaseRecord.model_validate({"case_id": "fixture", "split": bp.split, "schema_version": "case_v1.0",
            "policy_version": "policy_v1.0", "input": {"order_facts": bp.trusted_order_facts.model_dump(mode="json"),
            "customer_message": message}, "gold": gold, "review_metadata": {"fixture": True}})


def test_invalid_span_changed_intent_and_explicit_uncertainty_block_gold():
    bp = generate_blueprints()[0]
    message, ex = example(bp)
    bad = deepcopy(ex);bad["tag_status"]["evidence"] = ["英文概括"]
    with pytest.raises(ValueError, match="non-verbatim"):
        candidate_gold(bp, message, bad)
    bad = deepcopy(ex);bad["tag_status"]["value"] = "removed"
    with pytest.raises(ValueError, match="differ from approved blueprint"):
        candidate_gold(bp, message, bad)
    missing = next(b for b in generate_blueprints() if b.generation_constraints.composition_tag == "missing_information")
    message, ex = example(missing)
    field = next(k for k,v in ex.items() if v["value"] == "unknown")
    ex[field]["evidence"] = ["我不确定"]
    with pytest.raises(ValueError, match="differs from blueprint intent"):
        candidate_gold(missing, message + "我不确定", ex)


def record(case_id, split, text, annotation="Customer asks to return the clothing."):
    return {"case_id": case_id, "split": split, "customer_message": text,
        "english_annotation": annotation, "blueprint": {"target": {"route": "eligible"}}}


def test_audit_detects_cross_split_duplicates_leakage_and_content_locked_pairs():
    base = "尺码不合适，吊牌还在，衣服没有污损，只在家试穿，想申请退货。"
    records = [record("dev_001", "dev", base), record("test_001", "test", base),
               record("test_002", "test", base.replace("尺码", "尺寸"))]
    audit = audit_messages(records)
    assert audit["exact_duplicate_count"] == 1
    assert audit["pairs_checked"] == {"cross_split": 2, "test": 1}
    pair_ids = {p["pair_id"] for p in audit["near_duplicate_pairs"]}
    records[2]["customer_message"] += "谢谢。"
    assert not pair_ids.intersection(p["pair_id"] for p in audit_messages(records)["near_duplicate_pairs"])
    leak = audit_messages([record("dev_001", "dev", "正确结果 eligible，EL01_STATUTORY7。")])
    assert leak["model_visible_leakage"]
    natural = audit_messages([record("dev_001", "dev", "商品标签还在。")])
    assert natural["input_word_flags"] and not natural["model_visible_leakage"]


def test_no_implicit_human_approval_or_stale_snapshot():
    drafts = [{"case_id": f"dev_{i:03}"} for i in range(180)]
    with pytest.raises(ValueError, match="different draft snapshot"):
        approved_records(drafts, {"source_drafts_sha256": "old"})
    with pytest.raises(ValueError, match="All 180"):
        approved_records(drafts, {"source_drafts_sha256": digest(drafts), "reviews": []})
    reviews = {"source_drafts_sha256": digest(drafts), "reviews": [
        {"case_id": d["case_id"], "review_status": "pending"} for d in drafts]}
    with pytest.raises(ValueError, match="case approval/checklist pending"):
        approved_records(drafts, reviews)


def test_live_raw_requests_have_matching_label_free_provenance():
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "scripts/prepare_dataset_review.py"
    spec = importlib.util.spec_from_file_location("review_preparation", path)
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    drafts, provenance = module.load_drafts()
    assert len(drafts) == 180
    assert all(d["review_status"] == "pending" and d["review_method_version"] is None for d in drafts)
    assert provenance["dev"]["actual_settings"] == provenance["test"]["actual_settings"] == {"temperature": 0.7, "top_p": 0.9}


def test_approved_records_require_resolved_pairs_and_current_human_audit(monkeypatch):
    drafts, reviews = [], []
    for bp in generate_blueprints():
        message, ex = example(bp)
        case_id = bp.blueprint_id.replace("_bp_", "_")
        drafts.append({"case_id": case_id, "split": bp.split, "blueprint": bp.model_dump(mode="json"),
            "customer_message": message, "english_annotation": "Test fixture annotation.",
            "extraction": ex, "generation_provenance": {"fixture": True}, "raw_record_sha256": "fixture"})
        reviews.append({"case_id": case_id, "customer_message": message, "english_annotation": "Test fixture annotation.",
            "extraction": ex, "review_status": "approved", "checklist_confirmed": True, "checklist_items": [True]*13,
            "review_method_version": "structured_case_review_v1.1", "reviewed_at": "2026-01-01T00:00:00Z",
            "issues_found": [], "repairs_made": [], "review_notes": "Fixture-only substantive review.",
            "reviewed_content_sha256": digest({"customer_message": message, "english_annotation": "Test fixture annotation.", "extraction": ex})})
    # Test the review gate separately from similarity algorithms, covered above.
    monkeypatch.setattr("returnguard.dataset_review.audit_messages", lambda rows: {
        "exact_duplicate_count": 0, "model_visible_leakage": [], "id_label_leakage": [],
        "near_duplicate_pairs": [{"pair_id": "fixture_pair"}], "dataset_snapshot_sha256": "fixture_snapshot"})
    packet = {"source_drafts_sha256": digest(drafts), "reviews": reviews}
    with pytest.raises(ValueError, match="near-duplicate pairs need structured"):
        approved_records(drafts, packet)
    packet["pair_decisions"] = {"fixture_pair": {"decision": "accepted_distinct", "review_method_version": "structured_case_review_v1.1", "notes": "Fixture decision.", "reviewed_at": "2026-01-01T00:00:00Z"}}
    with pytest.raises(ValueError, match="needs structured attestation"):
        approved_records(drafts, packet)
    packet["audit_attestation"] = {"review_method_version": "structured_case_review_v1.1", "reviewed_at": "2026-01-01T00:00:00Z",
        "formatting_checked": True, "annotation_flags_checked": True, "input_flags_checked": True,
        "dataset_snapshot_sha256": "fixture_snapshot"}
    final, audit = approved_records(drafts, packet)
    assert len(final) == audit["review_approved"] == 180
    assert all(r["review_metadata"]["english_annotation"] == "Test fixture annotation." for r in final)
    assert all(set(r["input"]) == {"order_facts", "customer_message"} for r in final)
    assert all("reviewer_name" not in r["review_metadata"] and "reviewed_by" not in r["review_metadata"] for r in final)
    packet["reviews"][0]["review_method_version"] = None
    with pytest.raises(ValueError, match="Versioned and timestamped"):
        approved_records(drafts, packet)
    packet["reviews"][0]["review_method_version"] = "structured_case_review_v1.1"
    packet["reviews"][0]["reviewed_at"] = "2026-01-01"
    with pytest.raises(ValueError, match="timezone-aware ISO-8601"):
        approved_records(drafts, packet)
    packet["reviews"][0]["reviewed_at"] = "2026-01-01T00:00:00Z"
    packet["audit_attestation"]["dataset_snapshot_sha256"] = "stale"
    with pytest.raises(ValueError, match="needs structured attestation"):
        approved_records(drafts, packet)
    packet["audit_attestation"]["dataset_snapshot_sha256"] = "fixture_snapshot"
    packet["reviews"][0]["customer_message"] += "谢谢。"
    with pytest.raises(ValueError, match="Case review is stale"):
        approved_records(drafts, packet)
    packet["reviews"][0]["customer_message"] = drafts[0]["customer_message"]
    packet["reviews"][0]["checklist_items"][0] = False
    with pytest.raises(ValueError, match="All 13"):
        approved_records(drafts, packet)
