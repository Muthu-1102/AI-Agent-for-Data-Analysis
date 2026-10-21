"""
Baseline Evaluation Summary & Metric Calculator
Reads raw result JSONL files from evaluation/results/baseline/ and computes:
- Wilson 95% confidence intervals for all proportions
- Run-to-run consistency across repetitions
- Complete failure taxonomy (Experiment E2)
- Latency percentiles (p50, p95, max)
- Grounding and Security metrics
Saves consolidated summary to evaluation/results/baseline/baseline_summary.json
"""

import os
import sys
import json
import math
import numpy as np
from typing import Dict, Any, List, Tuple

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float, float]:
    """
    Computes Wilson score interval for a binomial proportion.
    Returns (center, lower, upper).
    """
    if total == 0:
        return (0.0, 0.0, 0.0)
    
    # z for 95% confidence = 1.95996
    z = 1.959963984540054
    p = successes / total
    
    denominator = 1 + (z**2) / total
    center = (p + (z**2) / (2 * total)) / denominator
    spread = (z / denominator) * math.sqrt((p * (1 - p) / total) + ((z**2) / (4 * (total**2))))
    
    lower = max(0.0, center - spread)
    upper = min(1.0, center + spread)
    return (round(p, 4), round(lower, 4), round(upper, 4))

def load_jsonl(filepath: str) -> List[Dict[str, Any]]:
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def summarize_e1(e1_file: str) -> Dict[str, Any]:
    records = load_jsonl(e1_file)
    if not records:
        return {"status": "EMPTY"}
        
    n = len(records)
    completed = sum(1 for r in records if r.get("status") == "completed")
    exec_success = sum(1 for r in records if r.get("execution_success"))
    comp_correct = sum(1 for r in records if r.get("computation_correct"))
    sum_correct = sum(1 for r in records if r.get("summary_correct"))
    
    # Exclude infrastructure errors for conditional accuracy
    non_infra = [r for r in records if r.get("outcome_classification") != "INFRA_ERROR"]
    n_cond = len(non_infra)
    comp_correct_cond = sum(1 for r in non_infra if r.get("computation_correct"))
    
    # Consistency across repetitions (grouped by case_id)
    by_case = {}
    for r in records:
        cid = r["case_id"]
        by_case.setdefault(cid, []).append(bool(r.get("computation_correct")))
        
    consistency_counts = {3: 0, 2: 0, 1: 0, 0: 0}
    for cid, passes in by_case.items():
        pass_count = sum(passes)
        consistency_counts[pass_count] = consistency_counts.get(pass_count, 0) + 1
        
    # Breakdown by category
    by_cat = {}
    for r in records:
        cat = r.get("category", "Unknown")
        by_cat.setdefault(cat, {"n": 0, "correct": 0})
        by_cat[cat]["n"] += 1
        if r.get("computation_correct"):
            by_cat[cat]["correct"] += 1
            
    cat_summary = {}
    for cat, d in by_cat.items():
        p, lo, hi = wilson_score_interval(d["correct"], d["n"])
        cat_summary[cat] = {
            "n": d["n"],
            "correct": d["correct"],
            "rate": p,
            "ci_95": [lo, hi]
        }
        
    # Breakdown by dataset
    by_ds = {}
    for r in records:
        ds = r.get("dataset", "Unknown")
        by_ds.setdefault(ds, {"n": 0, "correct": 0})
        by_ds[ds]["n"] += 1
        if r.get("computation_correct"):
            by_ds[ds]["correct"] += 1
            
    ds_summary = {}
    for ds, d in by_ds.items():
        p, lo, hi = wilson_score_interval(d["correct"], d["n"])
        ds_summary[ds] = {
            "n": d["n"],
            "correct": d["correct"],
            "rate": p,
            "ci_95": [lo, hi]
        }
        
    # Failure taxonomy (Experiment E2)
    taxonomy = {}
    for r in records:
        out = r.get("outcome_classification", "UNCLASSIFIED")
        taxonomy[out] = taxonomy.get(out, 0) + 1
        
    # Latency stats
    latencies = [r["total_latency"] for r in records if r.get("total_latency", 0) > 0]
    lat_stats = {}
    if latencies:
        lat_stats = {
            "p50": round(float(np.percentile(latencies, 50)), 3),
            "p95": round(float(np.percentile(latencies, 95)), 3),
            "max": round(float(np.max(latencies)), 3),
            "mean": round(float(np.mean(latencies)), 3),
            "std": round(float(np.std(latencies)), 3)
        }
        
    return {
        "n_total_runs": n,
        "n_unique_questions": len(by_case),
        "completion": {
            "count": completed,
            "rate": wilson_score_interval(completed, n)[0],
            "ci_95": list(wilson_score_interval(completed, n)[1:])
        },
        "execution_success": {
            "count": exec_success,
            "rate": wilson_score_interval(exec_success, n)[0],
            "ci_95": list(wilson_score_interval(exec_success, n)[1:])
        },
        "computation_correctness": {
            "count": comp_correct,
            "rate": wilson_score_interval(comp_correct, n)[0],
            "ci_95": list(wilson_score_interval(comp_correct, n)[1:])
        },
        "summary_correctness": {
            "count": sum_correct,
            "rate": wilson_score_interval(sum_correct, n)[0],
            "ci_95": list(wilson_score_interval(sum_correct, n)[1:])
        },
        "conditional_correctness": {
            "n_available": n_cond,
            "count": comp_correct_cond,
            "rate": wilson_score_interval(comp_correct_cond, n_cond)[0] if n_cond else 0.0,
            "ci_95": list(wilson_score_interval(comp_correct_cond, n_cond)[1:]) if n_cond else [0.0, 0.0]
        },
        "consistency_3_reps": consistency_counts,
        "category_breakdown": cat_summary,
        "dataset_breakdown": ds_summary,
        "failure_taxonomy": taxonomy,
        "latency_stats": lat_stats
    }

