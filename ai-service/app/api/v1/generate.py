"""
Frontend API endpoint for AI generation requests.

POST /api/v1/generate - Submit prompt and receive task ID
"""
from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Request
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from app.models.schemas import AIRequest, PromptContext
from app.core.messaging import queue_manager
from app.utils.logging import get_logger, log_context
from app.utils.rate_limiter import rate_limiter

router = APIRouter()
logger = get_logger(__name__)


class GenerateRequest(BaseModel):
    """Frontend generation request"""
    prompt: str = Field(..., min_length=10, max_length=2000)
    user_id: str = Field(..., min_length=1, max_length=255)
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    
    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Ensure prompt is meaningful"""
        if not v.strip():
            raise ValueError("Prompt cannot be empty or whitespace")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Create a todo list app with add, delete, and complete features",
                "user_id": "user_123",
                "session_id": "session_abc",
                "context": None
            }
        }


class GenerateResponse(BaseModel):
    """Response with task ID for tracking"""
    task_id: str
    user_id: str
    session_id: str
    status: str
    message: str
    created_at: str
    estimated_completion_seconds: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user_123",
                "session_id": "session_abc",
                "status": "queued",
                "message": "Request queued for processing",
                "created_at": "2025-01-01T12:00:00Z",
                "estimated_completion_seconds": 45
            }
        }


@router.post(
    "/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Generation"],
    summary="Submit AI generation request",
    description="Submit a prompt for AI-powered app generation. Returns task ID for tracking."
)
async def generate_app(
    request: GenerateRequest,
    http_request: Request,
    background_tasks: BackgroundTasks
) -> GenerateResponse:
    """
    Submit AI generation request.
    
    Flow:
    1. Validate request
    2. Check rate limits
    3. Create task ID and correlation ID
    4. Publish to RabbitMQ
    5. Return task ID immediately
    
    Frontend should:
    - Connect to WebSocket with task_id
    - Listen for progress updates
    - Handle completion/error messages
    """
    
    # Generate IDs
    task_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    session_id = request.session_id or str(uuid.uuid4())
    
    # Set up logging context
    with log_context(
        correlation_id=correlation_id,
        task_id=task_id,
        user_id=request.user_id,
        session_id=session_id,
        endpoint="/api/v1/generate",
        method="POST"
    ):
        logger.info(
            "api.request.received",
            extra={
                "prompt_length": len(request.prompt),
                "has_context": request.context is not None,
                "client_ip": http_request.client.host if http_request.client else None
            }
        )
        
        # Check rate limits
        try:
            allowed, rate_info = await rate_limiter.check_rate_limit(request.user_id)
            
            if not allowed:
                logger.warning(
                    "api.rate_limit.exceeded",
                    extra={
                        "limit": rate_info.get("limit"),
                        "remaining": rate_info.get("remaining"),
                        "retry_after": rate_info.get("retry_after")
                    }
                )
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "rate_limit_exceeded",
                        "message": f"Rate limit exceeded. Try again in {rate_info.get('retry_after', 0)} seconds.",
                        "limit": rate_info.get("limit"),
                        "retry_after": rate_info.get("retry_after")
                    }
                )
            
            logger.info(
                "api.rate_limit.passed",
                extra={
                    "remaining": rate_info.get("remaining"),
                    "limit": rate_info.get("limit")
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "api.rate_limit.check_failed",
                extra={"error": str(e)},
                exc_info=True
            )
            # Fail open - allow request if rate limiter fails
        
        # Create AI request
        try:
            ai_request = AIRequest(
                task_id=task_id,
                user_id=request.user_id,
                session_id=session_id,
                socket_id=f"ws_{task_id}",  # Frontend should connect to WebSocket with task_id
                prompt=request.prompt,
                context=PromptContext(**request.context) if request.context else None,
                timestamp=datetime.utcnow()
            )
            
            logger.info(
                "api.ai_request.created",
                extra={
                    "ai_request": ai_request.dict()
                }
            )
            
        except Exception as e:
            logger.error(
                "api.ai_request.creation_failed",
                extra={"error": str(e)},
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_request",
                    "message": f"Failed to create AI request: {str(e)}"
                }
            )
        
        # Publish to RabbitMQ in background
        async def publish_to_queue():
            """Publish request to RabbitMQ queue"""
            try:
                with log_context(
                    correlation_id=correlation_id,
                    task_id=task_id,
                    operation="publish_to_queue"
                ):
                    success = await queue_manager.publish_response(ai_request.dict())
                    
                    if success:
                        logger.info(
                            "api.queue.published",
                            extra={
                                "queue": "ai-requests",
                                "task_id": task_id
                            }
                        )
                    else:
                        logger.error(
                            "api.queue.publish_failed",
                            extra={
                                "queue": "ai-requests",
                                "task_id": task_id
                            }
                        )
                        
            except Exception as e:
                logger.error(
                    "api.queue.publish_error",
                    extra={
                        "queue": "ai-requests",
                        "task_id": task_id,
                        "error": str(e)
                    },
                    exc_info=True
                )
        
        # Add to background tasks
        background_tasks.add_task(publish_to_queue)
        
        # Create response
        response = GenerateResponse(
            task_id=task_id,
            user_id=request.user_id,
            session_id=session_id,
            status="queued",
            message="Request queued for processing. Connect to WebSocket for updates.",
            created_at=datetime.utcnow().isoformat() + "Z",
            estimated_completion_seconds=45
        )
        
        logger.info(
            "api.response.created",
            extra={
                "response": response.dict(),
                "websocket_instructions": {
                    "endpoint": f"ws://your-domain/ws/{task_id}",
                    "protocol": "JSON",
                    "message_types": ["progress", "complete", "error"]
                }
            }
        )
        
        return response


@router.get(
    "/task/{task_id}",
    tags=["Generation"],
    summary="Get task status",
    description="Check the status of a generation task"
)
async def get_task_status(task_id: str):
    """
    Get task status (implementation depends on your needs).
    
    This is a placeholder - you can implement Redis-based
    task status tracking if needed.
    """
    
    with log_context(task_id=task_id, endpoint="/api/v1/task"):
        logger.info("api.task.status_requested")
        
        # TODO: Implement Redis-based task status lookup
        return {
            "task_id": task_id,
            "status": "processing",
            "message": "Connect to WebSocket for real-time updates"
        }