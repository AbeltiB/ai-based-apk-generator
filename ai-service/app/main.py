"""
Main FastAPI application for AI App Builder Service.

This is the entry point that:
1. Starts the FastAPI web server
2. Connects to all infrastructures (RabbitMQ, Redis, PostgreSQL)
3. Consumes AI requests from RabbitMQ
4. Processes requests through the pipeline
5. Publishes response back RabbitMQ
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
from app.core.database import db_manager
from app.models.schemas import AIRequest
from app.services.pipeline import default_pipeline
from app.api.v1 import health, test_routes


# ============================================================================
# APPLICATION LIFESPAN
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """

    # ------------------------------------------------------------------------
    # STARTUP
    # ------------------------------------------------------------------------

    logger.info("=" * 60)
    logger.info(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    logger.info("=" * 60)

    setup_logging()
    logger.info("✅ Logging configured")

    # RabbitMQ
    try:
        await queue_manager.connect()
        logger.info("✅ RabbitMQ connected")
    except Exception as e:
        logger.error(f"❌ RabbitMQ connection failed: {e}")
        raise

    # Redis
    try:
        await cache_manager.connect()
        logger.info("✅ Redis cache connected")
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed: {e}")
        logger.warning("   Continuing without cache (degraded performance)")

    # PostgreSQL
    try:
        await db_manager.connect()
        logger.info("✅ PostgreSQL connected")
    except Exception as e:
        logger.error(f"❌ PostgreSQL connection failed: {e}")
        raise

    # Start consumer
    logger.info("👂 Starting AI request consumer...")
    consumer_task = asyncio.create_task(consume_ai_requests())

    logger.info("=" * 60)
    logger.info("✅ Service ready to accept requests")
    logger.info("=" * 60)

    yield

    # ------------------------------------------------------------------------
    # SHUTDOWN
    # ------------------------------------------------------------------------

    logger.info("=" * 60)
    logger.info("🛑 Shutting down service...")
    logger.info("=" * 60)

    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        logger.info("✅ Consumer task cancelled")

    await queue_manager.disconnect()
    logger.info("✅ RabbitMQ disconnected")

    await cache_manager.disconnect()
    logger.info("✅ Redis disconnected")

    await db_manager.disconnect()
    logger.info("✅ PostgreSQL disconnected")

    logger.info("=" * 60)
    logger.info("✅ Shutdown complete")
    logger.info("=" * 60)


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered mobile app generation service using Claude API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # configure in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(test_routes.router, prefix="/api/v1", tags=["Testing"])


# ============================================================================
# RABBITMQ CONSUMER
# ============================================================================

async def consume_ai_requests():
    """
    Main consumer loop - listens to RabbitMQ ai-requests queue.
    """

    logger.info(
        f"👂 Listening for AI requests on queue: "
        f"{settings.rabbitmq_queue_ai_requests}"
    )

    async def message_handler(message_body: dict):
        try:
            request = AIRequest(**message_body)

            logger.info(f"📥 Received AI request - Task: {request.task_id}")
            logger.debug(f"   User: {request.user_id}")
            logger.debug(f"   Prompt: {request.prompt[:100]}...")

            await default_pipeline.send_progress(
                task_id=request.task_id,
                socket_id=request.socket_id,
                stage="analyzing",
                progress=5,
                message="Starting AI processing...",
            )

            try:
                result = await default_pipeline.execute(request)
                logger.info(f"✅ Request completed - Task: {request.task_id}")
                logger.debug(
                    f"   Total time: {result.get('total_time_ms', 0)}ms"
                )
            except Exception as pipeline_error:
                logger.error(f"❌ Pipeline execution failed: {pipeline_error}")

                await default_pipeline.send_error(
                    task_id=request.task_id,
                    socket_id=request.socket_id,
                    error="Pipeline execution failed",
                    details=str(pipeline_error),
                )

        except Exception as e:
            logger.error(f"❌ Error processing request: {e}")

            try:
                await default_pipeline.send_error(
                    task_id=message_body.get("task_id", "unknown"),
                    socket_id=message_body.get("socket_id", "unknown"),
                    error="Failed to process request",
                    details=str(e),
                )
            except Exception as send_error:
                logger.error(
                    f"❌ Failed to send error response: {send_error}"
                )

    try:
        await queue_manager.consume(
            queue_name=settings.rabbitmq_queue_ai_requests,
            callback=message_handler,
        )
    except Exception as e:
        logger.error(f"❌ Consume error: {e}")
        raise


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health",
        "features": {
            "rabbitmq": queue_manager.is_connected,
            "redis": cache_manager._connected,
            "postgresql": db_manager.is_connected,
        },
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
        log_level=settings.log_level.lower(),
    )