def summarize_e4(e4_file: str) -> Dict[str, Any]:
    records = load_jsonl(e4_file)
    if not records:
        return {"status": "EMPTY"}
        
    malicious = [r for r in records if r.get("probe_type") == "MALICIOUS"]
    benign = [r for r in records if r.get("probe_type") == "BENIGN"]
    
    # Malicious block rate
    mal_total = len(malicious)
    mal_blocked_val = sum(1 for r in malicious if r.get("validation_agent_blocked"))
    mal_blocked_sand = sum(1 for r in malicious if r.get("sandbox_is_safe_code_blocked") or r.get("sandbox_blocked"))
    mal_blocked_e2e = sum(1 for r in malicious if r.get("end_to_end_blocked"))
    
    # Per-category malicious bypasses
    mal_cats = {}
    for r in malicious:
        c = r.get("category", "General")
        mal_cats.setdefault(c, {"total": 0, "blocked": 0, "bypassed": 0, "bypasses": []})
        mal_cats[c]["total"] += 1
        if r.get("end_to_end_blocked"):
            mal_cats[c]["blocked"] += 1
        else:
            mal_cats[c]["bypassed"] += 1
            mal_cats[c]["bypasses"].append(r.get("probe_id") or r.get("case_id"))
            
    # Benign false positives
    ben_total = len(benign)
    ben_fp_val = sum(1 for r in benign if r.get("validation_agent_blocked"))
    ben_fp_sand = sum(1 for r in benign if r.get("sandbox_is_safe_code_blocked") or r.get("sandbox_blocked"))
    ben_fp_e2e = sum(1 for r in benign if r.get("end_to_end_blocked"))
    
    return {
        "malicious_corpus": {
            "total_probes": mal_total,
            "validation_agent_blocked": mal_blocked_val,
            "sandbox_substring_blocked": mal_blocked_sand,
            "end_to_end_blocked": mal_blocked_e2e,
            "overall_block_rate": wilson_score_interval(mal_blocked_e2e, mal_total)[0],
            "ci_95": list(wilson_score_interval(mal_blocked_e2e, mal_total)[1:]),
            "category_breakdown": mal_cats
        },
        "benign_corpus": {
            "total_snippets": ben_total,
            "validation_agent_false_positives": ben_fp_val,
            "sandbox_substring_false_positives": ben_fp_sand,
            "end_to_end_false_positives": ben_fp_e2e,
            "false_positive_rate": wilson_score_interval(ben_fp_e2e, ben_total)[0],
            "ci_95": list(wilson_score_interval(ben_fp_e2e, ben_total)[1:])
        }
    }

