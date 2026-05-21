import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File

from api.schemas import QueryRequest, QueryResponse, UploadResponse
from dependencies import get_file_service, get_logger
from services.file_service import FileService

from core.orchestrator import Orchestrator

router = APIRouter()

def get_orchestrator() -> Orchestrator:
    """Dependency injecting the Orchestrator."""
    return Orchestrator()

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_service: FileService = Depends(get_file_service),
    logger: logging.Logger = Depends(get_logger)
):
    """
    Endpoint to upload a CSV file data source.
    Stores the data natively and makes it accessible for future queries.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Only CSV files are explicitly allowed at this time."
        )
    
    try:
        file_id = await file_service.save_upload_file(file)
        
        logger.info(f"File uploaded smoothly: {file.filename} -> {file_id}")
        return UploadResponse(status="success", file_id=file_id, message=f"File '{file.filename}' uploaded successfully.")
        
    except Exception as e:
        logger.error(f"Error handling file upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="We encountered an unexpected failure trying to upload the file."
        )


@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    logger: logging.Logger = Depends(get_logger)
):
    """
    Takes a user's natural language request and orchestrates 
    the Multi-Agent pipeline (Schema -> Prompt -> Code -> Validation -> Execution -> Report)
    """
    try:
        logger.info(f"Processing analytic query across dataset [{request.file_id}]: {request.query}")
        
        pipeline_output = await orchestrator.execute_pipeline(request.query, request.file_id)
        
        return QueryResponse(
            status=pipeline_output.get("status", "error"),
            insights_summary=pipeline_output.get("insights_summary"),
            generated_code=pipeline_output.get("generated_code"),
            captured_output=pipeline_output.get("captured_output"),
            chart_image_base64=pipeline_output.get("chart_image_base64"),
            error=pipeline_output.get("error")
        )
    
    except ValueError as e:
        logger.warning(f"Validation error during query orchestration: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        
    except Exception as e:
        logger.error(f"Critical multi-agent orchestration error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An irrecoverable internal error occurred while processing your query."
        )
