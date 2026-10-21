"""
Experiment E6: Report Faithfulness & Numerical Grounding Analysis
Deterministically verifies whether numerical facts asserted in `insights_summary`
are faithfully grounded in the underlying `captured_output` of pandas execution.
"""

import os
import sys
import json
import re
from typing import Dict, Any, List, Set, Tuple

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def extract_numbers_from_text(text: str) -> List[Tuple[float, str]]:
    """
    Extracts numerical values from text, stripping currency symbols, commas, percent signs.
    Returns list of (float_value, raw_token).
    """
    # Regex matching integers, floats, currencies, percentages
    # e.g., $1,234.56, 758584.41, 15%, 204, 3.14
    pattern = r'(?<![A-Za-z_])[\$€£]?\s*([+-]?[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|[+-]?[0-9]+(?:\.[0-9]+)?)\s*%?'
    
    matches = re.finditer(pattern, text)
    numbers = []
    for m in matches:
        raw = m.group(1).replace(",", "").strip()
        try:
            val = float(raw)
            # Filter out obvious markdown bullet indices or isolated 0/1 unless relevant
            numbers.append((val, m.group(0).strip()))
        except ValueError:
            continue
    return numbers

def extract_prompt_numbers(question: str) -> Set[float]:
    """Extract numbers present in the question to avoid flagging prompt-carried constants."""
    q_nums = extract_numbers_from_text(question)
    s = set()
    for v, _ in q_nums:
        s.add(round(v, 4))
        # Also include percentage equivalence e.g. 15 and 0.15
        if 0 < v < 1:
            s.add(round(v * 100, 2))
        elif 1 <= v <= 100:
            s.add(round(v / 100, 4))
    return s

def extract_output_numbers(captured_output: str) -> Set[float]:
    """Extract all distinct numeric values from captured pandas stdout."""
    nums = extract_numbers_from_text(captured_output)
    s = set()
    for v, _ in nums:
        s.add(round(v, 4))
        # Add common rounding variants
        s.add(round(v, 2))
        s.add(round(v, 1))
        s.add(round(v, 0))
    return s

def check_grounding(summary: str, captured_output: str, question: str) -> Dict[str, Any]:
    prompt_nums = extract_prompt_numbers(question)
    output_nums = extract_output_numbers(captured_output)
    summary_nums = extract_numbers_from_text(summary)
    
    # Filter out numbers that were given in the question (e.g. "discount > 0.15" -> 15% in summary)
    eval_nums = []
    for val, raw in summary_nums:
        # If val is in prompt, consider it context
        v_round = round(val, 4)
        if v_round in prompt_nums:
            continue
        eval_nums.append((val, raw))
        
    if not eval_nums:
        return {
            "total_summary_numbers": 0,
            "grounded_count": 0,
            "ungrounded_count": 0,
            "grounding_rate": 1.0,
            "is_fully_grounded": True,
            "ungrounded_numbers": []
        }
        
    grounded = []
    ungrounded = []
    
    for val, raw in eval_nums:
        # Check direct or approximate match against output numbers
        matched = False
        for out_v in output_nums:
            if abs(val - out_v) <= 0.05 or (out_v != 0 and abs(val - out_v) / abs(out_v) <= 0.015):
                matched = True
                break
            # Percentage match e.g. 0.45 in output vs 45% in summary
            if 0 <= out_v <= 1 and abs(val - (out_v * 100)) <= 0.5:
                matched = True
                break
        if matched:
            grounded.append((val, raw))
        else:
            ungrounded.append((val, raw))
            
    total = len(eval_nums)
    g_count = len(grounded)
    u_count = len(ungrounded)
    rate = g_count / total if total > 0 else 1.0
    
    return {
        "total_summary_numbers": total,
        "grounded_count": g_count,
        "ungrounded_count": u_count,
        "grounding_rate": round(rate, 4),
        "is_fully_grounded": u_count == 0,
        "ungrounded_numbers": [raw for _, raw in ungrounded]
    }

def run_e6_analysis(input_jsonl: str, output_jsonl: str):
    if not os.path.exists(input_jsonl):
        print(f"Error: {input_jsonl} does not exist.")
        return
        
    with open(input_jsonl, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f]
        
    # Analyze executed cases
    executed_records = [r for r in records if r.get("execution_success")]
    print(f"Evaluating numerical grounding across {len(executed_records)} executed runs...")
    
    out_rows = []
    total_nums = 0
    total_grounded = 0
    fully_grounded_runs = 0
    
    for r in executed_records:
        summary = r.get("insights_summary") or ""
        captured = r.get("captured_output") or ""
        q = r.get("question") or ""
        
        g_res = check_grounding(summary, captured, q)
        row = {
            "experiment_id": "E6",
            "case_id": r.get("case_id"),
            "repetition": r.get("repetition"),
            "question": q,
            "total_summary_numbers": g_res["total_summary_numbers"],
            "grounded_count": g_res["grounded_count"],
            "ungrounded_count": g_res["ungrounded_count"],
            "grounding_rate": g_res["grounding_rate"],
            "is_fully_grounded": g_res["is_fully_grounded"],
            "ungrounded_numbers": g_res["ungrounded_numbers"]
        }
        out_rows.append(row)
        
        total_nums += g_res["total_summary_numbers"]
        total_grounded += g_res["grounded_count"]
        if g_res["is_fully_grounded"]:
            fully_grounded_runs += 1
            
    os.makedirs(os.path.dirname(output_jsonl), exist_ok=True)
    with open(output_jsonl, "w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r) + "\n")
            
    overall_num_rate = total_grounded / total_nums if total_nums > 0 else 1.0
    summary_rate = fully_grounded_runs / len(executed_records) if executed_records else 0.0
    
    print(f"\n--- E6 Grounding Results ({len(executed_records)} runs) ---")
    print(f"Total Extracted Numbers: {total_nums}")
    print(f"Faithfully Grounded Numbers: {total_grounded} ({overall_num_rate*100:.1f}%)")
    print(f"Fully Grounded Summaries: {fully_grounded_runs}/{len(executed_records)} ({summary_rate*100:.1f}%)")
    print(f"Raw results saved to {output_jsonl}")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    e1_heldout = f"evaluation/results/{mode}/e1_heldout_raw.jsonl"
    e6_out = f"evaluation/results/{mode}/e6_grounding_raw.jsonl"
    run_e6_analysis(e1_heldout, e6_out)
