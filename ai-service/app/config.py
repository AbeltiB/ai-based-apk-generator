"""
Application configuration management using Pydantic Settings.
Loads configuration from environment variables and .env file.

This configuration handles:
- Application settings and metadata
- Multiple LLM provider configurations (Anthropic Claude, Llama3, Groq)
- Message queue (RabbitMQ) settings
- Caching (Redis) with semantic caching
- Database (PostgreSQL) connections
- Rate limiting and security
- UI/Canvas specifications
- Component definitions
- Processing and retry logic
"""
import logging
import sys
from typing import Literal, Optional, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator, field_validator
from functools import lru_cache
import os

# Configure logging for configuration module
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden by creating a .env file in the project root.
    Environment variables take precedence over .env file values.
    Sensitive values are masked in logging.
    
    Usage:
        >>> from app.config import get_settings
        >>> settings = get_settings()
        >>> print(settings.app_name)
    """
    
    # ============================================================================
    # APPLICATION METADATA & RUNTIME SETTINGS
    # ============================================================================
    
    app_name: str = "AI App Builder Service"
    """Application name displayed in logs and API responses"""
    
    app_version: str = "0.1.0"
    """Application semantic version"""
    
    api_title: str = "AI Service API"
    """OpenAPI documentation title"""
    
    api_version: str = "1.0.0"
    """API version for endpoint routing"""
    
    environment: Literal["development", "staging", "production"] = "development"
    """Runtime environment - affects logging, debugging, and features"""
    
    debug: bool = False
    """Enable debug mode (verbose logging, additional endpoints)"""
    
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    """Logging verbosity level"""
    
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    """Allowed CORS origins for API requests"""
    
    # ============================================================================
    # ANTHROPIC CLAUDE API SETTINGS (Primary LLM)
    # ============================================================================

    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key - REQUIRED for primary LLM")
    """Anthropic API key - REQUIRED"""
    
    anthropic_model: str = "claude-sonnet-4-20250514"
    """Claude model to use for generation (claude-3-opus-20240229, claude-3-sonnet-20240229, etc.)"""
    
    anthropic_max_tokens: int = 4000
    """Maximum tokens per API call"""
    
    anthropic_temperature: float = 0.3
    """Sampling temperature (0.0 - 1.0) - Lower for consistency"""
    
    anthropic_timeout: int = 30
    """API request timeout in seconds"""
    
    anthropic_max_retries: int = 3
    """Maximum retries for Anthropic API calls"""
    
    anthropic_retry_delay: int = 2
    """Delay between retries in seconds"""
    
    # ============================================================================
    # LLAMA3 API SETTINGS (Secondary/Fallback LLM)
    # ============================================================================
    
    llama3_api_url: str = "https://fastchat.ideeza.com/v1/chat/completions"
    """Llama3 API endpoint URL"""
    
    llama3_model: str = "llama-3-70b-instruct"
    """Llama3 model identifier"""
    
    llama3_api_key: Optional[str] = None
    """Llama3 API key (optional, for fallback)"""
    
    llama3_timeout: float = 60.0
    """Llama3 API timeout in seconds"""
    
    llama3_max_tokens: int = 2000
    """Maximum tokens for Llama3 responses"""
    
    llama3_temperature: float = 0.7
    """Llama3 sampling temperature"""
    
    # ============================================================================
    # GROQ API SETTINGS (Tier 2 Fallback)
    # ============================================================================
    
    groq_api_key: Optional[str] = None
    """Groq API key (optional, for tier 2 fallback)"""
    
    groq_model: str = "mixtral-8x7b-32768"
    """Groq model to use (mixtral-8x7b-32768, llama2-70b-4096, etc.)"""
    
    groq_timeout: int = 30
    """Groq API timeout in seconds"""
    
    # ============================================================================
    # LLM ORCHESTRATOR & FAILOVER SETTINGS
    # ============================================================================
    
    llm_primary_provider: Literal["anthropic", "llama3", "groq"] = "anthropic"
    """Primary LLM provider to use"""
    
    llm_fallback_enabled: bool = True
    """Enable automatic failover to backup LLM providers"""
    
    llm_fallback_sequence: list[str] = ["anthropic", "llama3", "groq"]
    """Fallback sequence for LLM providers"""
    
    llm_failure_threshold: int = 3
    """Number of consecutive failures before marking provider as unhealthy"""
    
    llm_failure_window_minutes: int = 5
    """Time window for tracking failures"""
    
    llm_health_check_interval: int = 60
    """Health check interval in seconds"""
    
    llm_default_temperature: float = 0.7
    """Default temperature for LLM calls"""
    
    llm_default_max_tokens: int = 2000
    """Default maximum tokens for LLM responses"""
    
    # ============================================================================
    # PROMPT ENGINEERING SETTINGS
    # ============================================================================
    
    default_prompt_version: str = "v2"
    """Default prompt template version"""
    
    prompt_cache_enabled: bool = True
    """Enable caching of compiled prompts"""
    
    prompt_cache_ttl: int = 3600
    """Prompt cache TTL in seconds"""
    
    system_prompt_path: str = "prompts/system"
    """Path to system prompt templates"""
    
    user_prompt_path: str = "prompts/user"
    """Path to user prompt templates"""
    
    # ============================================================================
    # RABBITMQ MESSAGE QUEUE SETTINGS
    # ============================================================================
    
    rabbitmq_url: str = "amqp://admin:password@localhost:5672"
    """RabbitMQ connection URL"""
    
    rabbitmq_host: str = "localhost"
    """RabbitMQ host (alternative to URL)"""
    
    rabbitmq_port: int = 5672
    """RabbitMQ port"""
    
    rabbitmq_user: str = "guest"
    """RabbitMQ username"""
    
    rabbitmq_password: str = "guest"
    """RabbitMQ password"""
    
    rabbitmq_queue_ai_requests: str = "ai-requests"
    """Queue name for incoming AI requests"""
    
    rabbitmq_queue_ai_responses: str = "ai-responses"
    """Queue name for outgoing AI responses"""
    
    rabbitmq_queue_app_generation: str = "app-generation-queue"
    """Queue name for app generation tasks"""
    
    rabbitmq_prefetch_count: int = 1
    """Number of messages to prefetch (1 = process one at a time)"""
    
    rabbitmq_heartbeat: int = 60
    """RabbitMQ heartbeat interval in seconds"""
    
    rabbitmq_connection_timeout: int = 10
    """RabbitMQ connection timeout in seconds"""
    
    # ============================================================================
    # REDIS CACHE & SESSION SETTINGS
    # ============================================================================
    
    redis_url: str = "redis://localhost:6379"
    """Redis connection URL"""
    
    redis_host: str = "localhost"
    """Redis host (alternative to URL)"""
    
    redis_port: int = 6379
    """Redis port"""
    
    redis_db: int = 0
    """Redis database number"""
    
    redis_password: Optional[str] = None
    """Redis password (if required)"""
    
    redis_cache_ttl: int = 86400
    """Cache TTL in seconds (default: 24 hours)"""
    
    redis_semantic_cache_ttl: int = 604800
    """Semantic cache TTL in seconds (default: 7 days)"""
    
    redis_session_ttl: int = 28800
    """Session TTL in seconds (default: 8 hours)"""
    
    redis_cache_similarity_threshold: float = 0.95
    """Minimum cosine similarity for cache hit (0.0 - 1.0)"""
    
    redis_pool_size: int = 10
    """Redis connection pool size"""
    
    redis_socket_timeout: int = 5
    """Redis socket timeout in seconds"""
    
    # ============================================================================
    # POSTGRESQL DATABASE SETTINGS
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
    
    postgres_connection_timeout: int = 30
    """Connection timeout in seconds"""
    
    postgres_statement_timeout: int = 30000
    """Statement timeout in milliseconds"""
    
    postgres_pool_recycle: int = 3600
    """Connection pool recycle time in seconds"""
    
    # ============================================================================
    # PROCESSING, RETRY & TIMEOUT SETTINGS
    # ============================================================================
    
    max_retries: int = 3
    """Maximum number of retries for failed operations"""
    
    retry_delay: int = 2
    """Base delay between retries in seconds"""
    
    retry_backoff_factor: float = 1.5
    """Exponential backoff factor for retries"""
    
    request_timeout: int = 30
    """Maximum time to process a request (seconds)"""
    
    batch_processing_size: int = 10
    """Maximum batch size for batch operations"""
    
    concurrent_workers: int = 4
    """Number of concurrent worker threads/processes"""
    
    # ============================================================================
    # RATE LIMITING & SECURITY SETTINGS
    # ============================================================================
    
    rate_limit_enabled: bool = True
    """Enable rate limiting"""
    
    rate_limit_requests_per_hour: int = 100
    """Maximum requests per user per hour"""
    
    rate_limit_requests_per_minute: int = 20
    """Maximum requests per user per minute"""
    
    rate_limit_window_size: int = 60
    """Rate limit window size in seconds"""
    
    rate_limit_storage_backend: Literal["redis", "memory"] = "redis"
    """Storage backend for rate limiting"""
    
    api_key_header: str = "X-API-Key"
    """Header name for API key authentication"""
    
    jwt_secret_key: Optional[str] = None
    """Secret key for JWT token generation and validation"""
    
    jwt_algorithm: str = "HS256"
    """JWT signing algorithm"""
    
    jwt_token_expire_minutes: int = 60
    """JWT token expiration time in minutes"""
    
    # ============================================================================
    # UI/CANVAS SPECIFICATION SETTINGS
    # ============================================================================
    
    canvas_width: int = 375
    """Mobile canvas width (iPhone standard)"""
    
    canvas_height: int = 667
    """Mobile canvas height (iPhone standard)"""
    
    canvas_safe_area_top: int = 44
    """Safe area inset top (status bar)"""
    
    canvas_safe_area_bottom: int = 34
    """Safe area inset bottom (home indicator)"""
    
    canvas_background_color: str = "#FFFFFF"
    """Default canvas background color"""
    
    canvas_grid_size: int = 8
    """Grid size for component alignment"""
    
    canvas_snap_to_grid: bool = True
    """Enable snap-to-grid for component placement"""
    
    # ============================================================================
    # COMPONENT LIBRARY SETTINGS
    # ============================================================================
    
    available_components: list[str] = [
        "Button", "InputText", "Switch", "Checkbox", "TextArea",
        "Slider", "Spinner", "Text", "Joystick", "ProgressBar",
        "DatePicker", "TimePicker", "ColorPicker", "Map", "Chart",
        "Dropdown", "RadioGroup", "Image", "Video", "Audio",
        "List", "Grid", "Card", "Modal", "TabView"
    ]
    """List of available UI components"""
    
    min_touch_target_size: int = 44
    """Minimum touch target size in pixels (accessibility)"""
    
    default_font_family: str = "San Francisco, Roboto, sans-serif"
    """Default font family stack"""
    
    default_font_size: int = 16
    """Default font size in pixels"""
    
    default_spacing_unit: int = 8
    """Default spacing unit (8-point grid system)"""
    
    # ============================================================================
    # FILE STORAGE & ASSET SETTINGS
    # ============================================================================
    
    upload_directory: str = "./uploads"
    """Directory for file uploads"""
    
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    """Maximum upload file size in bytes"""
    
    allowed_file_types: list[str] = [".png", ".jpg", ".jpeg", ".gif", ".pdf", ".txt"]
    """Allowed file extensions for uploads"""
    
    asset_base_url: str = "https://assets.example.com"
    """Base URL for served assets"""
    
    # ============================================================================
    # MONITORING & METRICS SETTINGS
    # ============================================================================
    
    metrics_enabled: bool = True
    """Enable metrics collection"""
    
    metrics_port: int = 9090
    """Metrics server port"""
    
    health_check_endpoint: str = "/health"
    """Health check endpoint path"""
    
    readiness_endpoint: str = "/ready"
    """Readiness endpoint path"""
    
    prometheus_endpoint: str = "/metrics"
    """Prometheus metrics endpoint"""
    
    # ============================================================================
    # VALIDATORS & COMPUTED PROPERTIES
    # ============================================================================
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate and normalize log level"""
        logger.info(f"Setting log level to: {v}")
        return v.upper()
    
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value"""
        valid_environments = ["development", "staging", "production"]
        if v not in valid_environments:
            logger.warning(f"Invalid environment '{v}', defaulting to 'development'")
            return "development"
        logger.info(f"Application environment: {v}")
        return v
    
    @field_validator('debug')
    @classmethod
    def set_debug_from_environment(cls, v: bool, info) -> bool:
        """Override debug mode based on environment"""
        environment = info.data.get('environment', 'development')
        if environment == "production" and v:
            logger.warning("Debug mode is enabled in production environment")
        elif environment == "development" and not v:
            logger.info("Auto-enabling debug mode for development")
            return True
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == "development"
    
    @property
    def postgres_dsn(self) -> str:
        """Get PostgreSQL connection DSN"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration dictionary"""
        return {
            "primary_provider": self.llm_primary_provider,
            "fallback_enabled": self.llm_fallback_enabled,
            "fallback_sequence": self.llm_fallback_sequence,
            "failure_threshold": self.llm_failure_threshold,
            "failure_window_minutes": self.llm_failure_window_minutes,
            "default_temperature": self.llm_default_temperature,
            "default_max_tokens": self.llm_default_max_tokens,
            "anthropic_model": self.anthropic_model,
            "llama3_api_url": self.llama3_api_url,
            "llama3_model": self.llama3_model,
            "groq_model": self.groq_model,
        }
    
    # ============================================================================
    # PYDANTIC CONFIGURATION
    # ============================================================================
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="APP_",  # All environment variables should be prefixed with APP_
        validate_default=True,
    )
    
    def __repr__(self) -> str:
        """Safe string representation (hides sensitive data)"""
        masked_api_key = f"{self.anthropic_api_key[:8]}...{self.anthropic_api_key[-4:]}" if self.anthropic_api_key else "Not Set"
        
        return (
            f"Settings(\n"
            f"  app_name='{self.app_name}', version='{self.app_version}', environment='{self.environment}'\n"
            f"  debug={self.debug}, log_level='{self.log_level}'\n"
            f"  anthropic_model='{self.anthropic_model}', api_key='{masked_api_key}'\n"
            f"  postgres='{self.postgres_host}:{self.postgres_port}/{self.postgres_db}'\n"
            f"  redis='{self.redis_host}:{self.redis_port}'\n"
            f"  rabbitmq='{self.rabbitmq_host}:{self.rabbitmq_port}'\n"
            f")"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get cached settings instance with comprehensive logging.
    
    Uses lru_cache to ensure settings are loaded only once.
    This is the recommended way to access settings throughout the application.
    
    Returns:
        Settings instance with all configuration values
        
    Example:
        >>> from app.config import get_settings
        >>> settings = get_settings()
        >>> print(settings.app_name)
    """
    logger.info("🚀 Initializing application configuration...")
    
    try:
        # Check for .env file
        env_file = ".env"
        if os.path.exists(env_file):
            logger.info(f"📁 Loading configuration from {env_file}")
        else:
            logger.warning(f"⚠️  {env_file} not found, using environment variables and defaults")
        
        # Load settings
        settings = Settings()
        
        # Log successful loading
        logger.info(f"✅ Configuration loaded successfully for {settings.app_name} v{settings.app_version}")
        logger.info(f"   Environment: {settings.environment}")
        logger.info(f"   Debug mode: {'Enabled' if settings.debug else 'Disabled'}")
        logger.info(f"   Log level: {settings.log_level}")
        
        # Log LLM configuration
        llm_status = []
        if settings.anthropic_api_key:
            llm_status.append("Anthropic Claude ✓")
        if settings.llama3_api_key:
            llm_status.append("Llama3 ✓")
        if settings.groq_api_key:
            llm_status.append("Groq ✓")
        
        logger.info(f"🤖 LLM Providers: {', '.join(llm_status) if llm_status else 'None configured'}")
        logger.info(f"   Primary provider: {settings.llm_primary_provider}")
        logger.info(f"   Fallback enabled: {settings.llm_fallback_enabled}")
        
        # Log service connections
        logger.info("🔌 Service Connections:")
        logger.info(f"   PostgreSQL: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
        logger.info(f"   Redis: {settings.redis_host}:{settings.redis_port}")
        logger.info(f"   RabbitMQ: {settings.rabbitmq_host}:{settings.rabbitmq_port}")
        
        # Warnings for production
        if settings.is_production:
            if settings.debug:
                logger.warning("🚨 WARNING: Debug mode is enabled in production!")
            if not settings.anthropic_api_key:
                logger.error("❌ CRITICAL: Anthropic API key is required in production!")
            if settings.rabbitmq_password == "guest":
                logger.warning("⚠️  WARNING: Using default RabbitMQ credentials in production!")
            if settings.postgres_password == "password":
                logger.warning("⚠️  WARNING: Using default PostgreSQL credentials in production!")
        
        return settings
        
    except Exception as e:
        logger.critical(f"❌ Failed to load configuration: {str(e)}")
        logger.critical("Please check your .env file or environment variables")
        raise


def print_configuration_summary(settings: Settings) -> None:
    """
    Print a comprehensive configuration summary to console.
    
    Args:
        settings: Settings instance to summarize
    """
    print("=" * 80)
    print("CONFIGURATION SUMMARY")
    print("=" * 80)
    
    # Application info
    print(f"\n📦 APPLICATION")
    print(f"   Name: {settings.app_name}")
    print(f"   Version: {settings.app_version}")
    print(f"   API Title: {settings.api_title}")
    print(f"   Environment: {settings.environment.upper()}")
    print(f"   Debug: {'✅ Enabled' if settings.debug else '❌ Disabled'}")
    print(f"   Log Level: {settings.log_level}")
    
    # LLM Configuration
    print(f"\n🤖 LLM CONFIGURATION")
    print(f"   Primary Provider: {settings.llm_primary_provider.upper()}")
    print(f"   Fallback Enabled: {'✅ Yes' if settings.llm_fallback_enabled else '❌ No'}")
    
    print(f"\n   🔷 Anthropic Claude")
    print(f"      Model: {settings.anthropic_model}")
    print(f"      Max Tokens: {settings.anthropic_max_tokens}")
    print(f"      Temperature: {settings.anthropic_temperature}")
    print(f"      API Key: {'✅ Loaded' if settings.anthropic_api_key else '❌ Missing'}")
    
    print(f"\n   🦙 Llama3")
    print(f"      Model: {settings.llama3_model}")
    print(f"      API URL: {settings.llama3_api_url}")
    print(f"      API Key: {'✅ Loaded' if settings.llama3_api_key else '⚠️  Optional'}")
    
    print(f"\n   ⚡ Groq")
    print(f"      Model: {settings.groq_model}")
    print(f"      API Key: {'✅ Loaded' if settings.groq_api_key else '⚠️  Optional'}")
    
    # Database
    print(f"\n🗄️  DATABASE")
    print(f"   PostgreSQL: {settings.postgres_host}:{settings.postgres_port}")
    print(f"   Database: {settings.postgres_db}")
    print(f"   User: {settings.postgres_user}")
    print(f"   Pool: {settings.postgres_min_connections}-{settings.postgres_max_connections}")
    
    # Cache
    print(f"\n💾 CACHE & SESSIONS")
    print(f"   Redis: {settings.redis_host}:{settings.redis_port}")
    print(f"   Cache TTL: {settings.redis_cache_ttl}s ({settings.redis_cache_ttl//3600}h)")
    print(f"   Semantic Cache TTL: {settings.redis_semantic_cache_ttl}s ({settings.redis_semantic_cache_ttl//86400}d)")
    print(f"   Session TTL: {settings.redis_session_ttl}s ({settings.redis_session_ttl//3600}h)")
    
    # Message Queue
    print(f"\n🐰 MESSAGE QUEUE")
    print(f"   RabbitMQ: {settings.rabbitmq_host}:{settings.rabbitmq_port}")
    print(f"   User: {settings.rabbitmq_user}")
    print(f"   Queues: {settings.rabbitmq_queue_ai_requests}, {settings.rabbitmq_queue_ai_responses}")
    print(f"   App Generation Queue: {settings.rabbitmq_queue_app_generation}")
    
    # Canvas & UI
    print(f"\n🎨 UI/CANVAS")
    print(f"   Canvas Size: {settings.canvas_width}x{settings.canvas_height}")
    print(f"   Safe Area: Top {settings.canvas_safe_area_top}px, Bottom {settings.canvas_safe_area_bottom}px")
    print(f"   Available Components: {len(settings.available_components)}")
    print(f"   Min Touch Size: {settings.min_touch_target_size}px")
    
    # Security
    print(f"\n🔐 SECURITY")
    print(f"   Rate Limiting: {'✅ Enabled' if settings.rate_limit_enabled else '❌ Disabled'}")
    print(f"   Requests/Hour: {settings.rate_limit_requests_per_hour}")
    print(f"   JWT Expiration: {settings.jwt_token_expire_minutes} minutes")
    print(f"   API Key Header: {settings.api_key_header}")
    
    # File Uploads
    print(f"\n📁 FILE UPLOADS")
    print(f"   Upload Directory: {settings.upload_directory}")
    print(f"   Max Upload Size: {settings.max_upload_size // (1024*1024)}MB")
    print(f"   Allowed Types: {', '.join(settings.allowed_file_types)}")
    
    print("\n" + "=" * 80)
    print("✅ CONFIGURATION LOADED SUCCESSFULLY")
    print("=" * 80)


# Global settings instance for convenience
settings = get_settings()


if __name__ == "__main__":
    # Configure basic logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    # Test configuration loading
    print_configuration_summary(settings)
    
    # Additional debug info
    if settings.debug:
        print(f"\n🔍 DEBUG INFORMATION:")
        print(f"   LLM Config Dict: {settings.llm_config}")
        print(f"   PostgreSQL DSN: {settings.postgres_dsn}")
        print(f"   Is Production: {settings.is_production}")
        print(f"   Is Development: {settings.is_development}")