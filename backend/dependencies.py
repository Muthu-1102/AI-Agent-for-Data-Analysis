from functools import lru_cache
import logging

from fastapi import Depends

# Assuming modular imports structure
from config import Settings, settings
from services.llm_service import LLMService
from services.file_service import FileService

@lru_cache()
def get_settings() -> Settings:
    """
    Dependency to get the application settings.
    Using lru_cache ensures the settings are loaded and validated only once,
    drastically improving performance for dependency injection on every request.
    """
    return settings

def get_logger() -> logging.Logger:
    """
    Dependency to get the default API logger instance.
    """
    return logging.getLogger("api")

# --- Service Dependencies ---
# Utilizing FastAPI's Depends to inject other dependencies automatically

def get_llm_service(app_settings: Settings = Depends(get_settings)) -> LLMService:
    """
    Dependency injection for the shared LLM Service.
    It passes the required API key and default model directly from the configured settings.
    """
    return LLMService(
        api_key=app_settings.GROQ_API_KEY,
        default_model=app_settings.GROQ_MODEL
    )

def get_file_service() -> FileService:
    """
    Dependency injection for the file processing service.
    Useful for isolated tracking or file system operations (like saving CSVs).
    """
    return FileService()
