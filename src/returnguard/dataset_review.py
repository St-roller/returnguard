"""Human-review gates, deterministic gold construction, and dataset audits."""

from collections import Counter, defaultdict
from difflib import SequenceMatcher
import hashlib
import json
import re
import unicodedata

from .blueprints import Blueprint, validate_blueprints
from .policy import Policy
from .schemas import CaseRecord, Extraction
from .surface_generation import MODEL_ID, LABEL_PATTERN
from .validation import validate_extraction, validate_input, derive_facts

NEAR_RATIO = 0.80
NEAR_JACCARD = 0.55
INPUT_LEAKAGE = re.compile(LABEL_PATTERN.pattern + r"|\b(?:gold|label)\b|正确答案|标签", re.I)


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text.strip())
    return re.sub(r"\s*([,.;:!?，。；：！？、])\s*", r"\1", text)


def candidate_gold(bp: Blueprint, message: str, extraction: dict) -> dict:
    # Scores are schema placeholders for deterministic derive_facts only;
    # they are neither gold values nor model confidence measurements.
    ex = validate_extraction({name: {**field, "support_score": 1.0}
                             for name, field in extraction.items()}, message)
    if {name: getattr(ex, name).value for name in Extraction.model_fields} != bp.intended_extraction.model_dump():
        raise ValueError("Realized facts differ from approved blueprint; revise message/evidence before approval")
    for name, field in extraction.items():
        if field["value"] == "not_stated" and field["evidence"]:
            raise ValueError("not_stated requires absent reason evidence []")
        if field["value"] == "unknown":
            expected_explicit = bp.generation_constraints.composition_tag == "explicit_uncertainty"
            if bool(field["evidence"]) != expected_explicit:
                raise ValueError(f"{name}: missing/explicit uncertainty evidence differs from blueprint intent")
    case = validate_input({"order_facts": bp.trusted_order_facts.model_dump(mode="json"),
                           "customer_message": message})
    derived = derive_facts(case, ex)
    decision = Policy().decide(case, ex, derived)
    if (decision.candidate_route, decision.candidate_rule_id) != (bp.target.route, bp.target.rule_id):
        raise ValueError("Recomputed policy decision differs from approved blueprint")
    return {"extraction": {name: {"value": getattr(ex, name).value, "evidence": getattr(ex, name).evidence}
                           for name in Extraction.model_fields},
            "derived": derived.model_dump(), "decision": {
                "route": decision.candidate_route, "rule_id": decision.candidate_rule_id,
                "review_reason": decision.candidate_review_reason}}


def make_drafts(blueprints: list[Blueprint], raw: list[dict]) -> list[dict]:
    validate_blueprints(blueprints)
    by_id = {r["blueprint_id"]: r for r in raw}
    if len(by_id) != len(raw) or set(by_id) != {b.blueprint_id for b in blueprints}:
        raise ValueError("Missing or duplicate raw records; do not alter dataset size")
    drafts = []
    for bp in blueprints:
        record = by_id[bp.blueprint_id]
        if record["generation_provenance"]["model_id"] != MODEL_ID:
            raise ValueError("Unlocked generator model")
        surface = record.get("surface") or {}
        ex = {name: {"value": value, "evidence": surface.get("proposed_evidence", {}).get(name, [])}
              for name, value in bp.intended_extraction.model_dump().items()}
        issues = []
        try:
            proposed = candidate_gold(bp, surface.get("customer_message", ""), ex)
        except ValueError as exc:
            proposed = None
            issues.append(str(exc))
        if record["generation_status"] != "generated":
            issues.append("Generator output requires revision: " + record["generation_status"])
        drafts.append({
            "case_id": bp.blueprint_id.replace("_bp_", "_"), "split": bp.split,
            "blueprint": bp.model_dump(mode="json"), "customer_message": surface.get("customer_message", ""),
            "english_annotation": surface.get("english_annotation", ""), "extraction": ex,
            "proposed_gold": proposed, "preflight_issues": issues,
            "review_status": "pending", "reviewer_name": None, "reviewed_at": None,
            "review_round": 1, "checklist_confirmed": False, "review_notes": "",
            "generation_provenance": record["generation_provenance"],
            "raw_record_sha256": digest(record), "original_message_sha256": digest(surface.get("customer_message", "")),
            "unparsed_generator_content": (record.get("raw_response") or {}).get("choices", [{}])[0].get("message", {}).get("content") if not surface else None,
            "generation_artifact_word_flags": sorted(set(INPUT_LEAKAGE.findall(json.dumps(record.get("raw_response"), ensure_ascii=False)))),
            "generation_request_label_hits": sorted(set(INPUT_LEAKAGE.findall(json.dumps(record.get("request"), ensure_ascii=False)))),
        })
    return drafts


