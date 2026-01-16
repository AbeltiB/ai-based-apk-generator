"""
Health check endpoints for monitoring service status.
"""
from fastapi import APIRouter, status
from pydantic import BaseModel
from datetime import datetime, timezone

from app.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    service: str
    version: str
    timestamp: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "AI App Builder Service",
                "version": "0.1.0",
                "timestamp": "2025-12-16T12:00:00Z"
            }
        }


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Service health check",
    description="Returns the current health status of the AI service"
)
async def health_check():
    """
    Health check endpoint.
    
    Returns basic service information and health status.
    Used by monitoring systems and load balancers.
    """
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc)
    )


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Readiness check",
    description="Returns 200 if service is ready to accept requests"
)
async def readiness_check():
    """
    Readiness check endpoint.
    
    Used by Kubernetes and other orchestrators to determine
    if the service is ready to receive traffic.
    """
    return {"ready": True}


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Liveness check",
    description="Returns 200 if service is alive"
)
async def liveness_check():
    """
    Liveness check endpoint.
    
    Used by Kubernetes to determine if the service should be restarted.
    """
    return {"alive": True}