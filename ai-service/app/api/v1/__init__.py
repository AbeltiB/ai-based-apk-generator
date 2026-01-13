"""
API v1 endpoints.
"""

from .health_advanced import router as health_router
from .generate import router as generate_router
from .stats import router as stats_router

__all__ = ["health_router", "generate_router", "stats_router"]