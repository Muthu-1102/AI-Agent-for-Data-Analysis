# Evaluation Metrics & Formal Definitions

This document contains the exact operational and mathematical definitions of all metrics used in the evaluation of the AI Agent for Data Analysis pipeline.
All definitions are frozen and committed prior to executing baseline experiments.

---

## 1. Primary Pipeline Metrics

### 1.1 Pipeline Completion Rate
- **Operational Definition**: Proportion of query runs where the orchestrator returns `status == "completed"` without raising an uncaught exception or returning `status == "error"` / `status == "fatal"`.
- **Mathematical Formula**:
  $$\text{Pipeline Completion Rate} = \frac{N_{\text{status} = \text{"completed"}}}{N_{\text{total\_runs}}}$$
- **Denominator**: Total attempted query runs in the test cohort ($N_{\text{total\_runs}}$).
- **Pass Criteria**: Pipeline returns a response dict with `"status": "completed"`.
- **Note**: As observed in Phase 1, `status == "completed"` can be returned even when code execution failed (since `ExecutionAgent` swallows exceptions and `ReportAgent` formats an error summary). Therefore, this is not a correctness metric.

### 1.2 Execution Success Rate
- **Operational Definition**: Proportion of runs where the generated Python code executed inside `ExecutionAgent` without throwing a runtime exception (`execution_success == True`).
- **Mathematical Formula**:
  $$\text{Execution Success Rate} = \frac{\sum_{i=1}^{N} \mathbb{I}(\text{execution\_success}_i = \text{True})}{N_{\text{total\_runs}}}$$
- **Denominator**: Total query runs ($N_{\text{total\_runs}}$).
- **Pass Criteria**: `execution_success == True` captured directly from pipeline internal state.

---

## 2. Correctness Metrics

### 2.1 Computation Correctness (Primary Correctness Metric)
- **Operational Definition**: The raw captured stdout (`captured_output`) produced by running the generated code against the dataset matches the deterministically computed ground-truth answer according to type-specific tolerance rules.
- **Matching Rules**:
  1. **Scalar Numeric**: Ground truth numeric value $y^*$ and extracted numeric candidate $y$.
     - Absolute tolerance: $|y - y^*| \le 10^{-3}$ OR
     - Relative tolerance: $\frac{|y - y^*|}{\max(|y^*|, 10^{-6})} \le 10^{-3}$ (0.1%).
     - Formats supported: integers, floats, currency (\$1,234.56), percentages (12.34% $\leftrightarrow$ 0.1234).
  2. **Categorical / String**: Case-insensitive, whitespace-trimmed, punctuation-normalized exact match.
  3. **Ordered List / Ranking (e.g. Top 3)**:
     - Exact sequence match of normalized string identifiers in the reported ranking.
  4. **Set / Multi-Entity**:
     - Set equality or intersection of expected entity tokens within the output.
  5. **Empty / No-Data**:
     - Correct identification of empty result or zero count.
- **Mathematical Formula**:
  $$\text{Computation Correctness} = \frac{\sum_{i=1}^{N} \mathbb{I}(\text{Match}(\text{captured\_output}_i, \text{ground\_truth}_i) = \text{True})}{N}$$
- **Reporting**:
  - **Raw Correctness**: Denominator = all attempted runs ($N_{\text{total}}$). Infrastructure/API failures count as incorrect.
  - **Availability-Conditional Correctness**: Denominator = runs that did not fail due to API infrastructure errors ($N_{\text{valid}} = N_{\text{total}} - N_{\text{infra}}$).
  - 95% Wilson Score Confidence Intervals reported for all proportions.

### 2.2 Summary Correctness (Secondary Metric)
- **Operational Definition**: The final human-readable markdown summary (`insights_summary`) produced by `ReportAgent` contains the ground-truth answer entity or value, extracted using the same deterministic matching rules.
- **Mathematical Formula**:
  $$\text{Summary Correctness} = \frac{\sum_{i=1}^{N} \mathbb{I}(\text{Match}(\text{insights\_summary}_i, \text{ground\_truth}_i) = \text{True})}{N}$$

### 2.3 Run-to-Run Consistency
- **Operational Definition**: For each question evaluated across $R=3$ independent repetitions, consistency is the degree to which all repetitions yield the identical correctness outcome.
- **Mathematical Formula**:
  - Per-question consistency score:
    $$C_q = \mathbb{I}(\text{result}_{q,1} = \text{result}_{q,2} = \text{result}_{q,3})$$
  - Overall Dataset Consistency:
    $$\bar{C} = \frac{1}{Q} \sum_{q=1}^{Q} C_q$$
  - Also reported: Mean accuracy across runs $\mu$ and standard deviation across repetitions $\sigma = \sqrt{\frac{1}{R-1}\sum_{r=1}^{R} (\text{acc}_r - \bar{\text{acc}})^2}$.

---

## 3. Failure Taxonomy Classification (E2)

