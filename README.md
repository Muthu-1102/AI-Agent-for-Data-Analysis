# AI Data Analysis Agent

A multi-agent AI system for automated data analysis using natural language queries.

## Features

- **Multi-Agent Pipeline**: Schema analysis, prompt engineering, code generation, validation, execution, and reporting
- **FastAPI Backend**: RESTful API for data analysis operations
- **Streamlit Frontend**: User-friendly web interface for uploading datasets and querying
- **Secure Code Execution**: Sandboxed Python execution environment
- **LLM Integration**: Powered by Groq API

## Setup

### Prerequisites

- Python 3.11+ (Required by pandas>=3.0 and numpy>=2.0)
- Groq API key

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
3. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - Linux/Mac: `source .venv/bin/activate`
4. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

### Configuration

1. Copy `.env` file and update the Groq API key:
   ```
   GROQ_API_KEY=your_api_key_here
   ```

## Running the Application

### Backend

From the project root:
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

From the project root:
```bash
cd frontend
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

### Access

- Backend API: http://localhost:8000
- Frontend: http://localhost:8501
- API Documentation: http://localhost:8000/docs

## Usage

1. Open the Streamlit frontend
2. Upload a CSV dataset
3. Ask questions in natural language (e.g., "What is the average sales by region?")
4. The AI pipeline will analyze the data and provide insights

## API Endpoints

- `GET /health` - Root health check
- `POST /api/v1/upload` - Upload CSV file (enforces 50MB limit & path sanitization)
- `POST /api/v1/query` - Process natural language query through multi-agent pipeline

*Note: Core data analysis endpoints are mounted under the `/api/v1` route prefix.*

## Code Execution & Security

- **AST Security Visitor**: Generated code is parsed into an abstract syntax tree and inspected before execution. Blocks dunder introspection (`__class__`, `__subclasses__`), unauthorized imports, dangerous builtins, and disk write primitives (`to_csv`, `to_pickle`).
- **Subprocess Isolation**: Code executes in a separate Python subprocess with a hard wall-clock timeout (`SANDBOX_TIMEOUT_SECONDS=30`) to protect the backend from infinite loops or CPU exhaustion.
- **Production Boundary**: For public multi-tenant environments, execution should be further isolated inside containerized or microVM sandboxes (e.g., Docker/gVisor).

## Project Structure

```
├── backend/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── api/
│   │   ├── routes.py        # API endpoints
│   │   └── schemas.py       # Pydantic models
│   ├── core/
│   │   └── orchestrator.py  # Multi-agent orchestrator with self-repair
│   ├── agents/              # AI agents (Schema, Prompt, Code, Validation, Execution, Report)
│   ├── services/            # External services (LLM, file handling)
│   └── utils/               # Utilities (Sandbox, AST visitor, Logger)
├── frontend/
│   ├── app.py               # Streamlit application
│   ├── api_client.py        # Backend API client
│   └── components.py        # UI components
├── evaluation/              # Empirical evaluation framework & benchmark suite
├── data/                    # Sample datasets
└── logs/                    # Application logs
```

## Development & Testing

Run backend tests from the `backend/` directory:
```bash
cd backend
python -m pytest tests/
```

Run evaluation test suites:
```bash
python -m pytest evaluation/harness/test_matcher.py
```

## License

MIT License