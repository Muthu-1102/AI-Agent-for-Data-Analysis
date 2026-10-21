# Phase 1 Investigation Findings: AI Agent for Data Analysis

- **Baseline Commit**: `bddb5ca9545b2d191e45c265147dc39a35258571`
- **Branch**: `eval/evidence`
- **Execution Date**: 2026-10-21
- **Host Platform**: Windows 11 (win32), Shell: PowerShell
- **Active Python**: Python 3.13.14 (Virtualenv: `.venv/Scripts/python.exe`)

---

## 1. Environment & Python Version Constraints

### Finding
The repository's [README.md](../../README.md) states:
> Prerequisites: Python 3.8+

However, [backend/requirements.txt](../../backend/requirements.txt) pins:
```text
pandas==3.0.2
numpy==2.4.4
fastapi==0.136.1
```
- `numpy >= 2.0` dropped support for Python 3.8 and 3.9; it requires Python 3.10+.
- `pandas 3.0+` requires Python 3.11+.
- The repository Dockerfiles ([backend/Dockerfile](../../backend/Dockerfile) and [frontend/Dockerfile](../../frontend/Dockerfile)) specify:
  `FROM python:3.11-slim`
- **True Minimum Python Version**: Python 3.11+.
- Python version used in this evaluation: **Python 3.13.14**.

---

## 2. Module Imports & Launch Commands

### Documented Commands Tested
The README provides two conflicting launch instructions for the backend:
1. `cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000`
2. `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000` (from project root)

### Test Results
- **Command 1 (`cd backend && uvicorn main:app`)**: **WORKS**.
  - `backend/main.py` performs root-relative imports:
    `from api.routes import router as api_router`
    `from config import settings`
    `from utils.logger import setup_logging`
  - When the process CWD is `backend/`, Python includes `backend/` in `sys.path`.
- **Command 2 (`uvicorn backend.main:app` from root)**: **FAILS**.
  - Raw command: `python -c "import backend.main"` from repo root.
  - Raw output:
    ```text
    Traceback (most recent call last):
      File "<string>", line 1, in <module>
      File "D:\Projects\Agent for Data Analysis\backend\main.py", line 8, in <module>
        from api.routes import router as api_router
    ModuleNotFoundError: No module named 'api'
    ```

---

## 3. Existing Test Suite Execution

### Command Tested
Per README:
`pytest backend/tests/`

### Test Results
1. **Invocation from root**: `pytest backend/tests/`
   - **Result**: **0 passed, 0 failed, 2 collection errors**.
   - Raw output:
     ```text
     ERROR collecting backend/tests/test_agents.py
     ModuleNotFoundError: No module named 'agents'
     ERROR collecting backend/tests/test_pipeline.py
     ModuleNotFoundError: No module named 'core'
     ```
2. **Invocation with `backend/` in `sys.path`**: `python -m pytest tests/` inside `backend/`
   - **Result**: **7 passed, 6 failed (13 total)**.
   - Failure analysis:
     - `test_schema_agent_success`: `KeyError: 'columns'`. `SchemaAgent.process` returns `{"schema_info": schema.model_dump()}`, not `{"columns": ...}`.
     - `test_schema_agent_file_not_found`: `FileNotFoundError` escaping due to mismatch in mocked function path.
     - `test_prompt_agent_success`: `ValidationError` on `DataSchema`: missing required fields `null_counts` and `sample_rows`.
     - `test_code_agent_success`: `ValueError`: `CodeAgent requires 'structured_prompt' in the state context.` (test supplied obsolete key `prompt_plan`).
     - `test_orchestrator_success`: `KeyError: 'query'`. Orchestrator return dict exposes `status`, `insights_summary`, `generated_code`, `captured_output`, `error`, but test asserts `result['query']`.
     - `test_orchestrator_validation_failure`: `Failed: DID NOT RAISE <class 'PermissionError'>`. Orchestrator catches `RuntimeError` and returns `status: "error"`, never re-raising `PermissionError`.

---

## 4. API Endpoints & Route Prefixes

### Finding
The README states:
- `GET /health`
- `POST /upload`
- `POST /query`

### Test Results
- `GET /health` -> **200 OK** (`{"status":"up","version":"1.0.0","environment":"development"}`)
- `GET /api/v1/health` -> **404 Not Found**
- `POST /upload` -> **404 Not Found**
- `POST /api/v1/upload` -> **200 OK** (`{"status":"success","file_id":"dataset_1532c1ed.csv",...}`)
- `POST /query` -> **404 Not Found**
- `POST /api/v1/query` -> **200 OK**

**Discrepancy**: `POST /upload` and `POST /query` are mounted under router prefix `/api/v1` (`API_V1_STR` in `config.py`). The README omits `/api/v1` for upload and query. Frontend `api_client.py` correctly uses `BACKEND_URL="http://localhost:8000/api/v1"`.

---

## 5. Verification of Code Claims vs Implementation

