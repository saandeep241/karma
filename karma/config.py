"""Configuration settings for the Karma app."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI settings
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    
    # App settings
    app_name: str = "Karma - Smart Task Suggestions"
    debug: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

