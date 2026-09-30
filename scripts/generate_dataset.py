"""Generate one split in one isolated run; never read the other split's messages."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from returnguard.blueprints import Blueprint
from returnguard.surface_generation import DeepSeekGenerator, SETTINGS, MODEL_ID, PROMPT_VERSION, sha256

SOURCE_COMMIT = "c2af09ffb1346c91a8d6cb4783d827c24c6704bd"
DATA = ROOT / "data" / "returnguard_synth_v1"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--split", choices=("dev", "test"), required=True)
    p.add_argument("--settings-file", type=Path)
    args = p.parse_args()
    if args.split == "test" and not args.settings_file:
        raise SystemExit("Test run requires the dev settings/provenance file only, never dev text.")
    matrix = json.loads((DATA / "matrix_report.json").read_text())
    path = DATA / f"blueprints_{args.split}.jsonl"
    if sha256(path) != matrix["blueprint_file_sha256"][args.split]:
        raise SystemExit("Current blueprint hash does not match repository matrix")
    rows = [Blueprint.model_validate_json(line) for line in path.read_text().splitlines()]
    if len(rows) != 90 or any(b.split != args.split for b in rows):
        raise SystemExit("Invalid split")
    settings = dict(SETTINGS)
    fallbacks = []
    if args.settings_file:
        locked = json.loads(args.settings_file.read_text())
        if locked["model_id"] != MODEL_ID or locked["prompt_version"] != PROMPT_VERSION:
            raise SystemExit("Dev settings model/prompt differs")
        settings = locked["actual_settings"]
        fallbacks = locked["parameter_fallbacks"]
    batch = f"{args.split}_generation_v1_{os.environ.get('GITHUB_RUN_ID', 'local')}_{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
    out = DATA / "construction"
    out.mkdir(exist_ok=True)
    raw_path = out / f"raw_{args.split}.jsonl"
    if raw_path.exists():
        raise SystemExit("Raw run exists; do not overwrite or silently regenerate")
    generator = DeepSeekGenerator()
    records = []
    first = generator.generate(rows[0], settings, batch)
    # Only explicit endpoint parameter rejection permits the specified default
    # fallback, before settings are locked for all subsequent cases/both splits.
    while args.split == "dev" and first["generation_status"] == "api_failure":
        errors = first["errors"]
        text = " ".join(e["message"].lower() for e in errors)
        parameter = next((k for k in ("temperature", "top_p") if k in settings and k in text
                          and ("unsupported" in text or "not support" in text)), None)
        if parameter is None:
            break
        fallbacks.append({"parameter": parameter, "requested_value": settings.pop(parameter),
                          "fallback": "provider_default", "rejection": errors})
        first = generator.generate(rows[0], settings, batch)
    records.append(first)
    with raw_path.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps(first, ensure_ascii=False) + "\n")
        stream.flush()
        if first["generation_status"] != "api_failure":
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {pool.submit(generator.generate, b, settings, batch): b for b in rows[1:]}
                for future in as_completed(futures):
                    record = future.result()
                    records.append(record)
                    stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                    stream.flush()
                    print(record["blueprint_id"], record["generation_status"], flush=True)
    records.sort(key=lambda r: r["blueprint_id"])
    raw_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    summary = {
        "gateway_provider": "OpenRouter", "model_id": MODEL_ID, "prompt_version": PROMPT_VERSION,
        "actual_settings": settings, "parameter_fallbacks": fallbacks, "seed": None,
        "batch_id": batch, "split": args.split, "source_blueprint_commit": SOURCE_COMMIT,
        "source_matrix_sha256": sha256(DATA / "matrix_report.json"),
        "source_blueprint_sha256": sha256(path), "execution_commit": os.environ.get("GITHUB_SHA"),
        "started_from_separate_run": True, "completed_at": datetime.now(timezone.utc).isoformat(),
        "n": len(records), "status_counts": {status: sum(r["generation_status"] == status for r in records)
                      for status in ("generated", "needs_revision", "api_failure")},
        "upstream_providers": sorted({r["generation_provenance"]["upstream_provider"] for r in records
                                     if r["generation_provenance"]["upstream_provider"]}),
        "raw_sha256": sha256(raw_path), "human_review_status": "pending",
    }
    (out / f"provenance_{args.split}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    if len(records) != 90 or any(r["generation_status"] == "api_failure" for r in records):
        raise SystemExit("Split has pending/API-failed cases; preserve blueprints and raw attempts.")


if __name__ == "__main__":
    main()
