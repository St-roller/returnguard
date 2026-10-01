"""Deterministic formal evaluation; inference files contain no gold labels."""
from __future__ import annotations

import math
import statistics
from fractions import Fraction

ROUTES = ("eligible", "ineligible", "manual_review")
FIELDS = ("return_reason", "tag_status", "damage_or_stain", "use_beyond_inspection")


def wilson(k: int, n: int) -> list[float] | None:
    if n == 0:
        return None
    if not 0 <= k <= n:
        raise ValueError("invalid proportion counts")
    z = 1.959963984540054
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, center - half), min(1.0, center + half)]


def proportion(k: int, n: int) -> dict:
    return {"numerator": k, "denominator": n, "value": k / n if n else None,
            "wilson_95": wilson(k, n)}


def auto_candidate(row: dict) -> bool:
    return (row["evaluation_status"] == "completed"
            and row.get("validated_extraction") is not None
            and row.get("candidate_route") in ROUTES[:2]
            and row.get("case_support_score") is not None)


def apply_threshold(row: dict, threshold: float) -> dict:
    if not 0 <= threshold <= 1:
        raise ValueError("invalid threshold")
    out = dict(row)
    if auto_candidate(row):
        accepted = row["case_support_score"] >= threshold
        out["final_route"] = row["candidate_route"] if accepted else "manual_review"
        out["review_reason"] = None if accepted else "low_confidence"
    out["threshold_value"] = threshold
    out["operating_point"] = "provisional_locked_from_dev"
    return out


def join_gold(predictions: list[dict], cases: list[dict]) -> list[dict]:
    gold = {c["case_id"]: c["gold"] for c in cases}
    ids = [r["case_id"] for r in predictions]
    if len(ids) != len(set(ids)) or set(ids) != set(gold):
        raise ValueError("predictions must cover the complete frozen split exactly")
    return [{**r, "gold": gold[r["case_id"]]} for r in predictions]


def threshold_table(rows: list[dict]) -> tuple[list[dict], dict | None]:
    candidates = [r for r in rows if auto_candidate(r)]
    table = []
    for t in sorted({r["case_support_score"] for r in candidates}):
        accepted = [r for r in candidates if r["case_support_score"] >= t]
        correct = sum(r["candidate_route"] == r["gold"]["decision"]["route"] for r in accepted)
        n = len(accepted)
        table.append({"threshold": t, "accepted_n": n, "correct_accepted_n": correct,
                      "coverage": n / len(rows), "selective_accuracy": correct / n,
                      "low_confidence_abstain_n": len(candidates) - n,
                      "feasible": correct * 10 >= n * 9})
    feasible = [p for p in table if p["feasible"] and p["accepted_n"]]
    selected = max(feasible, key=lambda p: (p["accepted_n"],
                   Fraction(p["correct_accepted_n"], p["accepted_n"]), p["threshold"])) if feasible else None
    return table, selected


def support_diagnostic(rows: list[dict]) -> dict:
    c = [r for r in rows if auto_candidate(r)]
    correct = [r["case_support_score"] for r in c if r["candidate_route"] == r["gold"]["decision"]["route"]]
    incorrect = [r["case_support_score"] for r in c if r["candidate_route"] != r["gold"]["decision"]["route"]]
    bins = []
    for label, lo, hi in (("<0.50", 0, .5), ("0.50–0.69", .5, .7),
                           ("0.70–0.89", .7, .9), ("0.90–1.00", .9, 1.01)):
        subset = [r for r in c if lo <= r["case_support_score"] < hi]
        err = sum(r["candidate_route"] != r["gold"]["decision"]["route"] for r in subset)
        bins.append({"bin": label, "n": len(subset), "candidate_route_errors": err,
                     "error_rate": err / len(subset) if subset else None})
    scores = correct + incorrect
    return {"scope": "dev auto-route candidates only; descriptive ranking, not calibration",
            "auto_candidate_n": len(c), "bins": bins,
            "median_correct": statistics.median(correct) if correct else None,
            "median_incorrect": statistics.median(incorrect) if incorrect else None,
            "min_score": min(scores) if scores else None, "max_score": max(scores) if scores else None,
            "unique_scores_n": len(set(scores)),
            "auroc_correctness": (sum((a > b) + .5 * (a == b) for a in correct for b in incorrect)
                                   / (len(correct) * len(incorrect))) if correct and incorrect else None}


