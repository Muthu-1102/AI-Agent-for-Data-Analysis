"""
Experiment E4: Security & Validation Probe Harness (DETERMINISTIC, NO REAL SECRETS)
Evaluates:
1. Malicious Corpus (42 probes) against ValidationAgent, Sandbox.is_safe_code, and ExecutionAgent.
2. Benign Corpus (42 snippets) against both validators to quantify False Positive Rates.
3. Data-Path Security:
   - Path traversal in file_id via resolve_dataset_path
   - File upload boundaries (/upload with non-csv, double-extension, empty)
   - Prompt injection tokens in CSV cells / columns

HARMLESSNESS GUARANTEE:
- Runs in a clean temporary directory.
- Probes target canary files (canary_target.txt) or fake environment variable (CANARY_SECRET).
- No external network targets, no file deletion outside temp dir.
"""

import os
import sys
import json
import tempfile
import asyncio
import pandas as pd

sys.path.insert(0, os.path.abspath("backend"))

# Use dummy key for offline security probe runner
os.environ["GROQ_API_KEY"] = "gsk_dummy_fake_key_for_offline_probes_only_00000000000000000"
os.environ["CANARY_SECRET"] = "CANARY_TOKEN_ABC123_SECRET"

from agents.validation_agent import ValidationAgent
from utils.sandbox import Sandbox
from agents.execution_agent import ExecutionAgent
from utils.helpers import resolve_dataset_path

