"""API Routes."""

from .tasks import router as tasks_router
from .suggestions import router as suggestions_router
from .sessions import router as sessions_router
from .onboarding import router as onboarding_router

__all__ = ["tasks_router", "suggestions_router", "sessions_router", "onboarding_router"]

