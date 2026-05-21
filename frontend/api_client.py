import os
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1")

class DataAnalystAPI:
    """
    Python client for interacting with the Data Analyst FastAPI Backend.
    """
    
    @staticmethod
    def upload_dataset(file_obj, filename: str) -> str:
        """Uploads a CSV file and returns the dataset_id."""
        url = f"{BACKEND_URL}/upload"
        try:
            file_obj.seek(0)
            files = {"file": (filename, file_obj, "text/csv")}
            
            logger.info("Uploading dataset to backend via %s", url)
            response = requests.post(url, files=files, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data["file_id"]
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to upload dataset: {e}")
            raise RuntimeError(f"Could not connect to the backend: {e}")

    @staticmethod
    def process_query(query: str, file_id: str) -> dict:
        """Dispatches a natural language query to the AI pipeline."""
        url = f"{BACKEND_URL}/query"
        payload = {"query": query, "file_id": file_id}
        try:
            logger.info(f"Dispatching query for {file_id}: '{query}'")
            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Query dispatch failed: {e}")
            raise RuntimeError(f"The multi-agent pipeline failed or timed out: {e}")