def audit_messages(records: list[dict]) -> dict:
    """Deterministic findings; near duplicates are flags for human review."""
    normalized = [normalize(r["customer_message"]) for r in records]
    groups = defaultdict(list)
    for i, text in enumerate(normalized):
        if text:
            groups[text].append(records[i]["case_id"])
    exact = [ids for ids in groups.values() if len(ids) > 1]
    near = []
    scopes = Counter()
    for i, a in enumerate(records):
        for j in range(i + 1, len(records)):
            b = records[j]
            scope = "cross_split" if a["split"] != b["split"] else a["split"]
            left, right = normalized[i], normalized[j]
            if not left or not right:
                continue
            scopes[scope] += 1
            grams_a = {left[k:k+3] for k in range(max(1, len(left)-2))}
            grams_b = {right[k:k+3] for k in range(max(1, len(right)-2))}
            union = grams_a | grams_b
            jac = len(grams_a & grams_b) / len(union) if union else 1.0
            ratio = SequenceMatcher(None, left, right, autojunk=False).ratio()
            if left != right and (ratio >= NEAR_RATIO or jac >= NEAR_JACCARD):
                key = digest([a["case_id"], digest(a["customer_message"]), b["case_id"], digest(b["customer_message"])])
                near.append({"pair_id": key, "case_a": a["case_id"], "case_b": b["case_id"],
                             "scope": scope, "sequence_ratio": round(ratio, 5), "char3_jaccard": round(jac, 5)})
    visible_leaks, annotation_flags, input_flags = [], [], []
    formatting = defaultdict(list)
    prefixes = defaultdict(list)
    for r in records:
        hits = sorted(set(LABEL_PATTERN.findall(r["customer_message"])))
        if hits:
            visible_leaks.append({"case_id": r["case_id"], "hits": hits})
        general = sorted(set(INPUT_LEAKAGE.findall(r["customer_message"])))
        if general:
            input_flags.append({"case_id": r["case_id"], "hits": general})
        hits = sorted(set(INPUT_LEAKAGE.findall(r.get("english_annotation", ""))))
        if hits:
            annotation_flags.append({"case_id": r["case_id"], "hits": hits, "model_visible": False})
        route = r["blueprint"]["target"]["route"]
        text = r["customer_message"]
        formatting[route].append({"case_id": r["case_id"], "characters": len(text),
            "sentences": len([s for s in re.split(r"[。！？!?]+", text) if s.strip()]),
            "punctuation": len(re.findall(r"[，。！？、；：,.!?;:]", text)),
            "emoji": len(re.findall(r"[\U0001F300-\U0001FAFF]", text))})
        prefixes[normalize(text)[:6]].append(r["case_id"])
    return {
        "audit_version": "dataset_audit_v1", "dataset_snapshot_sha256": digest([
            {"case_id": r["case_id"], "customer_message": r["customer_message"], "english_annotation": r["english_annotation"]}
            for r in records]),
        "n": len(records), "pairs_checked": dict(scopes), "exact_duplicate_groups": exact,
        "nonempty_message_count": sum(bool(t) for t in normalized),
        "empty_message_cases": [records[i]["case_id"] for i,t in enumerate(normalized) if not t],
        "exact_duplicate_count": sum(len(ids)-1 for ids in exact), "near_duplicate_pairs": near,
        "near_duplicate_thresholds": {"sequence_ratio_gte": NEAR_RATIO, "char3_jaccard_gte": NEAR_JACCARD, "rule": "OR"},
        "model_visible_leakage": visible_leaks, "annotation_only_flags": annotation_flags,
        "input_word_flags": input_flags,
        "generator_artifact_word_flags": [{"case_id": r["case_id"], "hits": r["generation_artifact_word_flags"], "model_visible": False}
                                           for r in records if r.get("generation_artifact_word_flags")],
        "generation_request_leakage": [{"case_id": r["case_id"], "hits": r["generation_request_label_hits"]}
                                       for r in records if r.get("generation_request_label_hits")],
        "generation_requests_scanned": sum("generation_request_label_hits" in r for r in records),
        "id_label_leakage": [r["case_id"] for r in records if INPUT_LEAKAGE.search(r["case_id"])],
        "formatting_by_route": dict(formatting),
        "repeated_six_character_prefixes": [{"prefix": prefix, "case_ids": ids} for prefix,ids in prefixes.items() if len(ids)>=5],
        "audit_status": "pending_human_review",
    }


