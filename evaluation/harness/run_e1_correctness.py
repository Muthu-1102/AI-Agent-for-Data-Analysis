"""
Experiment E1: End-to-End Correctness & Consistency Runner
Evaluates DEV set (12 questions) and frozen HELD-OUT set (48 questions x 3 repetitions).
Measures:
- Pipeline completion rate
- Execution success rate
- Computation correctness (Primary)
- Summary correctness (Secondary)
- Run-to-run consistency & variance across repetitions
- Per-stage latency and attempt tracking via in-process telemetry wrapper
"""

import os
import sys
import json
import time
import asyncio
import traceback
from typing import Dict, Any, List

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure backend and evaluation modules resolve correctly
sys.path.insert(0, os.path.abspath("backend"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.show = lambda *args, **kwargs: None

sys.path.insert(0, os.path.abspath("."))

import config
# Set active evaluated model
EVAL_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
config.settings.GROQ_MODEL = EVAL_MODEL

from core.orchestrator import Orchestrator
from evaluation.harness.answer_matcher import AnswerMatcher

class InstrumentedOrchestrator(Orchestrator):
    """
    Subclass that wraps agent execution to record:
    - Exact attempt counts per agent
    - Per-stage monotonic latency (seconds)
    - Per-stage errors and state snapshots
    - Preserves execution_success from internal pipeline state
    """
    def __init__(self):
        super().__init__()
        self.code_agent.llm_service.default_model = EVAL_MODEL
        self.report_agent.llm_service.default_model = EVAL_MODEL
        
        # Bound max_tokens to prevent OTPM exhaustion on on-demand Groq tier
        orig_code_gen = self.code_agent.llm_service.generate_response
        async def bounded_code_gen(prompt, model=None, temperature=0.1, max_tokens=4096):
            return await orig_code_gen(prompt, model=model or EVAL_MODEL, temperature=temperature, max_tokens=min(max_tokens, 800))
        self.code_agent.llm_service.generate_response = bounded_code_gen
        
        orig_report_gen = self.report_agent.llm_service.generate_response
        async def bounded_report_gen(prompt, model=None, temperature=0.3, max_tokens=2048):
            return await orig_report_gen(prompt, model=model or EVAL_MODEL, temperature=temperature, max_tokens=min(max_tokens, 800))
        self.report_agent.llm_service.generate_response = bounded_report_gen
        
        self.telemetry = {
            "stage_latencies": {},
            "stage_attempts": {},
            "stage_errors": {},
            "final_state": {}
        }

    async def _run_agent(self, agent, state: Dict[str, Any]) -> Dict[str, Any]:
        agent_name = agent.__class__.__name__
        max_retries = config.settings.MAX_RETRIES
        attempts = 0
        t0 = time.perf_counter()
        
        while attempts < max_retries:
            try:
                attempts += 1
                result = await agent.process(state)
                if isinstance(result, dict):
                    state.update(result)
                elapsed = time.perf_counter() - t0
                self.telemetry["stage_latencies"][agent_name] = round(elapsed, 4)
                self.telemetry["stage_attempts"][agent_name] = attempts
                return state
            except Exception as e:
                self.telemetry["stage_errors"][agent_name] = str(e)
                if attempts >= max_retries:
                    elapsed = time.perf_counter() - t0
                    self.telemetry["stage_latencies"][agent_name] = round(elapsed, 4)
                    self.telemetry["stage_attempts"][agent_name] = attempts
                    raise RuntimeError(f"{agent_name} failed definitively: {str(e)}")
        return state

    async def run_instrumented(self, query: str, file_id: str) -> Dict[str, Any]:
        t_start = time.perf_counter()
        output = await self.execute_pipeline(query, file_id)
        total_time = round(time.perf_counter() - t_start, 4)
        
        # Merge telemetry
        run_record = {
            "pipeline_output": output,
            "total_latency": total_time,
            "stage_latencies": self.telemetry["stage_latencies"],
            "stage_attempts": self.telemetry["stage_attempts"],
            "stage_errors": self.telemetry["stage_errors"]
        }
        return run_record

def classify_failure(record: Dict[str, Any], match_comp: bool, match_sum: bool) -> str:
    """Classifies outcome into mutually exclusive failure categories."""
    if match_comp and match_sum:
        return "SUCCESS_BOTH"
    if match_comp and not match_sum:
        return "CORRECT_CODE_WRONG_SUMMARY"
        
    err = record["pipeline_output"].get("error") or ""
    stage_errors = record.get("stage_errors", {})
    all_err_text = (err + " " + " ".join(stage_errors.values())).lower()
    
    if "429" in all_err_text or "rate limit" in all_err_text or "model_not_found" in all_err_text or "503" in all_err_text or "500" in all_err_text:
        return "INFRA_ERROR"
        
    if "codeagent" in all_err_text:
        if "syntax" in all_err_text:
            return "SYNTAX_ERROR"
        return "EXTRACTION_ERROR"
        
    if "validationagent" in all_err_text:
        if "syntax" in all_err_text:
            return "SYNTAX_ERROR"
        return "VALIDATION_SECURITY_BLOCKED"
        
    if "execution blocked" in all_err_text or "sandbox" in all_err_text:
        return "SANDBOX_SUBSTRING_BLOCKED"
        
    captured = record["pipeline_output"].get("captured_output", "")
    code = record["pipeline_output"].get("generated_code", "")
    
    # Check if execution failed internally (ExecutionAgent error trace in captured or summary)
    summary = record["pipeline_output"].get("insights_summary") or ""
    if "encountered an error while executing" in summary or "traceback" in summary.lower():
        return "EXECUTION_RUNTIME_ERROR"
        
    if code and captured and not match_comp:
        return "EXECUTED_WRONG_ANSWER"
        
    return "UNCLASSIFIED"

async def run_cohort(questions_path: str, output_jsonl: str, repetitions: int = 1, delay_sec: float = 0.5):
    with open(questions_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    os.makedirs(os.path.dirname(output_jsonl), exist_ok=True)
    records = []
    total_calls = 0

    print(f"Starting execution: {len(questions)} questions x {repetitions} reps -> {output_jsonl}")

    with open(output_jsonl, "w", encoding="utf-8") as out_fp:
        for rep in range(1, repetitions + 1):
            print(f"\n--- Repetition {rep}/{repetitions} ---")
            for idx, q in enumerate(questions, start=1):
                q_id = q["id"]
                query = q["question"]
                file_id = q["dataset"]
                
                # Exponential backoff on rate limits
                backoff = 2.0
                max_retries = 5
                rec = None
                
                for attempt in range(max_retries):
                    try:
                        orch = InstrumentedOrchestrator()
                        rec = await orch.run_instrumented(query, file_id)
                        total_calls += 2 # 1 code + 1 report
                        break
                    except Exception as exc:
                        if "429" in str(exc) or "rate" in str(exc).lower():
                            print(f"[{q_id} Rep {rep}] Rate limit hit (attempt {attempt+1}/{max_retries}). Backing off {backoff:.1f}s...")
                            await asyncio.sleep(backoff)
                            backoff *= 2.0
                        else:
                            rec = {
                                "pipeline_output": {"status": "fatal", "error": str(exc)},
                                "total_latency": 0.0,
                                "stage_latencies": {},
                                "stage_attempts": {},
                                "stage_errors": {"Fatal": str(exc)}
                            }
                            break
                            
                if rec is None:
                    rec = {
                        "pipeline_output": {"status": "fatal", "error": "Exceeded max rate limit backoff retries"},
                        "total_latency": 0.0,
                        "stage_latencies": {},
                        "stage_attempts": {},
                        "stage_errors": {"RateLimit": "HTTP 429 rate limit exceeded"}
                    }
                    
                p_out = rec["pipeline_output"]
                captured_out = p_out.get("captured_output") or ""
                insights_sum = p_out.get("insights_summary") or ""
                
                # Check answers
                comp_match, comp_cand, comp_reason = AnswerMatcher.match(captured_out, q)
                sum_match, sum_cand, sum_reason = AnswerMatcher.match(insights_sum, q)
                
                # Determine true execution success from stdout/error
                is_exec_success = (
                    p_out.get("status") == "completed" and 
                    "encountered an error while executing" not in insights_sum and
                    bool(captured_out.strip())
                )
                
                outcome = classify_failure(rec, comp_match, sum_match)
                if comp_match:
                    outcome = "CORRECT"
                
                log_row = {
                    "experiment_id": "E1",
                    "case_id": q_id,
                    "repetition": rep,
                    "dataset": file_id,
                    "category": q["category"],
                    "question": query,
                    "expected_type": q["type"],
                    "ground_truth": q["ground_truth"],
                    "status": p_out.get("status"),
                    "execution_success": is_exec_success,
                    "computation_correct": comp_match,
                    "summary_correct": sum_match,
                    "computation_candidate": comp_cand,
                    "summary_candidate": sum_cand,
                    "outcome_classification": outcome,
                    "total_latency": rec["total_latency"],
                    "stage_latencies": rec["stage_latencies"],
                    "stage_attempts": rec["stage_attempts"],
                    "generated_code": p_out.get("generated_code"),
                    "captured_output": captured_out,
                    "insights_summary": insights_sum,
                    "error": p_out.get("error")
                }
                
                out_fp.write(json.dumps(log_row) + "\n")
                out_fp.flush()
                records.append(log_row)
                
                status_tag = "[PASS]" if comp_match else "[FAIL]"
                print(f"[{idx:02d}/{len(questions):02d} Rep {rep}] {q_id} | {status_tag} | Comp: {comp_match} | Sum: {sum_match} | Lat: {rec['total_latency']}s | Out: {outcome}")
                
                # Pace calls
                await asyncio.sleep(delay_sec)

    print(f"\nCohort finished. Saved {len(records)} records to {output_jsonl}. Estimated LLM calls: {total_calls}")
    return records

if __name__ == "__main__":
    target_mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    dev_path = "evaluation/dataset/questions_dev.json"
    heldout_path = "evaluation/dataset/questions_heldout.json"
    
    out_dev = f"evaluation/results/{target_mode}/e1_dev_raw.jsonl"
    out_heldout = f"evaluation/results/{target_mode}/e1_heldout_raw.jsonl"
    
    if target_mode == "after":
        # Run held-out evaluation directly for post-improvement benchmarking
        print(f"\n=== EXECUTING FROZEN HELD-OUT COHORT (AFTER IMPROVEMENTS) -> {out_heldout} ===")
        asyncio.run(run_cohort(heldout_path, out_heldout, repetitions=3, delay_sec=1.5))
    else:
        # 1. Run Dev Cohort (1 rep)
        print("=== EXECUTING DEV COHORT ===")
        asyncio.run(run_cohort(dev_path, out_dev, repetitions=1, delay_sec=1.2))
        
        # 2. Run Held-Out Cohort (3 reps)
        print(f"\n=== EXECUTING FROZEN HELD-OUT COHORT (3 REPETITIONS) -> {out_heldout} ===")
        asyncio.run(run_cohort(heldout_path, out_heldout, repetitions=3, delay_sec=1.2))