Every non-correct run must be partitioned into exactly ONE mutually exclusive failure category:
1. **`INFRA_ERROR`**: Groq API 429 rate limit, 5xx server error, connection drop, model not found, or harness-level request timeout.
2. **`EXTRACTION_ERROR`**: LLM returned a response from which no executable Python block could be parsed or code extraction failed.
3. **`SYNTAX_ERROR`**: Python code failed `ast.parse()` inside `ValidationAgent`.
4. **`VALIDATION_SECURITY_BLOCKED`**: `ValidationAgent` detected disallowed module import or blacklisted builtin function (`eval`, `exec`, `open`, etc.).
5. **`SANDBOX_SUBSTRING_BLOCKED`**: `Sandbox.is_safe_code()` blocked code due to substring keyword match (e.g., column containing `"open"` or `"exec"`) or import whitelist mismatch.
6. **`EXECUTION_RUNTIME_ERROR`**: Python exception raised during `exec()` in `ExecutionAgent` (e.g. `KeyError`, `AttributeError`, `TypeError`, `ZeroDivisionError`).
7. **`EXECUTED_WRONG_ANSWER`**: Code executed cleanly without exceptions (`execution_success == True`), but captured output does not match ground truth.
8. **`CORRECT_CODE_WRONG_SUMMARY`**: Code execution output correctly matches ground truth, but the summary distorted, omitted, or hallucinated different numbers.
9. **`UNCLASSIFIED`**: Any residual failure not fitting categories 1–8.

---

## 4. Security & Isolation Metrics (E4)

### 4.1 Malicious Block Rate
- **Operational Definition**: Proportion of malicious security probes rejected by validation or sandbox layers before execution, or prevented from accessing the canary target during execution.
- **Formula**:
  $$\text{Block Rate} = \frac{N_{\text{blocked\_malicious}}}{N_{\text{total\_malicious}}}$$
- Evaluated separately per probe category (Forbidden Imports, Introspection / Dunder Access, File I/O via Libraries, Env Var Leakage, Resource Exhaustion).

### 4.2 Benign False Positive Rate
- **Operational Definition**: Proportion of legitimate, benign data analysis code snippets that are incorrectly rejected by validation layers.
- **Formula**:
  $$\text{False Positive Rate} = \frac{N_{\text{blocked\_benign}}}{N_{\text{total\_benign}}}$$
- Evaluated separately for `ValidationAgent` AST checks vs `Sandbox.is_safe_code` substring/whitelist checks.

### 4.3 Data-Path Vulnerability
- Tested deterministically:
  - Path traversal in `file_id`: Does `resolve_dataset_path("../canary.csv")` access files outside the `data/` directory? (Pass = Rejected / Blocked; Fail = File opened).
  - Malformed upload rejection rate: Empty files, non-CSV extensions, double extensions (`data.csv.exe`).

---

## 5. Robustness & Hallucination Metrics (E5)

### 5.1 Graceful Handling Rate (Edge CSVs & Unanswerable Queries)
- **Operational Definition**: For unanswerable queries (nonexistent columns, impossible logic) or malformed CSVs, the proportion of runs where the system clearly indicates an inability to answer or raises an explicit error, rather than fabricating a plausible answer.
- **Formula**:
  $$\text{Graceful Handling Rate} = \frac{N_{\text{graceful}}}{N_{\text{unanswerable}}}$$

### 5.2 Fabrication / Hallucination Rate
- **Operational Definition**: Proportion of unanswerable queries where the insights summary asserts specific numerical values that do not exist in the dataset or stdout.
- **Formula**:
  $$\text{Fabrication Rate} = \frac{N_{\text{fabricated}}}{N_{\text{unanswerable}}}$$

---

## 6. Report Faithfulness & Grounding (E6)

### 6.1 Numeric Grounding Rate
- **Operational Definition**: Proportion of numerical tokens in `insights_summary` that can be mapped directly to numbers present in `captured_output` (within $\pm 1\%$ rounding allowance).
- **Formula**:
  $$\text{Grounding Rate} = \frac{N_{\text{grounded\_numbers}}}{N_{\text{total\_summary\_numbers}}}$$

### 6.2 Ungrounded Summary Incidence
- **Operational Definition**: Percentage of summaries that contain at least one ungrounded numerical claim.

---

## 7. Latency & Concurrency Metrics (E7)

### 7.1 Stage & Total Latency
- Measured in seconds using high-resolution monotonic timer (`time.perf_counter()`).
- Reported percentiles: p50 (Median), p95, Max.
- Broken down into:
  - Local Compute Time: Schema inspection + Prompt generation + Validation + Sandbox execution.
  - LLM Time: Code generation call + Report generation call.
  - Total End-to-End Latency.
- 95% Bootstrap Confidence Intervals computed over 1,000 bootstrap iterations.

### 7.2 Concurrency Integrity
- Under concurrent loads of $C \in \{1, 2, 4\}$ parallel requests:
  - Collision Rate on `output_plot.png`.
  - Process blocking / event-loop stalls (measuring latency degradation vs linear scaling).
  - Stdout cross-contamination between parallel executions.

---

## 8. Statistical Standards & Confidence Intervals
- Proportions $p = k/n$: 95% Wilson Score Confidence Interval:
  $$w = \frac{p + \frac{z^2}{2n} \pm z \sqrt{\frac{p(1-p)}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}} \quad (z = 1.96)$$
- Percentiles: Non-parametric bootstrap (1,000 resamples with replacement).
- All numbers must cite sample size $n$, raw result file path, and exact SHA-256 dataset hash.