def summarize_e6(e6_file: str) -> Dict[str, Any]:
    records = load_jsonl(e6_file)
    if not records:
        return {"status": "EMPTY"}
        
    n_runs = len(records)
    total_nums = sum(r.get("total_summary_numbers", 0) for r in records)
    total_grounded = sum(r.get("grounded_count", 0) for r in records)
    fully_grounded = sum(1 for r in records if r.get("is_fully_grounded"))
    
    num_rate, num_lo, num_hi = wilson_score_interval(total_grounded, total_nums) if total_nums else (1.0, 1.0, 1.0)
    sum_rate, sum_lo, sum_hi = wilson_score_interval(fully_grounded, n_runs) if n_runs else (0.0, 0.0, 0.0)
    
    return {
        "executed_runs_evaluated": n_runs,
        "total_summary_numbers": total_nums,
        "grounded_numbers_count": total_grounded,
        "numeric_grounding_rate": num_rate,
        "numeric_grounding_ci_95": [num_lo, num_hi],
        "fully_grounded_summaries_count": fully_grounded,
        "fully_grounded_summary_rate": sum_rate,
        "fully_grounded_summary_ci_95": [sum_lo, sum_hi]
    }

def summarize_e5(e5_file: str) -> Dict[str, Any]:
    records = load_jsonl(e5_file)
    if not records:
        return {"status": "EMPTY"}
        
    edge_csvs = [r for r in records if r.get("case_type") in ("edge_csv", "EDGE_CSV")]
    unanswerable = [r for r in records if r.get("case_type") in ("unanswerable", "UNANSWERABLE_QUESTION")]
    
    edge_graceful = sum(1 for r in edge_csvs if r.get("handled_gracefully"))
    unans_graceful = sum(1 for r in unanswerable if r.get("handled_gracefully"))
    unans_fabricated = sum(1 for r in unanswerable if r.get("fabricated_answer"))
    
    return {
        "edge_csvs": {
            "total": len(edge_csvs),
            "graceful": edge_graceful,
            "rate": wilson_score_interval(edge_graceful, len(edge_csvs))[0] if edge_csvs else 0.0,
            "ci_95": list(wilson_score_interval(edge_graceful, len(edge_csvs))[1:]) if edge_csvs else [0.0, 0.0]
        },
        "unanswerable_questions": {
            "total": len(unanswerable),
            "graceful": unans_graceful,
            "rate": wilson_score_interval(unans_graceful, len(unanswerable))[0] if unanswerable else 0.0,
            "ci_95": list(wilson_score_interval(unans_graceful, len(unanswerable))[1:]) if unanswerable else [0.0, 0.0],
            "fabricated_count": unans_fabricated,
            "fabricated_rate": wilson_score_interval(unans_fabricated, len(unanswerable))[0] if unanswerable else 0.0,
            "fabricated_ci_95": list(wilson_score_interval(unans_fabricated, len(unanswerable))[1:]) if unanswerable else [0.0, 0.0]
        }
    }

def generate_all_summaries():
    print("Generating comprehensive evaluation summary from baseline raw logs...")
    
    e1_file = "evaluation/results/baseline/e1_heldout_raw.jsonl"
    e4_file = "evaluation/results/baseline/e4_security_raw.jsonl"
    e5_file = "evaluation/results/baseline/e5_robustness_raw.jsonl"
    e6_file = "evaluation/results/baseline/e6_grounding_raw.jsonl"
    
    summary = {
        "experiment_e1_heldout": summarize_e1(e1_file),
        "experiment_e4_security": summarize_e4(e4_file),
        "experiment_e5_robustness": summarize_e5(e5_file),
        "experiment_e6_grounding": summarize_e6(e6_file)
    }
    
    out_path = "evaluation/results/baseline/baseline_summary.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        
    print(f"Baseline summary written to {out_path}")
    return summary

if __name__ == "__main__":
    generate_all_summaries()
