"""Configuration settings for the Karma backend."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI settings
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    
    # Karma AI toggle - set to "true" to use real AI, otherwise uses dummy mode
    openai_karma: str = ""  # Set OPENAI_KARMA=true to enable AI
    
    # App settings
    app_name: str = "Karma - Smart Task Suggestions"
    debug: bool = False
    
    # CORS settings for frontend
    frontend_url: str = "http://localhost:5173"  # Vite default
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @property
    def is_ai_enabled(self) -> bool:
        """Check if AI is enabled (OPENAI_KARMA=true and API key exists)."""
        return self.openai_karma.lower() == "true" and bool(self.openai_api_key)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

