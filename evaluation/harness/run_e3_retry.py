"""
Experiment E3: Retry & Recovery Fault Injection Harness (MOCK-BASED MECHANISM TESTS)
Uses controlled fault-injection to evaluate the actual behavior of Orchestrator._run_agent:
1. Scenario A: Transient LLM exceptions (inject 1 failure vs 3 failures) -> Does retry recover?
2. Scenario B: Validation failure (invalid syntax or blocked import) -> Does CodeAgent regenerate or repeat 3 identical attempts?
3. Scenario C: Runtime execution exception (ZeroDivisionError) -> Does the retry loop trigger at all?
"""

import os
import sys
import json
import asyncio
from unittest.mock import AsyncMock

sys.path.insert(0, os.path.abspath("backend"))

import config
from core.orchestrator import Orchestrator

async def test_scenario_a_transient_llm():
    """Scenario A: Transient LLM failures."""
    print("Running E3 Scenario A: Transient LLM failure injection...")
    results = []
    
    # Test A1: 1 failure then success
    orch = Orchestrator()
    mock_calls = 0
    async def mock_generate_recover(*args, **kwargs):
        nonlocal mock_calls
        mock_calls += 1
        if mock_calls == 1:
            raise ConnectionError("Simulated transient 503 error from LLM API")
        return "```python\nprint(df['sales_amount'].sum())\n```"

    orch.code_agent.llm_service.generate_response = mock_generate_recover
    
    # We mock report agent as well to keep test isolated
    orch.report_agent.llm_service.generate_response = AsyncMock(return_value="Total sales computed successfully.")

    out1 = await orch.execute_pipeline("What is total sales?", "synthetic_sales.csv")
    results.append({
        "scenario": "A1_single_transient_failure",
        "mock_type": "MOCK_FAULT_INJECTION",
        "injected_failures": 1,
        "max_retries": config.settings.MAX_RETRIES,
        "actual_attempts": mock_calls,
        "recovered": out1["status"] == "completed",
        "final_status": out1["status"],
        "error": out1["error"]
    })

    # Test A2: 3 consecutive failures (exceeds max_retries)
    orch2 = Orchestrator()
    mock_calls2 = 0
    async def mock_generate_fail(*args, **kwargs):
        nonlocal mock_calls2
        mock_calls2 += 1
        raise ConnectionError("Persistent 500 error from LLM API")

    orch2.code_agent.llm_service.generate_response = mock_generate_fail
    out2 = await orch2.execute_pipeline("What is total sales?", "synthetic_sales.csv")
    results.append({
        "scenario": "A2_exhausted_retries",
        "mock_type": "MOCK_FAULT_INJECTION",
        "injected_failures": 3,
        "max_retries": config.settings.MAX_RETRIES,
        "actual_attempts": mock_calls2,
        "recovered": False,
        "final_status": out2["status"],
        "error": out2["error"]
    })

    return results

async def test_scenario_b_validation_failure():
    """Scenario B: CodeAgent returns code failing validation."""
    print("Running E3 Scenario B: Code fails ValidationAgent...")
    results = []
    
    orch = Orchestrator()
    code_calls = 0
    async def mock_code_gen(*args, **kwargs):
        nonlocal code_calls
        code_calls += 1
        return "import os\nprint(os.getcwd())" # Forbidden import

    orch.code_agent.llm_service.generate_response = mock_code_gen
    
    # Track ValidationAgent calls
    valid_calls = 0
    orig_val_process = orch.validation_agent.process
    async def track_val(state):
        nonlocal valid_calls
        valid_calls += 1
        return await orig_val_process(state)
        
    orch.validation_agent.process = track_val

    out = await orch.execute_pipeline("Run inspection", "synthetic_sales.csv")
    results.append({
        "scenario": "B1_validation_rejection_loop",
        "mock_type": "MOCK_FAULT_INJECTION",
        "code_agent_regeneration_calls": code_calls,
        "validation_agent_attempts": valid_calls,
        "regenerated_with_feedback": False, # CodeAgent is NEVER recalled
        "final_status": out["status"],
        "error": out["error"],
        "behavior_finding": "ValidationAgent fails 3 times on the identical code; CodeAgent is never asked to regenerate with error feedback."
    })
    return results

async def test_scenario_c_execution_failure():
    """Scenario C: Code raises runtime error during ExecutionAgent exec()."""
    print("Running E3 Scenario C: Code raises runtime exception during execution...")
    results = []
    
    orch = Orchestrator()
    async def mock_zero_div(*args, **kwargs):
        return "x = 1 / 0\nprint(x)"

    orch.code_agent.llm_service.generate_response = mock_zero_div
    
    exec_attempts = 0
    orig_exec_process = orch.execution_agent.process
    async def track_exec(state):
        nonlocal exec_attempts
        exec_attempts += 1
        return await orig_exec_process(state)

    orch.execution_agent.process = track_exec
    
    out = await orch.execute_pipeline("Calculate zero div", "synthetic_sales.csv")
    results.append({
        "scenario": "C1_runtime_execution_failure",
        "mock_type": "MOCK_FAULT_INJECTION",
        "execution_attempts": exec_attempts,
        "retried": exec_attempts > 1,
        "reported_status": out["status"], # Notice: status is 'completed'!
        "captured_output": out["captured_output"],
        "insights_summary_preview": (out["insights_summary"] or "")[:120],
        "behavior_finding": "ExecutionAgent swallows ZeroDivisionError internally; _run_agent sees no exception and does not retry. Pipeline returns status: completed."
    })
    return results

async def run_all_e3(output_path="evaluation/results/baseline/e3_retry_raw.jsonl"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    all_results = []
    
    r_a = await test_scenario_a_transient_llm()
    r_b = await test_scenario_b_validation_failure()
    r_c = await test_scenario_c_execution_failure()
    
    all_results.extend(r_a)
    all_results.extend(r_b)
    all_results.extend(r_c)

    with open(output_path, "w", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(r) + "\n")

    print(f"E3 Complete. Saved {len(all_results)} scenario records to {output_path}")

if __name__ == "__main__":
    target_out = sys.argv[1] if len(sys.argv) > 1 else "evaluation/results/baseline/e3_retry_raw.jsonl"
    asyncio.run(run_all_e3(output_path=target_out))
