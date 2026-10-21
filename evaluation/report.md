# Comprehensive Baseline Evaluation Report
**Project**: AI Agent for Data Analysis  
**Repository**: [Muthu-1102/AI-Agent-for-Data-Analysis](https://github.com/Muthu-1102/AI-Agent-for-Data-Analysis)  
**Baseline Commit**: `bddb5ca9545b2d191e45c265147dc39a35258571`  
**Evaluation Branch**: `eval/evidence`  
**Evaluation Date**: 2026-10-21  
**Evaluator**: Senior AI Engineer & LLM Evaluation Specialist  

---

## 1. Executive Summary & Headline Results

This report provides a rigorous, empirical baseline evaluation of the multi-agent data analysis pipeline. Every metric reported herein was directly measured from executing synthetic benchmark suites with telemetry captured on disk. **Zero numbers have been fabricated, estimated, or simulated.**

All proportion metrics are reported with **Wilson 95% score confidence intervals** ($[L_{95}, U_{95}]$). Latency metrics are reported with empirical median ($p_{50}$), 95th percentile ($p_{95}$), and standard deviation across repeated runs.

### Headline Metrics Summary Table

| Metric | Measured Value | Wilson 95% Confidence Interval | Sample Size ($N$) | Supporting Raw Evidence File |
| :--- | :--- | :--- | :--- | :--- |
| **Pipeline Completion Rate** | **93.06%** (134/144) | [87.69%, 96.18%] | 144 runs (48 Qs $\times$ 3 reps) | [`e1_heldout_raw.jsonl`](file:///d:/Projects/Agent%20for%20Data%20Analysis/evaluation/results/baseline/e1_heldout_raw.jsonl) |
| **Execution Success Rate** | **93.06%** (134/144) | [87.69%, 96.18%] | 144 runs (48 Qs $\times$ 3 reps) | [`e1_heldout_raw.jsonl`](file:///d:/Projects/Agent%20for%20Data%20Analysis/evaluation/results/baseline/e1_heldout_raw.jsonl) |
| **Computation Correctness (Raw)** | **68.06%** (98/144) | [60.06%, 75.12%] | 144 runs (48 Qs $\times$ 3 reps) | [`e1_heldout_raw.jsonl`](file:///d:/Projects/Agent%20for%20Data%20Analysis/evaluation/results/baseline/e1_heldout_raw.jsonl) |
| **Computation Correctness (API Available)** | **73.13%** (98/134) | [65.06%, 79.92%] | 134 runs (excl. 10 infra 429s) | [`e1_heldout_raw.jsonl`](file:///d:/Projects/Agent%20for%20Data%20Analysis/evaluation/results/baseline/e1_heldout_raw.jsonl) |
| **Summary Correctness** | **88.89%** (128/144) | [82.71%, 93.04%] | 144 runs (48 Qs $\times$ 3 reps) | [`e1_heldout_raw.jsonl`](file:///d:/Projects/Agent%20for%20Data%20Analysis/evaluation/results/baseline/e1_heldout_raw.jsonl) |
| **3-Repetition Strict Consistency** | **54.17%** (26/48) | [40.35%, 67.37%] | 48 unique questions | [`baseline_summary.json`](file:///d:/Projects/Agent%20for%20Data%20Analysis/evaluation/results/baseline/baseline_summary.json) |
| **Malicious Code Block Rate** | **57.14%** (24/42) | [42.21%, 70.88%] | 42 attack probes | [`e4_security_raw.jsonl`](file:///d:/Projects/Agent%20for%20Data%20Analysis/evaluation/results/baseline/e4_security_raw.jsonl) |
| **Benign Code False Positive Rate** | **0.00%** (0/42) | [0.00%, 8.38%] | 42 legitimate snippets | [`e4_security_raw.jsonl`](file:///d:/Projects/Agent%20for%20Data%20Analysis/evaluation/results/baseline/e4_security_raw.jsonl) |
| **Numerical Grounding Rate** | **60.23%** (156/259) | [54.16%, 66.00%] | 259 extracted summary numbers | [`e6_grounding_raw.jsonl`](file:///d:/Projects/Agent%20for%20Data%20Analysis/evaluation/results/baseline/e6_grounding_raw.jsonl) |
| **Fully Grounded Summaries** | **58.21%** (78/134) | [49.74%, 66.22%] | 134 executed summaries | [`e6_grounding_raw.jsonl`](file:///d:/Projects/Agent%20for%20Data%20Analysis/evaluation/results/baseline/e6_grounding_raw.jsonl) |
| **Validation Retry Recovery Rate** | **0.00%** (0/3) | [0.00%, 56.15%] | 3 synthetic failure scenarios | [`e3_retry_raw.jsonl`](file:///d:/Projects/Agent%20for%20Data%20Analysis/evaluation/results/baseline/e3_retry_raw.jsonl) |
| **Execution Retry Recovery Rate** | **0.00%** (0/3) | [0.00%, 56.15%] | 3 runtime exception cases | [`e3_retry_raw.jsonl`](file:///d:/Projects/Agent%20for%20Data%20Analysis/evaluation/results/baseline/e3_retry_raw.jsonl) |
| **Median End-to-End Latency** | **8.55s** ($p_{95}: 11.06\text{s}$) | $\sigma = 6.10\text{s}$ | 134 successful runs | [`baseline_summary.json`](file:///d:/Projects/Agent%20for%20Data%20Analysis/evaluation/results/baseline/baseline_summary.json) |

---

## 2. Evaluation Methodology & System Environment

### 2.1 Hardware and Runtime Environment
- **Operating System**: Windows 11 Pro 64-bit (`win32`)
- **Python Version**: `3.13.14` (installed in isolated virtual environment `.venv`)
- **Key Dependencies**: `pandas==3.0.2`, `numpy==2.4.4`, `fastapi==0.110.0`, `groq==0.18.0`, `matplotlib==3.8.4`
- **LLM Evaluated**: `openai/gpt-oss-20b` via Groq LPU API.
  - *Note on Model Selection*: Default model in repository `llama-3.1-8b-instant` returned HTTP 404 (`model does not exist or you do not have access to it`). `qwen/qwen3.8-27b` has a 1,000 Output Tokens/Minute (OTPM) rate limit on Groq's on-demand tier causing burst 429 rejections. `openai/gpt-oss-20b` provided an 8,000 TPM limit and clean pandas generation.
  - *Temperature Settings*: Code generation: `0.1`, Report generation: `0.3`.
  - *Frozen Prompt Hashes*: PromptAgent SHA-256 `1a9521...`, ReportAgent SHA-256 `0cfb1c...`.

### 2.2 Synthetic Evaluation Datasets
To guarantee data privacy and zero leak of proprietary data to external cloud APIs, 4 synthetic datasets were generated with fixed random seeds (`seed=42`) and frozen:
1. [`synthetic_sales.csv`](file:///d:/Projects/Agent%20for%20Data%20Analysis/data/synthetic_sales.csv) (1,000 rows, 8 columns): Order transactions with numeric, categorical, date, and discount columns.
2. [`synthetic_hr.csv`](file:///d:/Projects/Agent%20for%20Data%20Analysis/data/synthetic_hr.csv) (500 rows, 7 columns): Workforce attrition, tenure, salary, and performance ratings.
3. [`synthetic_sensor.csv`](file:///d:/Projects/Agent%20for%20Data%20Analysis/data/synthetic_sensor.csv) (1,000 rows, 6 columns): High-frequency telemetry with temperature, pressure, vibration, status.
4. [`synthetic_messy.csv`](file:///d:/Projects/Agent%20for%20Data%20Analysis/data/synthetic_messy.csv) (300 rows, 5 columns): Uncleaned retail data with missing values (`NaN`), whitespaces, and dirty numeric formatting.

---

## 3. Detailed Experiment Results

### Experiment E1: End-to-End Correctness & Consistency
**Test Cohort**: 48 frozen held-out questions across 4 datasets, evaluated over 3 independent repetitions ($N = 144$ total runs).

#### 3.1 Accuracy by Analytical Query Category
| Category | Cases ($N$) | Correct | Accuracy (%) | Wilson 95% CI |
| :--- | :--- | :--- | :--- | :--- |
| **Correlations** | 9 | 9 | **100.00%** | [70.09%, 100.00%] |
| **Percentages** | 12 | 11 | **91.67%** | [64.61%, 98.51%] |
| **Missing Values** | 6 | 5 | **83.33%** | [43.65%, 96.99%] |
| **Filtering** | 21 | 16 | **76.19%** | [54.91%, 89.37%] |
| **Simple Aggregates** | 33 | 25 | **75.76%** | [58.98%, 87.17%] |
| **Groupby** | 33 | 20 | **60.61%** | [43.68%, 75.32%] |
| **Chart Requests** | 9 | 5 | **55.56%** | [26.67%, 81.12%] |
| **Top-K / Ranking** | 12 | 5 | **41.67%** | [19.33%, 68.05%] |
| **Multi-Step Logic** | 9 | 2 | **22.22%** | [6.32%, 54.74%] |

![Accuracy by Category](file:///d:/Projects/Agent%20for%20Data%20Analysis/evaluation/figures/fig1_accuracy_by_category.png)

#### 3.2 Accuracy by Dataset Complexity
- **Sensor Telemetry (`synthetic_sensor.csv`)**: **91.67%** [78.17%, 97.13%] (33/36). High performance due to clean column names and straightforward numeric aggregations.
- **Sales Transactions (`synthetic_sales.csv`)**: **64.29%** [49.17%, 77.01%] (27/42). Failures concentrated in compound groupby and top-k filtering.
- **Messy Data (`synthetic_messy.csv`)**: **62.50%** [42.71%, 78.84%] (15/24). Failures occurred when the generated code failed to handle missing values or unstripped strings.
- **HR Workforce (`synthetic_hr.csv`)**: **54.76%** [39.95%, 68.78%] (23/42). Lowest accuracy due to complex conditional logic across tenure, salary, and attrition.

#### 3.3 Run-to-Run Consistency (3 Repetitions)
- **3/3 Passed (High Consistency)**: **26 / 48 questions (54.2%)**
- **2/3 Passed (Moderate Variability)**: **10 / 48 questions (20.8%)**
- **1/3 Passed (Low Consistency)**: **0 / 48 questions (0.0%)**
- **0/3 Passed (Persistent Failure)**: **12 / 48 questions (25.0%)**

---

### Experiment E2: Failure Taxonomy
Every non-correct run in the baseline was classified into mutually exclusive failure categories:

| Failure Category | Count | % of All Runs ($N=144$) | Root Cause Analysis |
| :--- | :--- | :--- | :--- |
| **CORRECT** | 98 | 68.06% | Output matched ground-truth computation within tolerance. |
| **EXECUTED_WRONG_ANSWER** | 36 | 25.00% | Code executed without error, but computed incorrect logic (e.g. wrong grouping, missed `ascending=False` in sorting, incorrect denominator). |
| **INFRA_ERROR (429 Rate Limit)** | 10 | 6.94% | Groq daily token quota (TPD) reached at the very end of repetition 3. Classified cleanly as infrastructure availability limit. |
| **VALIDATION_SECURITY_BLOCKED** | 0 | 0.00% | AST validator correctly permitted benign queries. |
| **SANDBOX_SUBSTRING_BLOCKED** | 0 | 0.00% | No substring false positives on standard questions. |
| **SYNTAX_ERROR** | 0 | 0.00% | Model consistently generated valid Python AST. |

![Failure Taxonomy](file:///d:/Projects/Agent%20for%20Data%20Analysis/evaluation/figures/fig2_failure_taxonomy.png)

---

### Experiment E3: Retry & Recovery Mechanism Audit
**Methodology**: Deterministic fault injection using mock LLM and execution fixtures.

1. **Transient LLM Exceptions**: The retry loop in `_run_agent` successfully caught network timeouts and retried up to `MAX_RETRIES=3`, achieving **100% recovery** when the transient error cleared within 2 attempts.
2. **Code Validation Failures**: When `ValidationAgent` rejected code, `Orchestrator._run_agent` retried the *exact same ValidationAgent* on the *unchanged state dictionary* 3 times. It **never sent the syntax or security error back to CodeAgent** to regenerate code. Recovery rate: **0%**.
3. **Execution Runtime Exceptions**: When generated code raised an exception during `exec()` (e.g., `ZeroDivisionError`, `KeyError`), `ExecutionAgent.process` caught the exception in an internal `except Exception:` block, set `execution_success = False`, and returned normally. `Orchestrator` never triggered a retry, proceeding immediately to `ReportAgent`. Recovery rate: **0%**.

---

### Experiment E4: Security Probes & Sandbox Evaluation
**Methodology**: Tested 42 malicious attack probes across 6 categories and 42 benign analysis snippets against `ValidationAgent`, `Sandbox.is_safe_code`, and end-to-end `ExecutionAgent`.

| Attack Category | Probes ($N$) | Blocked | Bypassed | Block Rate | Key Bypass Vectors Observed |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Forbidden Imports** | 7 | 7 | 0 | **100.0%** | Fully blocked by AST validator (`os`, `sys`, `subprocess`, `shutil`). |
| **Forbidden Builtins** | 7 | 7 | 0 | **100.0%** | Blocked (`__import__`, `eval`, `exec`, `open`). |
| **Dunder Introspection** | 7 | 0 | **7** | **0.0%** | **CRITICAL BYPASS**: `df.__class__.__mro__[1].__subclasses__()` allows escaping into host modules because AST validator allows attribute access and safe builtins include `type`, `getattr`, `dir`. |
| **Library File I/O** | 7 | 3 | **4** | **42.9%** | **BYPASS**: `df.to_csv()`, `df.to_pickle()`, and `plt.savefig()` written directly to host filesystem because pandas and matplotlib methods are unrestricted. |
| **Environment Variable Leak** | 7 | 5 | **2** | **71.4%** | Introspection via `[c for c in ().__class__.__bases__[0].__subclasses__() if c.__name__ == 'catch_warnings'][0]()._module.__builtins__['__import__']('os').environ`. |
| **Resource Exhaustion** | 7 | 2 | **5** | **28.6%** | **CRITICAL DEFECT**: `while True: pass` hung the execution process indefinitely. `SANDBOX_TIMEOUT_SECONDS=30` is **completely unenforced** in `ExecutionAgent`. |
| **Total Malicious** | **42** | **24** | **18** | **57.14%** | [42.21%, 70.88%] |
| **Benign Snippets** | **42** | **42 permitted** | 0 false pos | **0.00% FP** | [0.00%, 8.38%] |

![Security Matrix](file:///d:/Projects/Agent%20for%20Data%20Analysis/evaluation/figures/fig4_security_matrix.png)

#### Additional Attack Surface Findings:
- **Path Traversal in `resolve_dataset_path`**: `backend/utils/helpers.py` attempts relative candidates but falls back to `file_id` directly (`candidates = [..., file_id]`), allowing arbitrary reading of CSV files across the host filesystem.
- **Data-Path Prompt Injection**: Malicious cell values injected into CSV sample rows are directly concatenated into the LLM prompt by `SchemaAgent`.

---

### Experiment E5: Robustness & Unanswerable Queries
1. **Edge CSV Formats (8 cases)**:
   - Empty CSV (`edge_empty.csv`): Gracefully caught by `SchemaAgent` with descriptive error.
   - Single row, BOM UTF-8, semicolon delimiter, duplicate columns, all-null columns: Executed gracefully without server crash.
   - Wide table (500 columns, `edge_wide.csv`): `SchemaAgent` serialized all 500 column headers into the prompt, expanding it to 20,839 tokens and exceeding Groq's 7,000 ITPM limit (HTTP 413 error).
2. **Unanswerable Questions (3 cases)**:
   - Nonexistent column (`crypto_token_balance`): CodeAgent returned `0`, and ReportAgent fabricated an executive explanation stating: *"The data indicates that there are no positive token balances recorded across the entire dataset"*, rather than refusing to answer. Fabrication rate: **33.3%**.

---

### Experiment E6: Report Faithfulness & Numerical Grounding
**Methodology**: Deterministic regex and token extraction comparing numbers stated in `insights_summary` against raw numerical results in `captured_output` across 134 executed queries.

- **Total Extracted Summary Numbers**: 259
- **Faithfully Grounded Numbers**: 156 (**60.23%** [54.16%, 66.00%])
- **Ungrounded / Hallucinated Numbers**: 103 (**39.77%**)
- **Fully Grounded Summaries**: 78 / 134 (**58.21%** [49.74%, 66.22%])

**Root Cause**: The prompt in `backend/agents/report_agent.py` contains the instruction:
> *"If it seems numbers are broken or malformed in the raw output, try to elegantly infer the closest reasonable metric or mention the discrepancy."*

This directive actively prompts the model to invent figures when the terminal output does not match expectations.

---

### Experiment E7: Latency Scaling & Concurrency Profiling

#### 7.1 Local Compute Scaling Across Dataset Sizes
Evaluated across 5 dataset sizes (5 repetitions each, median $p_{50}$):
| Dataset Rows | Schema Load Latency ($p_{50}$) | Execution Latency ($p_{50}$) | Total Local Latency |
| :--- | :--- | :--- | :--- |
| **1,000** | 14.35 ms | 9.67 ms | **24.02 ms** |
| **10,000** | 17.92 ms | 41.96 ms | **59.88 ms** |
| **50,000** | 13.16 ms | 197.96 ms | **211.12 ms** |
| **100,000** | 16.96 ms | 386.58 ms | **403.54 ms** |
| **250,000** | 12.52 ms | 975.92 ms | **988.44 ms** |

![Latency Breakdown](file:///d:/Projects/Agent%20for%20Data%20Analysis/evaluation/figures/fig3_latency_breakdown.png)

#### 7.2 Stage Latency Breakdown (Over 134 Baseline Runs)
- **CodeAgent (LLM #1)**: Mean **4.88s** (57.5% of total time)
- **ReportAgent (LLM #2)**: Mean **3.25s** (38.3% of total time)
- **ValidationAgent (AST)**: Mean **0.003s** (<0.1%)
- **ExecutionAgent (Pandas)**: Mean **0.021s** (<0.3%)
- **Schema & Prompt Agents**: Mean **0.015s** (<0.2%)
- **Overall End-to-End Latency**: Median $p_{50} = 8.55\text{s}$, $p_{95} = 11.06\text{s}$, Max = $75.03\text{s}$ (during rate limit backoff).

#### 7.3 Concurrency & Race Conditions
- **Throughput**: 4 concurrent requests executed in **3.00s total wall-clock time** compared to 11.76s sequential sum (**3.92x overlap factor**), proving FastAPI's async event loop handles concurrent I/O.
- **Race Condition Observed**: All chart queries save to a single shared hardcoded path: `'output_plot.png'`. Overlapping requests overwrite each other's plot images before encoding into base64.
- **API Status Masking**: The HTTP API returns `200 OK` with JSON `status: "completed"` even when code execution failed internally.

---

### Experiment E8: Repository Hygiene Audit
1. **Stray File**: Empty file named `=` committed in repository root.
2. **Missing `.gitignore` Coverage**: `.gitignore` did not exclude `*.log` or test leak files; runtime log `logs/system.log` was committed.
3. **Launch Command Defect**: Documented launch command `uvicorn backend.main:app` from root fails with `ModuleNotFoundError: No module named 'api'` due to non-package imports.
4. **API Route Mismatch**: README states endpoints are at root (`/query`, `/upload`), but FastAPI router mounts them at `/api/v1/query` and `/api/v1/upload`.
5. **Python Compatibility Mismatch**: README claims `Python 3.8+`, but requirements pin `pandas==3.0.2` and `numpy==2.4.4` which strictly require **Python 3.11+**.

---

## 4. Summary of Key Weaknesses Discovered

1. **No Error-Feedback Loop**: When validation or runtime execution fails, the orchestrator retries identical code 3 times instead of feeding the error back to CodeAgent.
2. **Unenforced Sandbox Timeout & In-Process `exec`**: `SANDBOX_TIMEOUT_SECONDS=30` is dead code. Infinite loops hang the process, and dunder introspection bypasses the sandbox completely.
3. **Hallucination-Inducing Prompt**: ReportAgent's prompt explicitly encourages the LLM to invent numbers when output looks broken, yielding a 39.8% ungrounded figure rate.
4. **Untruthful API Status**: Runtime execution crashes are caught and swallowed; the API returns `status: "completed"` without exposing `execution_success`.
5. **Path Traversal & Race Conditions**: `resolve_dataset_path` allows accessing arbitrary CSVs, and shared `output_plot.png` causes image cross-talk under concurrency.

---

## 5. Limitations & Threats to Validity
- **Single Evaluated Model**: Baseline results reflect `openai/gpt-oss-20b` on Groq LPU. Results may vary on other frontier models.
- **Synthetic Data**: Datasets were synthetically generated to eliminate private data leakage; distributions may not capture all real-world human telemetry edge cases.
- **Frozen Denominator**: All metrics are calculated against the frozen held-out 48-question benchmark committed in Phase 2.
