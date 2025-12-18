"""
Application configuration management using Pydantic Settings.
Loads configuration from environment variables and .env file.
"""
from typing import Literal
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
    
    anthropic_temperature: float = 0.7
    """Sampling temperature (0.0 - 1.0)"""
    
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
    
    # ============================================================================
    # PROCESSING SETTINGS
    # ============================================================================
    
    max_retries: int = 3
    """Maximum number of retries for failed operations"""
    
    retry_delay: int = 2
    """Delay between retries in seconds"""
    
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
        """Safe string representation (hides API key)"""
        return (
            f"Settings("
            f"app_name='{self.app_name}', "
            f"debug={self.debug}, "
            f"anthropic_model='{self.anthropic_model}', "
            f"anthropic_api_key='sk-ant-***...'"
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
    
    print(f"\nApp Name: {test_settings.app_name}")
    print(f"Version: {test_settings.app_version}")
    print(f"Debug Mode: {test_settings.debug}")
    print(f"Log Level: {test_settings.log_level}")
    print(f"\nClaude Model: {test_settings.anthropic_model}")
    print(f"Max Tokens: {test_settings.anthropic_max_tokens}")
    print(f"\nRabbitMQ URL: {test_settings.rabbitmq_url}")
    print(f"Redis URL: {test_settings.redis_url}")
    print(f"\nAPI Key: {'✅ Loaded' if test_settings.anthropic_api_key else '❌ Missing'}")
    
    print("\n" + "=" * 60)
    print("✅ Configuration loaded successfully!")
    print("=" * 60)