def approved_records(drafts: list[dict], reviews: dict) -> tuple[list[dict], dict]:
    if reviews.get("source_drafts_sha256") != digest(drafts):
        raise ValueError("Review export is for a different draft snapshot")
    changes = reviews.get("reviews", [])
    by_id = {r["case_id"]: r for r in changes}
    if len(changes) != 180 or len(by_id) != 180 or set(by_id) != {d["case_id"] for d in drafts}:
        raise ValueError("All 180 cases require individual human review")
    finals, audit_input = [], []
    for draft in drafts:
        human = by_id[draft["case_id"]]
        if human.get("review_status") != "approved" or not human.get("checklist_confirmed"):
            raise ValueError(f"{draft['case_id']}: human approval/checklist pending")
        if len(human.get("checklist_items", [])) != 13 or not all(x is True for x in human["checklist_items"]):
            raise ValueError("All 13 human-review checks require individual confirmation")
        if not human.get("reviewer_name", "").strip() or not human.get("reviewed_at"):
            raise ValueError("Named and timestamped human review required")
        bp = Blueprint.model_validate(draft["blueprint"])
        if not human.get("english_annotation", "").strip():
            raise ValueError("English review annotation missing")
        gold = candidate_gold(bp, human["customer_message"], human["extraction"])
        metadata = {
            "english_annotation": human["english_annotation"], "review_status": "approved",
            "reviewed_by": "human", "reviewer_name": human["reviewer_name"],
            "reviewed_at": human["reviewed_at"], "review_round": human.get("review_round", 1),
            "review_notes": human.get("review_notes"), "checklist_confirmed": True,
            "dataset_version": "ReturnGuard-Synth-v1", "design_tags": bp.generation_constraints.model_dump(),
            "generation_provenance": draft["generation_provenance"],
            "source_blueprint_id": bp.blueprint_id, "source_raw_record_sha256": draft["raw_record_sha256"],
            "edited_during_review": human["customer_message"] != draft["customer_message"] or human["extraction"] != draft["extraction"],
        }
        final = CaseRecord.model_validate({"case_id": draft["case_id"], "split": draft["split"],
            "schema_version": "case_v1.0", "policy_version": "policy_v1.0",
            "input": {"order_facts": bp.trusted_order_facts.model_dump(mode="json"), "customer_message": human["customer_message"]},
            "gold": gold, "review_metadata": metadata})
        finals.append(final.model_dump(mode="json"))
        audit_input.append({**draft, "customer_message": human["customer_message"], "english_annotation": human["english_annotation"]})
    audit = audit_messages(audit_input)
    if audit["exact_duplicate_count"] or audit["model_visible_leakage"] or audit["id_label_leakage"] or audit.get("generation_request_leakage"):
        raise ValueError("Exact duplicates or model-visible label leakage block freeze")
    resolutions = reviews.get("pair_decisions", {})
    unresolved = [p["pair_id"] for p in audit["near_duplicate_pairs"] if not (
        resolutions.get(p["pair_id"], {}).get("decision") == "accepted_distinct" and
        resolutions[p["pair_id"]].get("reviewer_name") and resolutions[p["pair_id"]].get("notes", "").strip())]
    if unresolved:
        raise ValueError(f"{len(unresolved)} near-duplicate pairs need human resolution")
    attest = reviews.get("audit_attestation", {})
    if not (attest.get("reviewer_name") and attest.get("reviewed_at") and
            attest.get("formatting_checked") and attest.get("annotation_flags_checked") and attest.get("input_flags_checked") and
            attest.get("dataset_snapshot_sha256") == audit["dataset_snapshot_sha256"]):
        raise ValueError("Current formatting/annotation audit needs human attestation")
    audit.update(audit_status="passed", human_audit_attestation=attest, near_duplicate_resolutions=resolutions,
                 human_approved=180, evidence_validated=180, policy_recomputed=180)
    return finals, audit
