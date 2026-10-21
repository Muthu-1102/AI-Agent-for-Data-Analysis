from typing import List
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """
    Application configuration managed by Pydantic.
    Values are automatically loaded from environment variables or '.env' file.
    """
    
    # === App Settings ===
    PROJECT_NAME: str = "AI Data Analysis API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", description="development, staging, or production")
    API_V1_STR: str = "/api/v1"
    
    # In production, this should be a list of allowed origins
    CORS_ORIGINS: List[str] = Field(default=["*"])

    # === API Keys & Secrets ===
    # Forcing GROQ_API_KEY to be required at startup. If it's missing, the app will fail-fast securely.
    GROQ_API_KEY: str = Field(..., description="Groq API Key for LLM access")
    GROQ_MODEL: str = Field(default="openai/gpt-oss-20b", description="Default Groq model for all LLM calls (e.g. openai/gpt-oss-20b or qwen/qwen3.8-27b)")
    
    # === Agent / System Defaults ===
    MAX_RETRIES: int = Field(default=3, description="Maximum number of retries for LLM calls")
    SANDBOX_TIMEOUT_SECONDS: int = Field(default=30, description="Timeout for sandboxed code execution")

    # Use Pydantic V2 config syntax
    model_config = SettingsConfigDict(
        # The path corresponds to where you usually run the FastAPI app (e.g. root dir)
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore" # Ignore additional arbitrary env variables to avoid clutter or data-leak vulnerabilities
    )

# Instantiate as a singleton configuration object
# This will validate the variables (e.g., asserting that GROQ_API_KEY exists) at import time!
settings = Settings()
