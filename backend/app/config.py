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
    openai_karma: str = "false"  # Defaults to false (dummy mode). Set OPENAI_KARMA=true to enable AI
    
    # Clerk Authentication (optional)
    clerk_secret_key: Optional[str] = None
    clerk_publishable_key: Optional[str] = None
    
    # App settings
    app_name: str = "Karma - Smart Task Suggestions"
    debug: bool = False
    
    # Token rate limiting
    default_monthly_token_limit: int = 1_000_000  # Default: 1M tokens per month per user
    
    # Admin configuration
    admin_user_ids: str = ""  # Comma-separated list of admin user IDs
    admin_emails: str = ""  # Comma-separated list of admin emails
    
    # Database configuration (PostgreSQL/Cloud SQL)
    database_url: Optional[str] = None  # Full PostgreSQL URL (e.g. from Replit: postgresql://user:pass@host:port/db)
    cloud_sql_connection_name: Optional[str] = None  # Cloud SQL connection name (e.g., project:region:instance)
    database_user: Optional[str] = None  # Database user
    database_password: Optional[str] = None  # Database password (from Secret Manager in production)
    database_name: Optional[str] = None  # Database name
    database_host: Optional[str] = None  # Database host (for TCP connection, optional)
    database_port: int = 5432  # Database port (default PostgreSQL port)
    
    # CORS settings for frontend
    frontend_url: str = "http://localhost:5173"  # Vite default
    
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
    
    def is_admin(self, user_id: str = None, email: str = None) -> bool:
        """Check if a user is an admin."""
        admin_ids = [uid.strip() for uid in self.admin_user_ids.split(",") if uid.strip()]
        admin_emails_list = [e.strip().lower() for e in self.admin_emails.split(",") if e.strip()]
        
        if user_id and user_id in admin_ids:
            return True
        if email and email.lower() in admin_emails_list:
            return True
        return False
    
    @property
    def use_postgresql(self) -> bool:
        """Check if PostgreSQL should be used."""
        return bool(
            self.database_url
            or (self.cloud_sql_connection_name and self.database_user and self.database_name)
        )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

