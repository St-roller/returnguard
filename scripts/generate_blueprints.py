"""Create or verify the frozen-design Phase 2A blueprints without an API call."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from returnguard.blueprints import Blueprint, generate_blueprints, validate_blueprints

OUT = ROOT / "data" / "returnguard_synth_v1"


def _put_or_check(path: Path, content: bytes, check: bool) -> None:
    if path.exists():
        if path.read_bytes() != content:
            raise SystemExit(f"{path}: content differs; version the design before replacement")
    elif check:
        raise SystemExit(f"{path}: missing")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate committed bytes without writing")
    args = parser.parse_args()
    generated = generate_blueprints()
    report = validate_blueprints(generated)
    hashes = {}
    for split in ("dev", "test"):
        path = OUT / f"blueprints_{split}.jsonl"
        content = ("\n".join(b.model_dump_json() for b in generated if b.split == split) + "\n").encode("utf-8")
        _put_or_check(path, content, args.check)
        # Validate the serialized data, not just the in-memory objects.
        loaded = [Blueprint.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines()]
        if loaded != [b for b in generated if b.split == split]:
            raise SystemExit(f"{path}: round-trip mismatch")
        hashes[split] = hashlib.sha256(path.read_bytes()).hexdigest()
    report["blueprint_file_sha256"] = hashes
    report["phase"] = "2A"
    report["api_calls"] = 0
    report_path = OUT / "matrix_report.json"
    report_bytes = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _put_or_check(report_path, report_bytes, args.check)
    sample_ids = ("dev_bp_001", "test_bp_029", "dev_bp_037", "dev_bp_061", "test_bp_090")
    samples = {b.blueprint_id: b for b in generated if b.blueprint_id in sample_ids}
    if len(samples) != len(sample_ids):
        raise SystemExit("representative blueprint ID missing")
    sample_content = (json.dumps({
        "purpose": "Phase 2A design review only; no Chinese messages or API calls",
        "blueprints": [samples[identifier].model_dump(mode="json") for identifier in sample_ids],
    }, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _put_or_check(OUT / "review_samples.json", sample_content, args.check)
    print(json.dumps({
        "phase": "2A", "total": report["total_n"],
        "splits": {name: detail["n"] for name, detail in report["splits"].items()},
        "policy_recomputed_matches": report["validation"]["policy_recomputed_matches"],
        "valid_trusted_dates": report["validation"]["valid_trusted_dates"],
        "api_calls": report["api_calls"], "mode": "check" if args.check else "generate",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
