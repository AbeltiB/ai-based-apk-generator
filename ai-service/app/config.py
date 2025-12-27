"""
Application configuration management using Pydantic Settings.
Loads configuration from environment variables and .env file.
"""
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden by creating a .env file in the project root.
    Environment variables take precedence over .env file values.
    """
    
    # ============================================================================
    # APPLICATION SETTINGS
    # ============================================================================
    
    app_name: str = "AI App Builder Service"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    
    # ============================================================================
    # ANTHROPIC CLAUDE API SETTINGS
    # ============================================================================
    
    anthropic_api_key: str
    """Anthropic API key - REQUIRED"""
    
    anthropic_model: str = "claude-sonnet-4-20250514"
    """Claude model to use for generation"""
    
    anthropic_max_tokens: int = 4000
    """Maximum tokens per API call"""
    
    anthropic_temperature: float = 0.3
    """Sampling temperature (0.0 - 1.0) - Lower for consistency"""
    
    anthropic_timeout: int = 30
    """API request timeout in seconds"""
    
    # ============================================================================
    # Groq API SETTINGS
    # ============================================================================
    groq_api_key: Optional[str] = None
    """Groq API key (optional, for tier 2 fallback)"""
    
    # ============================================================================
    # RABBITMQ SETTINGS
    # ============================================================================
    
    rabbitmq_url: str = "amqp://admin:password@localhost:5672"
    """RabbitMQ connection URL"""
    
    rabbitmq_queue_ai_requests: str = "ai-requests"
    """Queue name for incoming AI requests"""
    
    rabbitmq_queue_ai_responses: str = "ai-responses"
    """Queue name for outgoing AI responses"""
    
    rabbitmq_prefetch_count: int = 1
    """Number of messages to prefetch (1 = process one at a time)"""
    
    # ============================================================================
    # REDIS SETTINGS
    # ============================================================================
    
    redis_url: str = "redis://localhost:6379"
    """Redis connection URL"""
    
    redis_cache_ttl: int = 86400
    """Cache TTL in seconds (default: 24 hours)"""
    
    redis_semantic_cache_ttl: int = 604800
    """Semantic cache TTL in seconds (default: 7 days)"""
    
    redis_cache_similarity_threshold: float = 0.95
    """Minimum cosine similarity for cache hit (0.0 - 1.0)"""
    
    # ============================================================================
    # POSTGRESQL SETTINGS
    # ============================================================================
    
    postgres_host: str = "localhost"
    """PostgreSQL host"""
    
    postgres_port: int = 5432
    """PostgreSQL port"""
    
    postgres_db: str = "appbuilder"
    """PostgreSQL database name"""
    
    postgres_user: str = "admin"
    """PostgreSQL username"""
    
    postgres_password: str = "password"
    """PostgreSQL password"""
    
    postgres_min_connections: int = 5
    """Minimum connections in pool"""
    
    postgres_max_connections: int = 20
    """Maximum connections in pool"""
    
    # ============================================================================
    # PROCESSING SETTINGS
    # ============================================================================
    
    max_retries: int = 3
    """Maximum number of retries for failed operations"""
    
    retry_delay: int = 2
    """Delay between retries in seconds"""
    
    request_timeout: int = 30
    """Maximum time to process a request (seconds)"""
    
    # ============================================================================
    # RATE LIMITING SETTINGS
    # ============================================================================
    
    rate_limit_requests_per_hour: int = 100
    """Maximum requests per user per hour"""
    
    rate_limit_enabled: bool = True
    """Enable rate limiting"""
    
    # ============================================================================
    # CANVAS SETTINGS
    # ============================================================================
    
    canvas_width: int = 375
    """Mobile canvas width (iPhone standard)"""
    
    canvas_height: int = 667
    """Mobile canvas height (iPhone standard)"""
    
    canvas_safe_area_top: int = 44
    """Safe area inset top (status bar)"""
    
    canvas_safe_area_bottom: int = 34
    """Safe area inset bottom (home indicator)"""
    
    # ============================================================================
    # COMPONENT SETTINGS
    # ============================================================================
    
    available_components: list[str] = [
        "Button", "InputText", "Switch", "Checkbox", "TextArea",
        "Slider", "Spinner", "Text", "Joystick", "ProgressBar",
        "DatePicker", "TimePicker", "ColorPicker", "Map", "Chart"
    ]
    """List of available UI components"""
    
    min_touch_target_size: int = 44
    """Minimum touch target size in pixels (accessibility)"""
    
    # ============================================================================
    # PYDANTIC CONFIGURATION
    # ============================================================================
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    def __repr__(self) -> str:
        """Safe string representation (hides sensitive data)"""
        return (
            f"Settings("
            f"app_name='{self.app_name}', "
            f"debug={self.debug}, "
            f"anthropic_model='{self.anthropic_model}', "
            f"postgres_host='{self.postgres_host}', "
            f"redis_url='{self.redis_url[:20]}...'"
            f")"
        )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are loaded only once.
    This is the recommended way to access settings throughout the application.
    
    Returns:
        Settings instance with all configuration values
        
    Example:
        >>> from app.config import get_settings
        >>> settings = get_settings()
        >>> print(settings.app_name)
        AI App Builder Service
    """
    return Settings()


# Global settings instance for convenience
settings = get_settings()


if __name__ == "__main__":
    # Test configuration loading
    print("=" * 60)
    print("CONFIGURATION TEST")
    print("=" * 60)
    
    test_settings = get_settings()
    
    print(f"\n📋 Application")
    print(f"   Name: {test_settings.app_name}")
    print(f"   Version: {test_settings.app_version}")
    print(f"   Debug: {test_settings.debug}")
    print(f"   Log Level: {test_settings.log_level}")
    
    print(f"\n🤖 Claude API")
    print(f"   Model: {test_settings.anthropic_model}")
    print(f"   Max Tokens: {test_settings.anthropic_max_tokens}")
    print(f"   Temperature: {test_settings.anthropic_temperature}")
    print(f"   Timeout: {test_settings.anthropic_timeout}s")
    print(f"   API Key: {'✅ Loaded' if test_settings.anthropic_api_key else '❌ Missing'}")
    
    print(f"\n🐰 RabbitMQ")
    print(f"   URL: {test_settings.rabbitmq_url}")
    print(f"   Request Queue: {test_settings.rabbitmq_queue_ai_requests}")
    print(f"   Response Queue: {test_settings.rabbitmq_queue_ai_responses}")
    
    print(f"\n📦 Redis")
    print(f"   URL: {test_settings.redis_url}")
    print(f"   Cache TTL: {test_settings.redis_cache_ttl}s")
    print(f"   Semantic Cache TTL: {test_settings.redis_semantic_cache_ttl}s")
    
    print(f"\n🐘 PostgreSQL")
    print(f"   Host: {test_settings.postgres_host}:{test_settings.postgres_port}")
    print(f"   Database: {test_settings.postgres_db}")
    print(f"   User: {test_settings.postgres_user}")
    print(f"   Pool: {test_settings.postgres_min_connections}-{test_settings.postgres_max_connections}")
    
    print(f"\n📱 Canvas")
    print(f"   Size: {test_settings.canvas_width}x{test_settings.canvas_height}")
    print(f"   Safe Area: Top {test_settings.canvas_safe_area_top}, Bottom {test_settings.canvas_safe_area_bottom}")
    
    print(f"\n🎨 Components")
    print(f"   Available: {len(test_settings.available_components)}")
    print(f"   Min Touch Size: {test_settings.min_touch_target_size}px")
    
    print("\n" + "=" * 60)
    print("✅ Configuration loaded successfully!")
    print("=" * 60)