### (a) "Retry" Mechanism
- **Claimed**: Multi-agent recovery / retries on failure.
- **Actual Implementation** ([backend/core/orchestrator.py:92-123](../../backend/core/orchestrator.py#L92-L123)):
  - The retry loop in `Orchestrator._run_agent` executes:
    ```python
    while attempts < max_retries:
        try:
            result = await agent.process(state)
            if isinstance(result, dict): state.update(result)
            return state
        except Exception as e:
            attempts += 1
    ```
  - It merely re-calls the *same* agent with the *identical* state dict.
  - If `ValidationAgent` rejects generated code (syntax error or blocked import), it simply re-runs `ValidationAgent` 3 times on the unchanged `state["generated_code"]`, then raises `RuntimeError`.
  - It **never** feeds the validation error back to `CodeAgent` to regenerate corrected code.
  - Furthermore, if `ExecutionAgent` throws an exception, `ExecutionAgent.process` catches it internally and does not raise, so `_run_agent` does not retry at all.

### (b) `SANDBOX_TIMEOUT_SECONDS`
- **Claimed**: Configuration setting `SANDBOX_TIMEOUT_SECONDS=30` in [backend/config.py](../../backend/config.py) and [example.env](../../example.env).
- **Actual Implementation**:
  - `SANDBOX_TIMEOUT_SECONDS` is defined in `Settings` but is **never referenced or imported anywhere else in the entire repository**.
  - Code execution in [backend/agents/execution_agent.py:80](../../backend/agents/execution_agent.py#L80) uses:
    ```python
    exec(generated_code, safe_globals, safe_locals)
    ```
  - There is zero timeout enforcement, zero signal handler, and zero subprocess limit. An infinite loop (`while True: pass`) hangs indefinitely.

### (c) "Sandboxed" Execution Isolation
- **Claimed**: "Secure Code Execution: Sandboxed Python execution environment".
- **Actual Implementation**:
  - Code execution is completely **in-process** via Python's standard `exec()`.
  - It is not containerized, not subprocess-isolated, and not memory-isolated.
  - `safe_globals` restricts `__builtins__`, but retains `type`, `getattr`, `hasattr`, `dir`, `id`.
  - Introspection or memory leaks affect the host server process directly.

### (d) Status Truthfulness (`status: "completed"`)
- **Actual Implementation**:
  - In [backend/agents/execution_agent.py:83-86](../../backend/agents/execution_agent.py#L83-L86), execution errors are caught:
    ```python
    except Exception as e:
        execution_success = False
        error_trace = traceback.format_exc()
    ```
  - `ExecutionAgent.process` returns normally with `{"execution_success": False, "error_trace": ...}`.
  - `ReportAgent` formats an error message into `insights_summary`.
  - `Orchestrator.execute_pipeline` returns `{"status": "completed", ...}`.
  - The API response does not expose `execution_success`, returning `status: "completed"` even when code execution failed completely.

### (e) Stray Empty File Named `=`
- An untracked/committed empty file `d:\Projects\Agent for Data Analysis\=` (0 bytes) is tracked in the repository root.
- Typically created accidentally in shell by typing a stray `=` or redirect.

### (f) Committed Runtime Artifacts in `logs/` and `data/`
- `.gitignore` contains `data` on line 13, but git tracking overrides `.gitignore`:
  - 41 CSV files are committed in `data/`, including 39 random upload artifacts (`dataset_05a70beb.csv`, etc.).
  - `logs/app.log` and `logs/system.log` are committed in git.
  - Running queries appends to `logs/system.log`, causing git working tree to immediately show `modified: logs/system.log`.

---

## 6. Docker & Container Readiness
- `docker --version`: `Docker version 29.5.2, build 79eb04c`
- `docker compose config`: Valid configuration.
- [backend/Dockerfile](../../backend/Dockerfile) and [frontend/Dockerfile](../../frontend/Dockerfile) both exist.

---

## 7. Groq Model Availability Discovery & Active Execution
- The codebase defaults to `GROQ_MODEL = "llama-3.1-8b-instant"`.
- When querying Groq API with the active key, the endpoint responded with:
  `Error code: 404 - The model llama-3.1-8b-instant does not exist or you do not have access to it.`
- Direct interrogation of the Groq API model catalog returned active chat models:
  - `qwen/qwen3.8-27b` (Verified responsive and successfully generated pandas code + report in live pipeline test)
  - `openai/gpt-oss-120b`
  - `openai/gpt-oss-20b`
- Setting `GROQ_MODEL=qwen/qwen3.8-27b` allowed the multi-agent pipeline to execute end-to-end successfully on `dataset_1532c1ed.csv`.

---

## 8. Windows Console Encoding Anomaly in `logger.py`
- In [backend/utils/logger.py:31](../../backend/utils/logger.py#L31), `console_handler = logging.StreamHandler(sys.stdout)` is configured without UTF-8 encoding.
- [backend/utils/logger.py:49](../../backend/utils/logger.py#L49) logs emoji strings: `=== 🧠 LLM INTERACTION START ===`.
- On Windows systems using default codepage `cp1252`, this triggers:
  `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f9e0'` inside the Python logging stream.

