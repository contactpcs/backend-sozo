"""Application configuration using Pydantic."""
from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings

from .constants import Environment


class DatabaseSettings(BaseSettings):
    """Database configuration."""
    
    url: str = Field(
        ...,
        description="Full database URL (postgresql, sqlite, etc)"
    )
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max overflow connections")
    pool_pre_ping: bool = Field(default=True, description="Test connections before using")
    echo: bool = Field(default=False, description="SQL echo for debugging")
    
    class Config:
        case_sensitive = False

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v):
        """Ensure database URL is provided."""
        if not v:
            raise ValueError("DATABASE_URL environment variable is required")
        return v



class AzureSettings(BaseSettings):
    """Azure cloud configuration."""
    
    key_vault_url: Optional[str] = Field(default=None, description="Azure Key Vault URL")
    storage_account_name: Optional[str] = Field(default=None, description="Azure Storage account")
    storage_account_key: Optional[SecretStr] = Field(default=None, description="Azure Storage key")
    openai_api_key: Optional[SecretStr] = Field(default=None, description="Azure OpenAI key")
    openai_endpoint: Optional[str] = Field(default=None, description="Azure OpenAI endpoint")
    openai_deployment: Optional[str] = Field(default=None, description="Azure OpenAI deployment")
    
    class Config:
        env_prefix = "AZURE_"


class JWTSettings(BaseSettings):
    """JWT security configuration."""
    
    secret_key: SecretStr = Field(default=SecretStr("dev-secret-key-change-in-production"))
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60)
    refresh_token_expire_days: int = Field(default=7)
    
    class Config:
        env_prefix = "JWT_"


class AISettings(BaseSettings):
    """AI/LLM configuration."""
    
    provider: str = Field(default="openai", description="LLM provider: openai, azure_openai, claude")
    openai_api_key: Optional[SecretStr] = Field(default=None)
    openai_model: str = Field(default="gpt-4")
    claude_api_key: Optional[SecretStr] = Field(default=None)
    claude_model: str = Field(default="claude-3-sonnet-20240229")
    max_tokens: int = Field(default=2048)
    temperature: float = Field(default=0.7)
    
    class Config:
        env_prefix = "AI_"


class Settings(BaseSettings):
    """Main application settings."""
    
    # Application
    app_name: str = Field(default="Sozo")
    app_version: str = Field(default="0.1.0")
    environment: Environment = Field(default=Environment.DEV)
    debug: bool = Field(default=False)
    
    # API
    api_v1_prefix: str = Field(default="/api/v1")
    api_title: str = Field(default="Sozo Healthcare Platform API")
    
    # CORS
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://localhost:8000", "http://localhost:8080", "http://localhost:5173"])
    cors_credentials: bool = Field(default=True)
    cors_methods: list[str] = Field(default=["GET", "POST", "PUT", "DELETE", "PATCH"])
    cors_headers: list[str] = Field(default=["*"])
    
    # Database
    database_url: str = Field(
        ...,
        description="Database connection URL (loaded via DATABASE_URL env var)"
    )
    db_pool_size: int = Field(default=10, description="Database connection pool size")
    db_max_overflow: int = Field(default=20, description="Database max overflow connections")
    
    # Supabase API
    supabase_url: Optional[str] = Field(default=None, description="Supabase project URL")
    supabase_key: Optional[SecretStr] = Field(default=None, description="Supabase API key")
    
    # Security
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    
    # Azure
    azure: AzureSettings = Field(default_factory=AzureSettings)
    
    # AI/LLM
    ai: AISettings = Field(default_factory=AISettings)
    
    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")  # json or text
    
    # Security
    require_https: bool = Field(default=True)
    secure_cookies: bool = Field(default=True)
    session_timeout_minutes: int = Field(default=1440)
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
        case_sensitive = False

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, v: str) -> Environment:
        """Validate environment string."""
        if isinstance(v, str):
            return Environment(v.lower())
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from JSON array, comma-separated string, or list."""
        if isinstance(v, str):
            import json
            # Try to parse as JSON array first
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                # Fall back to comma-separated parsing
                pass
            # Parse as comma-separated string
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def db(self) -> DatabaseSettings:
        """Get database settings from database_url."""
        return DatabaseSettings(url=self.database_url)

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == Environment.PROD

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == Environment.DEV

    @property
    def is_postgres(self) -> bool:
        """Check if using PostgreSQL."""
        return "postgresql" in self.database_url.lower()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
