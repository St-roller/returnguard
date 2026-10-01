"""Freeze only structured-review-approved cases with passed current audits.

First run prepares the final files. Commit those files in a dedicated commit.
Then run --freeze-commit SHA to verify committed bytes and record the manifest
in a following metadata commit, avoiding a self-referential commit/hash.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from prepare_dataset_review import load_drafts, DATA
from returnguard.dataset_review import approved_records
from returnguard.surface_generation import sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviews", required=True, type=Path)
    parser.add_argument("--freeze-commit", help="Actual dedicated data commit, verified locally")
    parser.add_argument("--approval", required=True, type=Path, help="Explicit project-level approval record for this reviewed snapshot")
    args = parser.parse_args()
    if (DATA / "freeze_manifest.json").exists():
        raise SystemExit("Dataset already frozen: version any correction explicitly")
    drafts, provenance = load_drafts()
    reviews = json.loads(args.reviews.read_text())
    finals, audit = approved_records(drafts, reviews)
    approval = json.loads(args.approval.read_text())
    if (approval.get("decision") != "approved_for_freeze" or not approval.get("approved_at")
            or not approval.get("approval_source", "").strip()
            or approval.get("dataset_snapshot_sha256") != audit["dataset_snapshot_sha256"]):
        raise ValueError("Explicit project-level approval of the current reviewed snapshot required")
    outputs = {}
    for split in ("dev", "test"):
        rows = [r for r in finals if r["split"] == split]
        if len(rows) != 90:
            raise ValueError("Split size changed")
        outputs[f"{split}.jsonl"] = ("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n").encode()
        outputs[f"provenance_{split}.json"] = (json.dumps({**provenance[split], "structured_review_status": "approved", "review_approved": 90}, ensure_ascii=False, indent=2) + "\n").encode()
    outputs["audit_report.json"] = (json.dumps(audit, ensure_ascii=False, indent=2) + "\n").encode()
    outputs["structured_reviews.json"] = (json.dumps(reviews, ensure_ascii=False, indent=2) + "\n").encode()
    if not args.freeze_commit:
        for name, content in outputs.items():
            path = DATA / name
            if path.exists() and path.read_bytes() != content:
                raise ValueError(f"{name} differs from prior prepared bytes; inspect before replacement")
            path.write_bytes(content)
        print("All 180 case approvals validated. Commit final data/audit/provenance/reviews, then record --freeze-commit SHA.")
        return
    commit = subprocess.check_output(["git", "rev-parse", "--verify", args.freeze_commit + "^{commit}"], cwd=ROOT, text=True).strip()
    names = list(outputs) + ["blueprints_dev.jsonl", "blueprints_test.jsonl", "matrix_report.json", "overlap_report.json"]
    for name in names:
        path = DATA / name
        actual = path.read_bytes()
        expected = outputs.get(name, actual)
        committed = subprocess.check_output(["git", "show", f"{commit}:{path.relative_to(ROOT)}"], cwd=ROOT)
        if actual != expected or committed != actual:
            raise ValueError(f"Freeze commit/current reviewed bytes differ: {name}")
    manifest = {
        "dataset_version": "ReturnGuard-Synth-v1", "dev_n": 90, "test_n": 90,
        "schema_version": "case_v1.0", "policy_version": "policy_v1.0",
        "audit_status": "passed", "frozen_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit, "source_blueprint_commit": provenance["dev"]["source_blueprint_commit"],
        "sha256": {name: sha256(DATA / name) for name in names},
        "dev_sha256": sha256(DATA / "dev.jsonl"), "test_sha256": sha256(DATA / "test.jsonl"),
        "project_level_approval": approval, "evaluated_model_formal_calls": 0, "acceptance_threshold_selected": False,
    }
    (DATA / "freeze_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print("Manifest recorded against verified data commit; commit manifest as metadata.")


if __name__ == "__main__":
    main()
