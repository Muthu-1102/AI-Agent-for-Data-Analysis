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

- Python 3.8+
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
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or from project root:
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
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

- `GET /health` - Health check
- `POST /upload` - Upload CSV file
- `POST /query` - Process natural language query

## Project Structure

```
├── backend/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── api/
│   │   ├── routes.py        # API endpoints
│   │   └── schemas.py       # Pydantic models
│   ├── core/
│   │   └── orchestrator.py  # Multi-agent orchestrator
│   ├── agents/              # AI agents
│   ├── services/            # External services (LLM, file handling)
│   └── utils/               # Utilities
├── frontend/
│   ├── app.py               # Streamlit application
│   ├── api_client.py        # Backend API client
│   └── components.py        # UI components
├── data/                    # Sample datasets
└── logs/                    # Application logs
```

## Development

Run tests:
```bash
pytest backend/tests/
```

## License

MIT License