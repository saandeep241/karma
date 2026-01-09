"""
Karma Backend - FastAPI Application
A smart task suggestion system with multi-agent AI architecture.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.routes import tasks_router, suggestions_router, sessions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    settings = get_settings()
    print(f"\n🚀 Starting {settings.app_name} - BACKEND API")
    print("=" * 60)
    
    # Check AI mode
    if settings.is_ai_enabled:
        print("✅ AI MODE: ENABLED (OPENAI_KARMA=true)")
        print(f"   Model: {settings.openai_model}")
    else:
        print("⚠️  DUMMY MODE: AI is disabled")
        if not settings.openai_karma.lower() == "true":
            print("   → Set OPENAI_KARMA=true to enable AI")
        if not settings.openai_api_key:
            print("   → Set OPENAI_API_KEY to your API key")
        print("   → All agents will return dummy data marked with [Dummy]")
    
    print(f"🌐 CORS enabled for: {settings.frontend_url}")
    print("📁 Data directories:")
    print("   - Tasks: data/tasks/")
    print("   - Reasoning: data/reasoning/")
    print("   - Memory: data/memory/")
    print("=" * 60)
    yield
    print("👋 Shutting down Karma Backend")


app = FastAPI(
    title="Karma - Multi-Agent AI Task Suggestions API",
    description="Backend API for the Karma productivity app with multiple specialized AI agents",
    version="4.0.0",
    lifespan=lifespan
)

# Setup CORS for frontend
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",  # Common React port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tasks_router)
app.include_router(suggestions_router)
app.include_router(sessions_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": "Karma Backend API",
        "version": "4.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "4.0.0 - Multi-Agent AI Backend",
        "ai_enabled": settings.is_ai_enabled,
        "dummy_mode": not settings.is_ai_enabled,
        "agents": [
            "TaskAnalyzer - Analyzes task properties",
            "TaskSuggester - Matches tasks to context",
            "TaskEnricher - Adds research & resources",
            "QuickWin - Generates micro-tasks",
            "Breakdown - Creates step-by-step plans with time estimates"
        ],
        "capabilities": [
            "multi_agent_orchestration",
            "specialized_agents",
            "persistent_memory",
            "learning_from_feedback",
            "reasoning_traces",
            "subtask_management",
            "time_estimates_per_subtask",
            "dummy_mode_fallback"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

