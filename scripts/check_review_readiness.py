"""Validate structured reviews and write approval-stage artifacts; never freeze.

This consumes explicit case-level review decisions. It does not review or approve
cases automatically and makes no model calls.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from prepare_dataset_review import load_drafts, OUT
from returnguard.dataset_review import approved_records, digest


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviews", type=Path, default=OUT / "structured_reviews.json")
    args = parser.parse_args()
    drafts, _ = load_drafts()
    packet = json.loads(args.reviews.read_text())
    finals, audit = approved_records(drafts, packet)
    reviews = {r["case_id"]: r for r in packet["reviews"]}
    lengths, categories = [], Counter()
    for d in drafts:
        r = reviews[d["case_id"]]
        constraint = d["blueprint"]["generation_constraints"]["message_length"]
        lo, hi = {"short": (15, 35), "medium": (36, 70), "long": (71, 130)}[constraint]
        n = len(r["customer_message"])
        if not lo <= n <= hi:
            raise ValueError(f"{d['case_id']}: {n} characters outside {constraint} intent")
        lengths.append({"case_id": d["case_id"], "intended_length": constraint, "characters": n})
        categories.update(set(r["issue_categories"]))
    preserved = json.loads((OUT / "preserved_source_hashes.json").read_text())
    for name, original in preserved.items():
        current = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        if current != original:
            raise ValueError(f"Preserved source changed: {name}")
    repaired = [d for d, final in zip(drafts, finals) if final["review_metadata"]["edited_during_review"]]
    evidence_repaired = [d["case_id"] for d in drafts if reviews[d["case_id"]]["extraction"] != d["extraction"]]
    annotation_repaired = [d["case_id"] for d in drafts if reviews[d["case_id"]]["english_annotation"] != d["english_annotation"]]
    semantic_categories = {"missing_damage_evidence", "missing_tag_evidence", "missing_use_evidence",
        "missing_reason_evidence", "invalid_evidence", "invalid_conflict", "unstated_reason_violation",
        "reason_family_mismatch", "issue_family_mismatch", "missing_information_mismatch", "truncated_response"}
    semantic_repaired = [r["case_id"] for r in reviews.values() if semantic_categories.intersection(r["issue_categories"])]
    sentence_cases = {}
    for r in reviews.values():
        for sentence in set(s.strip() for s in re.split(r"[。！？!?；;]", r["customer_message"])):
            if len(sentence) >= 8:
                sentence_cases.setdefault(sentence, []).append(r["case_id"])
    repeated = [{"sentence": s, "case_ids": ids} for s, ids in sentence_cases.items() if len(ids) >= 3]
    audit.update(length_intent_validated=180, length_checks=lengths,
        repeated_sentences_three_or_more=repeated,
        reviewed_records_sha256=digest(finals), dataset_status="reviewed_candidate_not_frozen",
        readiness_status="READY_FOR_DATASET_LEVEL_APPROVAL", project_level_approval="pending")
    summary = {
        "status": "READY_FOR_DATASET_LEVEL_APPROVAL", "blockers": [], "dataset_frozen": False,
        "project_level_approval": "pending", "total_reviewed": 180, "total_approved": 180,
        "total_repaired": len(repaired), "clean_no_change": 180-len(repaired),
        "truncated_repairs": categories["truncated_response"], "evidence_repairs": len(evidence_repaired),
        "semantic_realization_repairs": len(semantic_repaired), "language_realization_repairs": categories["language_realization"],
        "annotation_repairs": len(annotation_repaired), "original_annotation_mismatches": categories["annotation_mismatch"],
        "near_duplicate_rewrite_cases": categories["near_duplicate"],
        "near_duplicate_accepted_distinct_pairs": len(packet["pair_decisions"]), "rejected": 0,
        "issue_distribution_case_counts": dict(sorted(categories.items())),
        "original_preflight_issue_cases": sum(bool(d["preflight_issues"]) for d in drafts),
        "original_unflagged_cases_reviewed": sum(not d["preflight_issues"] for d in drafts),
        "evidence_repair_case_ids": evidence_repaired, "semantic_repair_case_ids": semantic_repaired,
        "annotation_repair_case_ids": annotation_repaired,
        "source_drafts_sha256": packet["source_drafts_sha256"],
        "dataset_snapshot_sha256": audit["dataset_snapshot_sha256"],
        "reviewed_records_sha256": digest(finals), "preserved_sources_checked": len(preserved),
        "formal_evaluated_model_calls": 0, "acceptance_threshold_selected": False,
        "count_note": "Repair categories overlap; annotation changes include translations updated after Chinese repair.",
    }
    hashes = {}
    for split in ("dev", "test"):
        rows = [r for r in finals if r["split"] == split]
        assert len(rows) == 90
        name = f"reviewed_candidate_{split}.jsonl"
        content = ("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n").encode()
        (OUT / name).write_bytes(content)
        hashes[name] = hashlib.sha256(content).hexdigest()
    summary["candidate_file_sha256"] = hashes
    write_json(OUT / "final_review_audit.json", audit)
    write_json(OUT / "review_summary.json", summary)
    print(json.dumps({k: summary[k] for k in ("status", "total_reviewed", "total_approved", "total_repaired", "clean_no_change", "truncated_repairs", "evidence_repairs", "semantic_realization_repairs", "annotation_repairs", "near_duplicate_rewrite_cases", "near_duplicate_accepted_distinct_pairs")}, indent=2))


if __name__ == "__main__":
    main()