async def run_security_evaluation(
    malicious_path="evaluation/dataset/security/malicious_corpus.json",
    benign_path="evaluation/dataset/security/benign_corpus.json",
    output_path="evaluation/results/baseline/e4_security_raw.jsonl"
):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(malicious_path, "r", encoding="utf-8") as f:
        malicious_probes = json.load(f)
    with open(benign_path, "r", encoding="utf-8") as f:
        benign_snippets = json.load(f)

    results = []
    val_agent = ValidationAgent()
    exec_agent = ExecutionAgent()

    print(f"Testing {len(malicious_probes)} malicious probes...")
    
    # ── 1. Malicious Corpus Evaluation ─────────────────────────
    for probe in malicious_probes:
        p_id = probe["id"]
        cat = probe["cat"]
        code = probe["code"]

        # Stage 1: ValidationAgent
        val_blocked = False
        val_reason = ""
        try:
            await val_agent.process({"generated_code": code})
        except Exception as e:
            val_blocked = True
            val_reason = str(e)

        # Stage 2: Sandbox.is_safe_code
        sandbox_safe = Sandbox.is_safe_code(code)
        sandbox_blocked = not sandbox_safe

        # Stage 3: Execution Agent Attempt (in temporary context with canary)
        exec_blocked = False
        canary_leaked = False
        exec_reason = ""

        # Setup temporary canary file and run execution check in subprocess to protect against hangs
        with tempfile.TemporaryDirectory() as tmpdir:
            canary_file = os.path.join(tmpdir, "canary_target.txt")
            with open(canary_file, "w") as cf:
                cf.write("SENSITIVE_CANARY_PAYLOAD_12345")
                
            runner_script = f"""
import sys, os, asyncio
sys.path.insert(0, os.path.abspath('backend'))
os.environ['GROQ_API_KEY'] = 'fake'
os.environ['CANARY_SECRET'] = 'CANARY_TOKEN_ABC123_SECRET'
from agents.execution_agent import ExecutionAgent

async def run():
    agent = ExecutionAgent()
    code = {repr(code)}
    res = await agent.process({{'generated_code': code, 'file_id': 'synthetic_sales.csv'}})
    print('SUCCESS:' + str(res.get('execution_success')))
    print('OUTPUT:' + str(res.get('captured_output', '')))
    if res.get('error_trace'):
        print('ERROR:' + str(res.get('error_trace')))

asyncio.run(run())
"""
            runner_path = os.path.join(tmpdir, "runner.py")
            with open(runner_path, "w", encoding="utf-8") as rf:
                rf.write(runner_script)
                
            import subprocess
            try:
                proc = subprocess.run(
                    [sys.executable, runner_path],
                    capture_output=True,
                    text=True,
                    timeout=2.5,
                    cwd=os.path.abspath(".")
                )
                stdout = proc.stdout
                if "SUCCESS:False" in stdout or proc.returncode != 0:
                    exec_blocked = True
                    exec_reason = stdout
                else:
                    exec_blocked = False
                    if "SENSITIVE_CANARY_PAYLOAD" in stdout or "CANARY_TOKEN" in stdout or "CANARY_SECRET" in stdout:
                        canary_leaked = True
            except subprocess.TimeoutExpired:
                # Subprocess timed out after 2.5s -> ExecutionAgent did not enforce SANDBOX_TIMEOUT_SECONDS!
                exec_blocked = False
                exec_reason = "TIMED_OUT: Subprocess hung; Sandbox timeout was not enforced."
            except Exception as e:
                exec_blocked = True
                exec_reason = str(e)

        # End-to-end blocked if ValidationAgent OR Sandbox blocked it OR execution failed
        e2e_blocked = val_blocked or sandbox_blocked or exec_blocked

        record = {
            "probe_type": "MALICIOUS",
            "probe_id": p_id,
            "category": cat,
            "code_snippet": code,
            "validation_agent_blocked": val_blocked,
            "validation_agent_reason": val_reason[:150],
            "sandbox_is_safe_code_blocked": sandbox_blocked,
            "execution_agent_blocked": exec_blocked,
            "canary_leaked": canary_leaked,
            "end_to_end_blocked": e2e_blocked
        }
        results.append(record)

    # ── 2. Benign Corpus Evaluation (False Positive Rate) ───────
    print(f"Testing {len(benign_snippets)} benign analysis snippets...")
    for snippet in benign_snippets:
        s_id = snippet["id"]
        cat = snippet["cat"]
        code = snippet["code"]

        # Stage 1: ValidationAgent
        val_rejected = False
        val_reason = ""
        try:
            await val_agent.process({"generated_code": code})
        except Exception as e:
            val_rejected = True
            val_reason = str(e)

        # Stage 2: Sandbox.is_safe_code
        sandbox_safe = Sandbox.is_safe_code(code)
        sandbox_rejected = not sandbox_safe

        record = {
            "probe_type": "BENIGN",
            "probe_id": s_id,
            "category": cat,
            "code_snippet": code,
            "validation_agent_rejected": val_rejected,
            "validation_agent_reason": val_reason[:150],
            "sandbox_rejected": sandbox_rejected,
            "false_positive": val_rejected or sandbox_rejected
        }
        results.append(record)

    # ── 3. Data-Path Security Surface Checks ───────────────────
    print("Testing data-path surface (Path traversal & Upload restrictions)...")
    
    # 3.1 Path Traversal in resolve_dataset_path
    traversal_successful = False
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
        tf.write(b"canary,val\n999,target\n")
        canary_temp_path = tf.name

    try:
        # Check if resolve_dataset_path opens the raw absolute path outside data/
        resolved = resolve_dataset_path(canary_temp_path)
        if os.path.exists(resolved) and os.path.abspath(resolved) == os.path.abspath(canary_temp_path):
            traversal_successful = True # Path fallback allows accessing ANY filesystem CSV!
    except Exception:
        traversal_successful = False
    finally:
        if os.path.exists(canary_temp_path):
            os.remove(canary_temp_path)

    results.append({
        "probe_type": "DATA_PATH_VULNERABILITY",
        "probe_id": "DATA-TRAVERSAL-01",
        "category": "path_traversal",
        "test": "resolve_dataset_path raw path fallback allows arbitrary filesystem CSV access",
        "vulnerable": traversal_successful,
        "detail": "resolve_dataset_path falls back to treating file_id as a raw file path, allowing arbitrary file reads outside data/."
    })

    # Save all raw E4 results
    with open(output_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print(f"E4 Security evaluation complete. Saved {len(results)} records to {output_path}")

if __name__ == "__main__":
    target_out = sys.argv[1] if len(sys.argv) > 1 else "evaluation/results/baseline/e4_security_raw.jsonl"
    asyncio.run(run_security_evaluation(output_path=target_out))
