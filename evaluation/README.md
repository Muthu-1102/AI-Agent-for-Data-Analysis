# Evaluation Framework: AI Agent for Data Analysis

This directory contains the independent evaluation framework, test datasets, harness code, security probes, and raw empirical results for evaluating the Multi-Agent Data Analysis system.

---

## 1. Methodology Overview

The evaluation treats the application as a black/grey-box system under test (SUT) across 8 structured experiments:
- **E1: End-to-End Answer Correctness vs Ground Truth**: 60 deterministic analytical questions across 4 synthetic domains, split into 20% DEV (12 questions) and 80% HELD-OUT (48 questions). The held-out set is executed across 3 independent repetitions ($N = 144$ runs) to assess model non-determinism, computation correctness, and summary fidelity.
- **E2: Failure Taxonomy**: Rigorous 9-category classification of every failed run from E1 raw JSONL telemetry.
- **E3: Retry & Recovery Behavior**: Controlled fault-injection testing of the orchestrator retry loop under transient LLM failures, validation rejections, and execution exceptions.
- **E4: Security of Code Validation & Execution**: 42 malicious security probes vs 42 benign analytical snippets evaluated against `ValidationAgent`, `Sandbox.is_safe_code`, and end-to-end `ExecutionAgent`, plus data-path path traversal tests.
- **E5: Robustness & Unanswerable Questions**: System behavior when faced with malformed CSVs, missing columns, impossible aggregation requests, and prompt injection attempts.
- **E6: Report Faithfulness & Grounding**: Numerical claim extraction from report summaries matched against console execution outputs to quantify hallucination and distortion rates.
- **E7: Latency & Concurrency**: Micro-benchmarks of per-stage execution times across dataset scales (1k, 10k, 50k, 100k rows) and concurrent HTTP stress testing (1, 2, 4 parallel workers) checking for event-loop blocking and file-collision bugs (`output_plot.png`).
- **E8: Repository Hygiene & Operational Audits**: Automated checks for stray files, gitignore coverage, exposed runtime artifacts, and configuration drift.

---

## 2. Directory Structure

```text
evaluation/
├── README.md                 # Methodology, environment, and reproduction commands
├── metrics.md                # Formal mathematical definitions of all metrics (committed before runs)
├── manifest.json             # Environment metadata, seeds, commit hashes, model info, timestamps
├── dataset/                  # Synthetic dataset generator, CSVs, and question catalogs
│   ├── generate_datasets.py  # Seeded synthetic CSV generator
│   ├── ground_truth.py       # Independent ground-truth calculation engine
│   ├── questions_dev.json    # 12 DEV questions with independent ground truth
│   ├── questions_heldout.json# 48 HELD-OUT questions with independent ground truth
│   └── security/             # Malicious (42) and benign (42) probe suites
├── harness/                  # Automated test harnesses and answer matchers
│   ├── test_matcher.py       # Unit tests for the answer matching engine
│   ├── run_e1_correctness.py # E1 runner (in-process + HTTP verification)
│   ├── run_e3_retry.py       # E3 fault injection runner
│   ├── run_e4_security.py    # E4 security probe runner
│   ├── run_e5_robustness.py  # E5 robustness runner
│   ├── run_e6_grounding.py   # E6 report grounding analyzer
│   ├── run_e7_latency.py     # E7 latency and concurrency benchmark
│   └── run_e8_hygiene.py     # E8 repository hygiene audit
├── results/
│   ├── baseline/             # Raw JSONL execution logs for baseline commit
│   └── after/                # Raw JSONL execution logs after Phase 6 improvements
├── logs/                     # Sanitized runtime execution logs (keys redacted)
├── figures/                  # Plots generated directly from raw result files
├── reports/                  # Detailed technical findings and Phase 1 audit
└── report.md                 # Comprehensive evaluation report
```

---

## 3. Environment & Reproduction Setup

### Requirements
- OS: Windows / Linux / macOS
- Python: 3.11+ (Evaluated on Python 3.13.14)
- Packages: dependencies from `backend/requirements.txt`

### Setup Instructions
```bash
# 1. Activate the virtual environment
.venv\Scripts\activate   # Windows
# or: source .venv/bin/activate  # Linux/Mac

# 2. Configure environment (set valid Groq key and active model)
# Ensure .env contains GROQ_API_KEY
set GROQ_MODEL=qwen/qwen3.8-27b   # On Windows
# or: export GROQ_MODEL=qwen/qwen3.8-27b  # Linux/Mac

# 3. Verify answer matcher unit tests
python -m pytest evaluation/harness/test_matcher.py

# 4. Generate synthetic datasets and freeze ground truth
python evaluation/dataset/generate_datasets.py
python evaluation/dataset/ground_truth.py

# 5. Execute experiments
python evaluation/harness/run_e1_correctness.py
python evaluation/harness/run_e3_retry.py
python evaluation/harness/run_e4_security.py
python evaluation/harness/run_e5_robustness.py
python evaluation/harness/run_e6_grounding.py
python evaluation/harness/run_e7_latency.py
python evaluation/harness/run_e8_hygiene.py
```
