"""
Karma Backend - FastAPI Application
A smart task suggestion system with multi-agent AI architecture.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.routes import tasks_router, suggestions_router, sessions_router
from app.routes.presentation import router as presentation_router
from app.database.connection import init_db, DATABASE_PATH
from app.auth import is_auth_enabled, CLERK_ENABLED
from app.logging_config import setup_logging, get_logger
from app.middleware import RequestLoggingMiddleware, SlowRequestLoggingMiddleware

# Initialize logging
setup_logging(level="DEBUG", log_to_file=True)
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    settings = get_settings()
    
    logger.info("=" * 60)
    logger.info(f"Starting {settings.app_name} - BACKEND API")
    logger.info("=" * 60)
    
    # Initialize database
    await init_db()
    logger.info(f"Database initialized: {DATABASE_PATH}")
    
    # Check AI mode
    if settings.is_ai_enabled:
        logger.info(f"AI MODE: ENABLED (model: {settings.openai_model})")
    else:
        logger.warning("DUMMY MODE: AI is disabled")
        if not settings.openai_karma.lower() == "true":
            logger.warning("Set OPENAI_KARMA=true to enable AI")
        if not settings.openai_api_key:
            logger.warning("Set OPENAI_API_KEY to your API key")
    
    logger.info(f"CORS enabled for: {settings.frontend_url}")
    
    # Check auth status
    if CLERK_ENABLED:
        logger.info("Authentication: ENABLED (Clerk)")
    else:
        logger.warning("Authentication: DISABLED (dev mode)")
    
    logger.info("=" * 60)
    logger.info("Karma Backend is ready to accept requests!")
    logger.info("=" * 60)
    
    yield
    
    logger.info("Shutting down Karma Backend")


app = FastAPI(
    title="Karma - Multi-Agent AI Task Suggestions API",
    description="Backend API for the Karma productivity app with multiple specialized AI agents",
    version="5.0.0",
    lifespan=lifespan
)

# Setup CORS for frontend
settings = get_settings()

# Build list of allowed origins
allowed_origins = [
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",  # Common React port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
]

# Add frontend URL from settings if it's set and not already in the list
if settings.frontend_url and settings.frontend_url not in allowed_origins:
    allowed_origins.append(settings.frontend_url)

# In production (Cloud Run), allow any *.run.app origin
import os
allow_origin_regex = None
if os.getenv("USE_CLOUD_STORAGE") == "true":  # Production indicator
    # Allow any Cloud Run URL (https://*.run.app)
    allow_origin_regex = r"https://.*\.run\.app"

logger.info(f"CORS allowed origins: {allowed_origins}")
if allow_origin_regex:
    logger.info(f"CORS allowed origin regex: {allow_origin_regex}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware (order matters - added after CORS)
app.add_middleware(SlowRequestLoggingMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Include routers
app.include_router(tasks_router)
app.include_router(suggestions_router)
app.include_router(sessions_router)
app.include_router(presentation_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": "Karma Backend API",
        "version": "5.0.0",
        "docs": "/docs",
        "health": "/api/health",
        "database": "SQLite"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "5.0.0 - SQLite Database",
        "ai_enabled": settings.is_ai_enabled,
        "dummy_mode": not settings.is_ai_enabled,
        "auth_enabled": CLERK_ENABLED,
        "database": "SQLite",
        "agents": [
            "TaskAnalyzer - Analyzes task properties",
            "TaskSuggester - Matches tasks to context",
            "TaskEnricher - Adds research & resources",
            "QuickWin - Generates micro-tasks",
            "Breakdown - Creates step-by-step plans with time estimates"
        ],
        "capabilities": [
            "sqlite_database",
            "multi_agent_orchestration",
            "specialized_agents",
            "persistent_memory",
            "learning_from_feedback",
            "reasoning_traces",
            "subtask_management",
            "time_estimates_per_subtask",
            "clerk_authentication"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
