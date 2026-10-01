"""Build an offline, structured case review packet; never freeze."""
import argparse
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from returnguard.blueprints import Blueprint
from returnguard.dataset_review import make_drafts, audit_messages, digest
from returnguard.surface_generation import sha256, MODEL_ID, PROMPT_VERSION, request_body

DATA = ROOT / "data/returnguard_synth_v1"
OUT = DATA / "construction"


def load_drafts():
    blueprints, raw, provenance = [], [], {}
    matrix_hash = sha256(DATA / "matrix_report.json")
    for split in ("dev", "test"):
        provenance[split] = p = json.loads((OUT / f"provenance_{split}.json").read_text())
        bp_path = DATA / f"blueprints_{split}.jsonl"
        raw_path = OUT / f"raw_{split}.jsonl"
        raw_bytes = raw_path.read_bytes() if raw_path.exists() else gzip.decompress(raw_path.with_suffix(".jsonl.gz").read_bytes())
        import hashlib
        if (p["source_matrix_sha256"] != matrix_hash or p["source_blueprint_sha256"] != sha256(bp_path)
                or p["raw_sha256"] != hashlib.sha256(raw_bytes).hexdigest() or p["n"] != 90
                or p["model_id"] != MODEL_ID or p["prompt_version"] != PROMPT_VERSION):
            raise ValueError("Raw provenance/source hash mismatch")
        split_blueprints = [Blueprint.model_validate_json(x) for x in bp_path.read_text().splitlines()]
        blueprint_by_id = {b.blueprint_id: b for b in split_blueprints}
        blueprints.extend(split_blueprints)
        rows = [json.loads(x) for x in raw_bytes.decode().splitlines()]
        for row in rows:
            rp = row["generation_provenance"]
            if rp["split"] != split or rp["generation_batch_id"] != p["batch_id"] or rp["model_id"] != MODEL_ID:
                raise ValueError("Per-case provenance mismatch")
            if row["request"] != request_body(blueprint_by_id[row["blueprint_id"]], p["actual_settings"]):
                raise ValueError("Generator request differs from label-free approved request contract")
            if {k: rp[k] for k in ("temperature", "top_p")} != {k: p["actual_settings"].get(k) for k in ("temperature", "top_p")}:
                raise ValueError("Per-case actual settings mismatch")
        raw.extend(rows)
    if provenance["dev"]["actual_settings"] != provenance["test"]["actual_settings"]:
        raise ValueError("Dev/test settings differ")
    if provenance["dev"]["batch_id"] == provenance["test"]["batch_id"]:
        raise ValueError("Dev/test runs must be separate")
    return make_drafts(blueprints, raw), provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviews", type=Path, help="Re-audit reviewed edits and preserve actual decisions")
    args = parser.parse_args()
    drafts, provenance = load_drafts()
    initial = {"source_drafts_sha256": digest(drafts), "reviews": [], "pair_decisions": {}, "audit_attestation": {}}
    if args.reviews:
        initial = json.loads(args.reviews.read_text())
        if initial["source_drafts_sha256"] != digest(drafts):
            raise ValueError("Review export is for a different draft snapshot")
    changes = {r["case_id"]: r for r in initial["reviews"]}
    audit_input = [{**d, **{k: changes[d["case_id"]][k] for k in ("customer_message", "english_annotation")}}
                   if d["case_id"] in changes else d for d in drafts]
    audit = audit_messages(audit_input)
    for name, obj in (("review_drafts.json", drafts), ("current_review_audit.json", audit)):
        (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
    packet = {"drafts": drafts, "audit": audit, "initial": initial, "provenance": provenance}
    embedded = json.dumps(packet, ensure_ascii=False).replace("<", "\\u003c")
    html = (ROOT / "templates/dataset_review.html").read_text().replace("__PACKET_JSON__", embedded)
    (OUT / "structured_review.html").write_text(html)
    print(json.dumps({"cases": len(drafts), "preflight_issue_cases": sum(bool(d["preflight_issues"]) for d in drafts),
        "exact_duplicate_count": audit["exact_duplicate_count"], "near_pairs": len(audit["near_duplicate_pairs"]),
        "review_approved": sum(r.get("review_status") == "approved" for r in initial["reviews"]),
        "review_page": str(OUT / "structured_review.html"), "freeze_status": "blocked_pending_dataset_level_approval"}))


if __name__ == "__main__":
    main()