def diagnostics(rows: list[dict]) -> dict:
    n = len(rows)
    field_counts = {f: 0 for f in FIELDS}
    exact = 0
    for r in rows:
        raw = r.get("raw_structured_extraction")
        matches = []
        for f in FIELDS:
            value = raw.get(f, {}).get("value") if isinstance(raw, dict) and isinstance(raw.get(f), dict) else None
            match = value == r["gold"]["extraction"][f]["value"]
            field_counts[f] += match
            matches.append(match)
        exact += all(matches)
    return {"n": n, "field_value_accuracy": {f: proportion(k, n) for f, k in field_counts.items()},
            "all_four_value_exact_accuracy": proportion(exact, n),
            "hard_validation_failure_n": sum(r["evaluation_status"] == "validation_failure" for r in rows),
            "evidence_valid_case_n": sum(r.get("validated_extraction") is not None for r in rows),
            "candidate_route_accuracy": proportion(sum(r.get("candidate_route") == r["gold"]["decision"]["route"] for r in rows), n),
            "candidate_rule_accuracy": proportion(sum(r.get("candidate_rule_id") == r["gold"]["decision"]["rule_id"] for r in rows), n),
            "candidate_policy_required_manual_n": sum(r.get("candidate_route") == "manual_review" for r in rows),
            "candidate_auto_route_n": sum(r.get("candidate_route") in ROUTES[:2] for r in rows),
            "execution_failure_n": sum(r["evaluation_status"] == "execution_failure" for r in rows)}


def metrics(rows: list[dict], *, dev_selected: bool = False) -> dict:
    n = len(rows)
    auto = [r for r in rows if r["final_route"] in ROUTES[:2]]
    correct = sum(r["final_route"] == r["gold"]["decision"]["route"] for r in auto)
    manual_gold = [r for r in rows if r["gold"]["decision"]["route"] == "manual_review"]
    manual_correct = sum(r["final_route"] == "manual_review" for r in manual_gold)
    matrix = {g: {p: 0 for p in ROUTES} for g in ROUTES}
    abstentions = {key: 0 for key in ("policy_required", "low_confidence", "validation_failure", "execution_failure")}
    for r in rows:
        matrix[r["gold"]["decision"]["route"]][r["final_route"]] += 1
        if r["final_route"] == "manual_review":
            abstentions[r["review_reason"]] += 1
    errors = [r for r in rows if auto_candidate(r) and r["candidate_route"] != r["gold"]["decision"]["route"]]
    captured = sum(r["review_reason"] == "low_confidence" for r in errors)
    return {"n": n, "auto_routed_n": len(auto), "correct_auto_n": correct,
            "coverage": proportion(len(auto), n), "selective_accuracy": proportion(correct, len(auto)),
            "route_accuracy": proportion(sum(r["final_route"] == r["gold"]["decision"]["route"] for r in rows), n),
            "manual_review_recall": proportion(manual_correct, len(manual_gold)),
            "gold_manual_auto_routed_n": len(manual_gold) - manual_correct,
            "abstentions": {k: {"n": v, "rate": v / n} for k, v in abstentions.items()},
            "confusion_matrix_gold_rows_final_columns": matrix,
            "error_capture": {"captured_n": captured, "error_candidate_n": len(errors),
                              "value": captured / len(errors) if errors else None,
                              "display": "N/A" if not errors else f"{captured}/{len(errors)}"},
            "dev_coverage_target_60_percent_met": len(auto) * 10 >= n * 6,
            "selective_accuracy_constraint_met": bool(auto) and correct * 10 >= len(auto) * 9,
            "interval_note": "Descriptive Wilson 95%; threshold selected on these same dev data; optimistic with respect to selection." if dev_selected else "Descriptive Wilson 95% intervals.",
            "diagnostics": diagnostics(rows)}
