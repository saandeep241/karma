"""Configuration settings for the Karma backend."""

from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI settings
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    
    # Karma AI toggle - set to "true" to use real AI, otherwise uses dummy mode
    openai_karma: str = ""  # Set OPENAI_KARMA=true to enable AI
    
    # Clerk Authentication (optional)
    clerk_secret_key: Optional[str] = None
    clerk_publishable_key: Optional[str] = None
    
    # App settings
    app_name: str = "Karma - Smart Task Suggestions"
    debug: bool = False
    
    # CORS settings for frontend
    frontend_url: str = "http://localhost:5173"  # Vite default
    
    # Cloud Storage settings
    use_cloud_storage: bool = False  # Set USE_CLOUD_STORAGE=true to enable
    gcs_bucket_name: str = "karma-app-data"  # Cloud Storage bucket name
    
    # Cloud SQL (PostgreSQL) settings
    database_url: Optional[str] = None  # Full database URL (overrides individual settings)
    cloud_sql_connection_name: Optional[str] = None  # PROJECT:REGION:INSTANCE
    database_user: str = "karma_user"
    database_password: Optional[str] = None
    database_name: str = "karma"
    database_host: Optional[str] = None  # For TCP connection (alternative to Unix socket)
    database_port: int = 5432
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars
    
    @property
    def is_ai_enabled(self) -> bool:
        """Check if AI is enabled (OPENAI_KARMA=true and API key exists)."""
        return self.openai_karma.lower() == "true" and bool(self.openai_api_key)
    
    @property
    def is_auth_enabled(self) -> bool:
        """Check if Clerk authentication is enabled."""
        return bool(self.clerk_secret_key and self.clerk_publishable_key)
    
    @property
    def use_postgresql(self) -> bool:
        """Check if PostgreSQL should be used (Cloud SQL)."""
        return bool(self.database_url or self.cloud_sql_connection_name or self.database_host)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

