"""
Karma Backend - FastAPI Application
A smart task suggestion system with multi-agent AI architecture.
"""

import re
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.config import get_settings
from app.routes import tasks_router, suggestions_router, sessions_router, onboarding_router
from app.routes.presentation import router as presentation_router
from app.database.connection import init_db, DATABASE_TYPE, DATABASE_PATH
from app.auth import is_auth_enabled, CLERK_ENABLED
from app.logging_config import setup_logging, get_logger
from app.middleware import (
    RequestLoggingMiddleware,
    SlowRequestLoggingMiddleware,
    CORSSafetyNetMiddleware,
)

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
    from app.database.connection import DATABASE_TYPE, DATABASE_PATH
    if DATABASE_PATH:
        logger.info(f"Database initialized: {DATABASE_TYPE} at {DATABASE_PATH}")
    else:
        logger.info(f"Database initialized: {DATABASE_TYPE} (Cloud SQL)")
    
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

# Add frontend URL from settings (with and without trailing slash for browser variance)
if settings.frontend_url:
    base = settings.frontend_url.rstrip("/")
    for url in (base, base + "/"):
        if url not in allowed_origins:
            allowed_origins.append(url)

import os
# Always allow *.replit.app for Replit deployments
allow_origin_regex = r"https://.*\.replit\.app"
# Also allow *.run.app when running on Google Cloud Run
if os.getenv("K_SERVICE") or os.getenv("USE_CLOUD_STORAGE") == "true":
    allow_origin_regex = r"https://(.*\.replit\.app|.*\.run\.app)"

logger.info(f"CORS allowed origins: {allowed_origins}")
if allow_origin_regex:
    logger.info(f"CORS allowed origin regex: {allow_origin_regex}")


def _is_origin_allowed(origin: str | None) -> bool:
    """Check if an Origin header value is allowed by CORS config."""
    if not origin or not origin.strip():
        return False
    origin = origin.strip()
    if origin in allowed_origins:
        return True
    if allow_origin_regex and re.match(allow_origin_regex, origin):
        return True
    # Trailing slash variant (browsers sometimes send with or without)
    normalized = origin.rstrip("/") if origin.endswith("/") else origin + "/"
    if normalized in allowed_origins:
        return True
    return False


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
# Safety net: ensure CORS headers on every response (e.g. 401, 404, 500)
app.add_middleware(
    CORSSafetyNetMiddleware,
    allowed_origins=allowed_origins,
    allow_origin_regex=allow_origin_regex,
)

# Include routers
app.include_router(tasks_router)
app.include_router(suggestions_router)
app.include_router(sessions_router)
app.include_router(onboarding_router)
app.include_router(presentation_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Ensure 500 (and any unhandled) responses include CORS headers so the
    browser does not report a CORS error when the real issue is a server error.
    """
    logger.exception("Unhandled exception: %s", exc)
    content = {"detail": "Internal server error", "type": type(exc).__name__}
    headers = {}
    origin = request.headers.get("origin") or request.headers.get("Origin")
    if origin and _is_origin_allowed(origin):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Vary"] = "Origin"
    return JSONResponse(status_code=500, content=content, headers=headers)



@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    from app.database.connection import DATABASE_TYPE
    settings = get_settings()
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": f"5.0.0 - {DATABASE_TYPE} Database",
        "ai_enabled": settings.is_ai_enabled,
        "dummy_mode": not settings.is_ai_enabled,
        "auth_enabled": CLERK_ENABLED,
        "database": DATABASE_TYPE,
        "cors": {
            "allowed_origins": allowed_origins,
            "allow_origin_regex": allow_origin_regex,
        },
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


FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(str(FRONTEND_DIST / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
