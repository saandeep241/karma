"""
Langfuse observability client (v4).

Returns a configured Langfuse instance when LANGFUSE_PUBLIC_KEY and
LANGFUSE_SECRET_KEY are set; otherwise returns None so the app runs
identically without any keys configured.
"""

from functools import lru_cache
from typing import Optional


@lru_cache()
def get_langfuse():
    """Return a Langfuse client, or None if keys are not configured."""
    from app.config import get_settings
    settings = get_settings()

    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None

    try:
        from langfuse import Langfuse
        return Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception:
        return None
