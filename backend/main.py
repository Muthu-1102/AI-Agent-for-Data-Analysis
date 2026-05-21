import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Modular imports based on the project structure
from api.routes import router as api_router
from config import settings
from utils.logger import setup_logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Replaces the deprecated @app.on_event("startup") and ("shutdown").
    """
    # Startup actions
    setup_logging()
    logger.info("Starting up AI Data Analysis API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # Add any other resource initialization here (e.g. DB pools, ML models)
    
    yield
    
    # Shutdown actions
    logger.info("Shutting down AI Data Analysis API...")
    # Add any resource cleanup here


def create_app() -> FastAPI:
    """
    Application factory pattern to initialize the FastAPI app.
    This structure is excellent for testing and production environments.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Backend API for the Multi-Agent AI Data Analysis System",
        lifespan=lifespan,
    )

    # Setup CORS Middleware
    # IMPORTANT: In production, configure settings.CORS_ORIGINS properly
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include main API router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # Health check endpoint
    @app.get("/health", tags=["System"])
    async def health_check():
        return {
            "status": "up",
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT
        }

    return app

# The main application instance to be run by Uvicorn (or other ASGI servers)
app = create_app()
