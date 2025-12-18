"""
Main FastAPI application for AI App Builder Service.

This is the entry point that:
1. Starts the FastAPI web server
2. Connects to RabbitMQ and Redis on startup
3. Consumes AI requests from RabbitMQ
4. Processes requests and sends responses back
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.core.logger import setup_logging
from app.core.messaging import queue_manager
from app.core.cache import cache_manager
from app.models.schemas import AIRequest, ProgressUpdate, ErrorResponse
from app.api.v1 import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    
    Startup:
    - Configure logging
    - Connect to RabbitMQ
    - Connect to Redis
    - Start consuming AI requests
    
    Shutdown:
    - Disconnect from RabbitMQ
    - Disconnect from Redis
    """
    
    # ========================================================================
    # STARTUP
    # ========================================================================
    
    logger.info("=" * 60)
    logger.info(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    logger.info("=" * 60)
    
    # Configure logging
    setup_logging()
    logger.info("✅ Logging configured")
    
    # Connect to RabbitMQ
    try:
        await queue_manager.connect()
        logger.info("✅ RabbitMQ connected")
    except Exception as e:
        logger.error(f"❌ RabbitMQ connection failed: {e}")
        raise
    
    # Connect to Redis
    try:
        await cache_manager.connect()
        logger.info("✅ Redis cache connected")
    except Exception as e:
        logger.warning(f"⚠️  Redis connection failed: {e}")
        # Continue without cache (non-critical)
    
    # Start consuming AI requests in background
    logger.info("👂 Starting AI request consumer...")
    consumer_task = asyncio.create_task(consume_ai_requests())
    
    logger.info("=" * 60)
    logger.info("✅ Service ready to accept requests")
    logger.info("=" * 60)
    
    yield
    
    # ========================================================================
    # SHUTDOWN
    # ========================================================================
    
    logger.info("=" * 60)
    logger.info("🛑 Shutting down service...")
    logger.info("=" * 60)
    
    # Cancel consumer task
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        logger.info("✅ Consumer task cancelled")
    
    # Disconnect from services
    await queue_manager.disconnect()
    logger.info("✅ RabbitMQ disconnected")
    
    await cache_manager.disconnect()
    logger.info("✅ Redis disconnected")
    
    logger.info("=" * 60)
    logger.info("✅ Shutdown complete")
    logger.info("=" * 60)


# ============================================================================
# CREATE FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered mobile app generation service using Claude API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])


# ============================================================================
# RABBITMQ MESSAGE CONSUMER
# ============================================================================

async def consume_ai_requests():
    """
    Main consumer loop - listens to RabbitMQ ai-requests queue.
    
    This is THE entry point where external prompts arrive from API Gateway.
    """
    logger.info(f"👂 Listening for AI requests on queue: {settings.rabbitmq_queue_ai_requests}")
    
    async def message_handler(message_body: dict):
        """
        Handle each incoming AI request message.
        
        Args:
            message_body: Deserialized JSON message from RabbitMQ
        """
        try:
            # Parse incoming request
            request = AIRequest(**message_body)
            logger.info(f"📥 Received AI request - Task: {request.task_id}")
            logger.debug(f"   User: {request.user_id}")
            logger.debug(f"   Prompt: {request.prompt[:100]}...")
            
            # Send initial progress update
            await send_progress(
                task_id=request.task_id,
                socket_id=request.socket_id,
                stage="analyzing",
                progress=5,
                message="Starting AI processing..."
            )
            
            # TODO: Process the prompt (will implement in next steps)
            # For now, just send a dummy response
            logger.info(f"⚙️  Processing request {request.task_id}...")
            
            # Simulate processing
            await asyncio.sleep(2)
            
            # Send completion progress
            await send_progress(
                task_id=request.task_id,
                socket_id=request.socket_id,
                stage="finalizing",
                progress=100,
                message="Processing complete (dummy response)"
            )
            
            # Send dummy response
            dummy_response = {
                "task_id": request.task_id,
                "socket_id": request.socket_id,
                "type": "response",
                "message": "Dummy response - AI processing not yet implemented",
                "prompt_received": request.prompt
            }
            
            await queue_manager.publish_response(dummy_response)
            logger.info(f"✅ Request completed - Task: {request.task_id}")
            
        except Exception as e:
            logger.error(f"❌ Error processing request: {e}")
            
            # Send error response
            try:
                error_response = ErrorResponse(
                    task_id=message_body.get("task_id", "unknown"),
                    socket_id=message_body.get("socket_id", "unknown"),
                    error=str(e),
                    details=str(type(e).__name__)
                )
                await queue_manager.publish_response(error_response.dict())
            except Exception as send_error:
                logger.error(f"Failed to send error response: {send_error}")
    
    # Start consuming messages
    try:
        await queue_manager.consume(
            queue_name=settings.rabbitmq_queue_ai_requests,
            callback=message_handler
        )
    except Exception as e:
        logger.error(f"Consumer error: {e}")
        raise


async def send_progress(
    task_id: str,
    socket_id: str,
    stage: str,
    progress: int,
    message: str
):
    """
    Send progress update to frontend via RabbitMQ.
    
    Args:
        task_id: Task identifier
        socket_id: WebSocket connection ID
        stage: Current processing stage
        progress: Progress percentage (0-100)
        message: Progress message
    """
    progress_update = ProgressUpdate(
        task_id=task_id,
        socket_id=socket_id,
        stage=stage,
        progress=progress,
        message=message
    )
    
    await queue_manager.publish_response(progress_update.dict())
    logger.debug(f"📊 Progress: {stage} - {progress}% - {message}")


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    """
    Root endpoint - basic service information.
    """
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


# ============================================================================
# DEVELOPMENT SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )