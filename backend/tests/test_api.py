import io
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from main import app
from api.routes import get_orchestrator


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "up"
    assert "version" in data


def test_upload_non_csv_rejected(client):
    file_content = b"some text content"
    response = client.post(
        "/api/v1/upload",
        files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
    )
    assert response.status_code == 400
    assert "Only CSV files are explicitly allowed" in response.json()["detail"]


def test_upload_valid_csv(client, mocker):
    mocker.patch(
        "services.file_service.FileService.save_upload_file",
        new_callable=AsyncMock,
        return_value="dataset_abc123.csv"
    )
    file_content = b"col1,col2\n1,2\n3,4"
    response = client.post(
        "/api/v1/upload",
        files={"file": ("data.csv", io.BytesIO(file_content), "text/csv")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["file_id"] == "dataset_abc123.csv"


def test_query_path_traversal_rejected(client):
    response = client.post(
        "/api/v1/query",
        json={"query": "Calculate mean", "file_id": "../../etc/passwd"}
    )
    assert response.status_code == 400
    assert "Path traversal characters are not permitted" in response.json()["detail"]


def test_query_path_traversal_backslash_rejected(client):
    response = client.post(
        "/api/v1/query",
        json={"query": "Calculate mean", "file_id": "..\\windows\\win.ini"}
    )
    assert response.status_code == 400
    assert "Path traversal characters are not permitted" in response.json()["detail"]


def test_query_success(client, mocker):
    mock_orch = AsyncMock()
    mock_orch.execute_pipeline.return_value = {
        "status": "completed",
        "execution_success": True,
        "insights_summary": "Mean is 42",
        "generated_code": "print(df.mean())",
        "captured_output": "42",
        "chart_image_base64": None,
        "error": None
    }
    app.dependency_overrides[get_orchestrator] = lambda: mock_orch

    try:
        response = client.post(
            "/api/v1/query",
            json={"query": "Calculate mean", "file_id": "dataset_123.csv"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["execution_success"] is True
        assert data["insights_summary"] == "Mean is 42"
    finally:
        app.dependency_overrides.clear()
