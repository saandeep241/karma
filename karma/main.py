"""
Karma - Smart Task Suggestions (Multi-Agent AI Version)
A FastAPI application with multiple specialized AI agents.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import Optional
import os

from config import get_settings
from models import (
    Task, TodoList, UserContext, TaskSuggestion,
    ImportTodoListRequest, ImportTodoListResponse,
    SetContextRequest, GetSuggestionRequest, SuggestionResponse,
    AcceptTaskRequest, AcceptTaskResponse, RequestAlternativeRequest,
    TimeAvailable, EnergyLevel, EmotionalState
)
from session_store import session_store
from agents import karma_orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    settings = get_settings()
    print(f"\n🚀 Starting {settings.app_name} - MULTI-AGENT AI VERSION")
    print("=" * 60)
    if not settings.openai_api_key:
        print("⚠️  No OpenAI API key configured - agents will not work")
    else:
        print("✅ OpenAI API configured - All agents enabled")
    print("📁 Data directories:")
    print("   - Tasks: data/tasks/")
    print("   - Reasoning: data/reasoning/")
    print("   - Memory: data/memory/")
    print("=" * 60)
    yield
    print("👋 Shutting down Karma Agents")


app = FastAPI(
    title="Karma - Multi-Agent AI Task Suggestions",
    description="Multiple specialized AI agents that help users make productive use of small time blocks",
    version="3.0.0",
    lifespan=lifespan
)

# Setup templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
static_dir = os.path.join(os.path.dirname(__file__), "static")

os.makedirs(templates_dir, exist_ok=True)
os.makedirs(static_dir, exist_ok=True)

templates = Jinja2Templates(directory=templates_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ============================================================================
# Frontend Routes
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main application page."""
    return templates.TemplateResponse("index.html", {"request": request})


# ============================================================================
# API Routes
# ============================================================================

@app.post("/api/session/create")
async def create_session():
    """Create a new session."""
    session = session_store.create_session()
    return {"session_id": session.id, "message": "Session created successfully"}


@app.post("/api/todo/import", response_model=ImportTodoListResponse)
async def import_todo_list(request: ImportTodoListRequest):
    """
    Import a todo list from text content.
    Uses TaskAnalyzer and TaskEnricher agents to process tasks.
    """
    session = session_store.create_session()
    
    # Parse tasks from text
    lines = [line.strip() for line in request.text_content.strip().split("\n")]
    tasks = [Task(text=line) for line in lines if line and not line.startswith("#")]
    
    if not tasks:
        raise HTTPException(
            status_code=400,
            detail="No valid tasks found in the provided text"
        )
    
    print("\n" + "=" * 60)
    print("🤖 ORCHESTRATOR: Processing imported tasks...")
    print(f"   Using agents: TaskAnalyzer, TaskEnricher")
    print("=" * 60)
    
    # Use orchestrator to analyze and enrich tasks
    analyzed_tasks, reasoning_trace = await karma_orchestrator.analyze_tasks(tasks)
    
    print(f"\n✅ Orchestrator: Processed {len(analyzed_tasks)} tasks")
    
    # Create todo list and attach to session
    todo_list = TodoList(tasks=analyzed_tasks)
    session.todo_list = todo_list
    session.agent_reasoning = reasoning_trace
    session_store.update_session(session)
    
    return ImportTodoListResponse(
        session_id=session.id,
        tasks_imported=len(analyzed_tasks),
        tasks=analyzed_tasks
    )


@app.post("/api/context/set")
async def set_user_context(request: SetContextRequest):
    """Set the user's current context."""
    session = session_store.get_session(request.session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    context = UserContext(
        time_available=request.time_available,
        energy_level=request.energy_level,
        emotional_state=request.emotional_state
    )
    
    session.context = context
    session_store.update_session(session)
    
    return {
        "message": "Context set successfully",
        "context": {
            "time_available": context.time_available.value,
            "energy_level": context.energy_level.value,
            "emotional_state": context.emotional_state.value if context.emotional_state else None
        }
    }


class SuggestFromStorageRequest(BaseModel):
    """Request to get suggestion directly from stored tasks."""
    time_available: int
    energy_level: str
    emotional_state: Optional[str] = None
    excluded_task_ids: list[str] = []


@app.post("/api/suggestion/from-storage")
async def get_suggestion_from_storage(request: SuggestFromStorageRequest):
    """Get a task suggestion directly from stored tasks without re-importing."""
    from tools import get_all_tasks_by_date
    from models import Task, UserContext, TaskSuggestion
    
    print("\n" + "=" * 60)
    print("🤖 ORCHESTRATOR: Finding best task from storage...")
    print(f"   Time: {request.time_available}min, Energy: {request.energy_level}")
    print("=" * 60)
    
    # Load all tasks from storage
    tasks_by_date = get_all_tasks_by_date()
    
    # Collect pending tasks
    all_tasks = []
    for date, date_data in tasks_by_date.items():
        for task_data in date_data.get("tasks", []):
            if task_data.get("status") in ["pending", "in_progress"]:
                # Convert to Task object
                task = Task(
                    id=task_data.get("id"),
                    text=task_data.get("text"),
                    estimated_minutes=task_data.get("estimated_minutes"),
                    energy_required=task_data.get("energy_required"),
                    category=task_data.get("category"),
                    tags=task_data.get("tags", []),
                    status=task_data.get("status", "pending")
                )
                all_tasks.append(task)
    
    if not all_tasks:
        # No tasks - use QuickWin agent
        context = UserContext(
            time_available=TimeAvailable(request.time_available),
            energy_level=EnergyLevel(request.energy_level)
        )
        quickwin = await karma_orchestrator.generate_quickwin(context)
        
        quickwin_task = Task(
            text=quickwin["text"],
            estimated_minutes=quickwin["estimated_minutes"]
        )
        
        suggestion = TaskSuggestion(
            task=quickwin_task,
            reasoning=quickwin["reasoning"],
            confidence_score=1.0,
            is_generic_quickwin=True
        )
        
        return {
            "session_id": "quickwin",
            "suggestion": suggestion.model_dump(),
            "alternatives_available": True,
            "message": "No pending tasks. Here's a quick activity!"
        }
    
    # Create context
    context = UserContext(
        time_available=TimeAvailable(request.time_available),
        energy_level=EnergyLevel(request.energy_level),
        emotional_state=EmotionalState(request.emotional_state) if request.emotional_state else None
    )
    
    # Create/update session
    session = session_store.create_session()
    session.context = context
    session.todo_list = TodoList(tasks=all_tasks)
    session.suggested_task_ids = request.excluded_task_ids
    session_store.update_session(session)
    
    # Get suggestion
    suggestion, reasoning_trace = await karma_orchestrator.suggest_task(
        tasks=all_tasks,
        context=context,
        excluded_task_ids=request.excluded_task_ids
    )
    
    if not suggestion:
        # No matching tasks - use QuickWin
        quickwin = await karma_orchestrator.generate_quickwin(context)
        
        quickwin_task = Task(
            text=quickwin["text"],
            estimated_minutes=quickwin["estimated_minutes"]
        )
        
        suggestion = TaskSuggestion(
            task=quickwin_task,
            reasoning=quickwin["reasoning"],
            confidence_score=1.0,
            is_generic_quickwin=True
        )
        
        return {
            "session_id": session.id,
            "suggestion": suggestion.model_dump(),
            "alternatives_available": True,
            "message": "No tasks match your context. Here's a quick activity!"
        }
    
    # Track suggested task
    session.suggested_task_ids.append(suggestion.task.id)
    session.current_task = suggestion.task
    session.current_reasoning = suggestion.reasoning
    session_store.update_session(session)
    
    # Check alternatives
    remaining_tasks = [t for t in all_tasks if t.id not in session.suggested_task_ids]
    
    print(f"\n✅ TaskSuggester: Suggested '{suggestion.task.text}'")
    
    return {
        "session_id": session.id,
        "suggestion": suggestion.model_dump(),
        "alternatives_available": len(remaining_tasks) > 0,
        "message": f"Based on your {request.time_available} minutes and {request.energy_level} energy:"
    }


@app.post("/api/suggestion/get")
async def get_task_suggestion(request: GetSuggestionRequest):
    """Get a task suggestion using the TaskSuggester agent."""
    session = session_store.get_session(request.session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.context:
        raise HTTPException(
            status_code=400,
            detail="User context not set. Please set time and energy level first."
        )
    
    print("\n" + "=" * 60)
    print("🤖 ORCHESTRATOR: Finding best task suggestion...")
    print(f"   Using agent: TaskSuggester")
    print("=" * 60)
    
    # Check if user has tasks
    if not session.todo_list or not session.todo_list.tasks:
        # Use QuickWin agent instead
        print("   No tasks available - delegating to QuickWin agent")
        quickwin = await karma_orchestrator.generate_quickwin(session.context)
        
        quickwin_task = Task(
            text=quickwin["text"],
            estimated_minutes=quickwin["estimated_minutes"]
        )
        
        suggestion = TaskSuggestion(
            task=quickwin_task,
            reasoning=quickwin["reasoning"],
            confidence_score=1.0,
            is_generic_quickwin=True
        )
        
        return {
            "suggestion": suggestion.model_dump(),
            "alternatives_available": True,
            "message": "You don't have any tasks imported. Here's a quick activity!",
            "agent_reasoning": f"QuickWin Agent: {quickwin['reasoning']}"
        }
    
    # Get suggestion with reasoning
    suggestion, reasoning_trace = await karma_orchestrator.suggest_task(
        tasks=session.todo_list.tasks,
        context=session.context,
        excluded_task_ids=session.suggested_task_ids
    )
    
    if not suggestion:
        # No matching tasks - use QuickWin agent
        print("   No matching tasks - delegating to QuickWin agent")
        quickwin = await karma_orchestrator.generate_quickwin(session.context)
        
        quickwin_task = Task(
            text=quickwin["text"],
            estimated_minutes=quickwin["estimated_minutes"]
        )
        
        suggestion = TaskSuggestion(
            task=quickwin_task,
            reasoning=quickwin["reasoning"],
            confidence_score=1.0,
            is_generic_quickwin=True
        )
        
        return {
            "suggestion": suggestion.model_dump(),
            "alternatives_available": True,
            "message": "No more tasks match your context. Here's a quick activity!",
            "agent_reasoning": f"QuickWin Agent: {quickwin['reasoning']}"
        }
    
    # Track suggested task
    session.suggested_task_ids.append(suggestion.task.id)
    session.current_task = suggestion.task
    session.current_reasoning = suggestion.reasoning
    session_store.update_session(session)
    
    # Check alternatives
    remaining_tasks = [
        t for t in session.todo_list.tasks 
        if t.id not in session.suggested_task_ids
    ]
    
    print(f"\n✅ TaskSuggester: Suggested '{suggestion.task.text}'")
    print(f"📊 Confidence: {suggestion.confidence_score:.0%}")
    
    return {
        "suggestion": suggestion.model_dump(),
        "alternatives_available": len(remaining_tasks) > 0,
        "message": f"Based on your {session.context.time_available.value} minutes and {session.context.energy_level.value} energy:",
        "agent_reasoning": f"TaskSuggester: {suggestion.reasoning}"
    }


@app.post("/api/suggestion/alternative")
async def get_alternative_suggestion(request: RequestAlternativeRequest):
    """Request an alternative task suggestion."""
    session = session_store.get_session(request.session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Record rejection feedback
    if session.current_task and session.context:
        print("\n📝 Recording rejection feedback for learning...")
        karma_orchestrator.record_feedback(
            task=session.current_task,
            context=session.context,
            accepted=False,
            reasoning=session.current_reasoning or ""
        )
    
    return await get_task_suggestion(GetSuggestionRequest(session_id=request.session_id))


@app.post("/api/task/accept")
async def accept_task(request: AcceptTaskRequest):
    """Accept a suggested task and get the breakdown from Breakdown agent."""
    session = session_store.get_session(request.session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.context:
        raise HTTPException(status_code=400, detail="User context not set")
    
    # Find the task
    task = None
    if session.current_task and session.current_task.id == request.task_id:
        task = session.current_task
    elif session.todo_list:
        task = next(
            (t for t in session.todo_list.tasks if t.id == request.task_id),
            None
        )
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    print("\n" + "=" * 60)
    print("🤖 ORCHESTRATOR: Breaking down accepted task...")
    print(f"   Using agent: Breakdown")
    print("=" * 60)
    
    # Record acceptance feedback
    karma_orchestrator.record_feedback(
        task=task,
        context=session.context,
        accepted=True,
        reasoning=session.current_reasoning or ""
    )
    
    # Break task into steps with reasoning
    breakdown, reasoning_trace = await karma_orchestrator.break_task_into_steps(
        task=task,
        time_available=session.context.time_available.value
    )
    
    session.current_task = task
    session.current_breakdown = breakdown
    session_store.update_session(session)
    
    print(f"\n✅ Breakdown Agent: Created {breakdown.total_steps} steps")
    
    return {
        "task": task.model_dump(),
        "breakdown": breakdown.model_dump(),
        "first_step": breakdown.steps[0].model_dump(),
        "message": "Great choice! Here's your first step:",
        "agent_reasoning": f"Breakdown Agent: Created {breakdown.total_steps} actionable steps"
    }


@app.get("/api/task/steps/{session_id}")
async def get_task_steps(session_id: str):
    """Get all steps for the current task."""
    session = session_store.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.current_breakdown:
        raise HTTPException(status_code=400, detail="No task has been accepted yet")
    
    return {
        "task": session.current_task.model_dump() if session.current_task else None,
        "breakdown": session.current_breakdown.model_dump(),
        "total_steps": session.current_breakdown.total_steps
    }


@app.get("/api/agent/reasoning/{session_id}")
async def get_agent_reasoning(session_id: str):
    """Get the agent's full reasoning trace for this session."""
    session = session_store.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "reasoning": getattr(session, 'agent_reasoning', {}),
        "current_reasoning": getattr(session, 'current_reasoning', '')
    }


@app.get("/api/agent/insights")
async def get_agent_insights():
    """Get learning insights from all agents."""
    insights = karma_orchestrator.get_learning_insights()
    return {
        "insights": insights,
        "message": "Learning insights from agent interactions",
        "agents": ["TaskAnalyzer", "TaskSuggester", "TaskEnricher", "QuickWin", "Breakdown"]
    }


# ============================================================================
# Task Management Routes
# ============================================================================

@app.get("/api/tasks/all")
async def get_all_tasks():
    """Get all tasks organized by date."""
    from tools import get_all_tasks_by_date, get_task_stats
    
    tasks_by_date = get_all_tasks_by_date()
    stats = get_task_stats()
    return {
        "tasks_by_date": tasks_by_date,
        "total_dates": len(tasks_by_date),
        "stats": stats
    }


@app.get("/api/tasks/stats")
async def get_stats():
    """Get overall task statistics for UI badges."""
    from tools import get_task_stats
    
    stats = get_task_stats()
    return stats


@app.get("/api/tasks/date/{date}")
async def get_tasks_by_date(date: str):
    """Get tasks for a specific date."""
    from tools import load_tasks
    
    data = load_tasks(date)
    return data


@app.get("/api/tasks/{task_id}")
async def get_task_detail(task_id: str):
    """Get full details for a specific task including enrichment."""
    from tools import get_task_details, get_task_enrichment
    
    task = get_task_details(task_id)
    if "error" in task:
        raise HTTPException(status_code=404, detail=task["error"])
    
    # Also get enrichment if available
    enrichment = get_task_enrichment(task_id)
    if "error" not in enrichment:
        task["enrichment"] = enrichment
    
    return task


@app.put("/api/tasks/{task_id}/status")
async def update_task_status_endpoint(task_id: str, status: str, date: str = None):
    """Update a task's status."""
    from tools import update_task_status
    
    valid_statuses = ["pending", "in_progress", "completed", "skipped"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    result = update_task_status(task_id, status, date)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Failed to update"))
    return result


@app.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: str):
    """Mark a task as completed."""
    from tools import update_task_status
    
    result = update_task_status(task_id, "completed")
    return result


# ============================================================================
# Task Action Routes (for starting tasks from browse view)
# ============================================================================

from pydantic import BaseModel

class TaskBreakdownRequest(BaseModel):
    """Request to break down a task into steps."""
    session_id: str
    task_id: str
    task_text: str


class TaskStatusRequest(BaseModel):
    """Request to update task status."""
    task_id: str
    status: str


@app.post("/api/task/breakdown")
async def breakdown_task_from_browse(request: TaskBreakdownRequest):
    """Break down a task into steps (called from browse view)."""
    from tools import get_task_details
    from models import Task, TaskBreakdown
    
    # Get or create session
    session = session_store.get_session(request.session_id)
    if not session:
        # Create a minimal session for this operation
        from models import Session, UserContext, TimeAvailable, EnergyLevel
        session = Session(id=request.session_id)
        session.context = UserContext(
            time_available=TimeAvailable.THIRTY,
            energy_level=EnergyLevel.MEDIUM
        )
        session_store.update_session(session)
    
    # Get task details
    task_data = get_task_details(request.task_id)
    if "error" in task_data:
        # Create task from text if not found
        task = Task(id=request.task_id, text=request.task_text)
    else:
        task = Task(**{k: v for k, v in task_data.items() if k in Task.model_fields})
    
    print("\n" + "=" * 60)
    print("🤖 ORCHESTRATOR: Breaking down task from browse view...")
    print(f"   Task: {task.text}")
    print(f"   Using agent: Breakdown")
    print("=" * 60)
    
    # Get time from context or default to 30 min
    time_available = 30
    if session.context:
        time_available = session.context.time_available.value
    
    # Break task into steps
    breakdown, reasoning_trace = await karma_orchestrator.break_task_into_steps(
        task=task,
        time_available=time_available
    )
    
    session.current_task = task
    session.current_breakdown = breakdown
    session_store.update_session(session)
    
    print(f"\n✅ Breakdown Agent: Created {breakdown.total_steps} steps")
    
    return {
        "task": task.model_dump(),
        "breakdown": breakdown.model_dump(),
        "first_step": breakdown.steps[0].model_dump(),
        "message": "Here's your task broken down into steps:",
        "agent_reasoning": f"Breakdown Agent: Created {breakdown.total_steps} actionable steps"
    }


@app.post("/api/task/status")
async def update_task_status_post(request: TaskStatusRequest):
    """Update task status (POST version for easier frontend calls)."""
    from tools import update_task_status
    
    valid_statuses = ["pending", "in_progress", "completed", "skipped"]
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    result = update_task_status(request.task_id, request.status)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Failed to update"))
    return result


class ReResearchRequest(BaseModel):
    """Request to re-research a task with optional correction."""
    task_id: str
    task_text: str
    correction_type: Optional[str] = None
    correction_text: Optional[str] = None


@app.post("/api/task/reresearch")
async def reresearch_task(request: ReResearchRequest):
    """Re-research a task, optionally with user correction/feedback."""
    from tools import get_task_details, save_task_with_details
    from models import Task
    from datetime import datetime
    
    print("\n" + "=" * 60)
    print("🤖 ORCHESTRATOR: Re-researching task with user feedback...")
    print(f"   Task: {request.task_text}")
    if request.correction_text:
        print(f"   Correction type: {request.correction_type}")
        print(f"   User feedback: {request.correction_text[:100]}...")
    print(f"   Using agent: TaskEnricher")
    print("=" * 60)
    
    # Get existing task or create new one
    task_data = get_task_details(request.task_id)
    if "error" in task_data:
        task = Task(id=request.task_id, text=request.task_text)
    else:
        task = Task(**{k: v for k, v in task_data.items() if k in Task.model_fields})
    
    # Build enhanced prompt with user correction
    enhanced_task_text = request.task_text
    if request.correction_text:
        enhanced_task_text = f"{request.task_text}\n\nIMPORTANT USER CORRECTION ({request.correction_type or 'general'}): {request.correction_text}"
    
    # Create a temporary task with enhanced text for enrichment
    temp_task = Task(id=task.id, text=enhanced_task_text)
    
    # Re-enrich with the correction context
    enrichment = await karma_orchestrator.enrich_task(temp_task)
    
    # Save correction to memory for future learning
    if request.correction_text:
        from tools import save_reasoning
        save_reasoning({
            "type": "user_correction",
            "task_id": request.task_id,
            "task_text": request.task_text,
            "correction_type": request.correction_type,
            "correction_text": request.correction_text,
            "timestamp": datetime.now().isoformat()
        }, "user_correction")
        print(f"📝 Saved user correction for future learning")
    
    # Update task with new enrichment
    task.enrichment = enrichment
    today = datetime.now().strftime("%Y-%m-%d")
    save_task_with_details(task.model_dump(), today)
    
    print(f"\n✅ TaskEnricher: Re-researched with {len(enrichment.get('steps', []))} steps")
    
    return {
        "task_id": request.task_id,
        "enrichment": enrichment,
        "message": "Task re-researched successfully!",
        "used_correction": bool(request.correction_text)
    }


@app.delete("/api/tasks/delete-all")
async def delete_all_tasks():
    """Delete all tasks - DANGER ZONE."""
    from tools import TASKS_DIR, TASK_DETAILS_DIR
    import shutil
    
    print("\n" + "=" * 60)
    print("⚠️  DELETING ALL TASKS...")
    print("=" * 60)
    
    deleted_count = 0
    
    try:
        # Delete all task files
        if TASKS_DIR.exists():
            for file in TASKS_DIR.glob("*.json"):
                file.unlink()
                deleted_count += 1
            print(f"   Deleted {deleted_count} date files from tasks/")
        
        # Delete all task detail files
        detail_count = 0
        if TASK_DETAILS_DIR.exists():
            for file in TASK_DETAILS_DIR.glob("*.json"):
                file.unlink()
                detail_count += 1
            print(f"   Deleted {detail_count} files from task_details/")
        
        print("✅ All tasks deleted successfully")
        
        return {
            "success": True,
            "deleted_task_files": deleted_count,
            "deleted_detail_files": detail_count,
            "message": "All tasks have been deleted"
        }
        
    except Exception as e:
        print(f"❌ Error deleting tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/options")
async def get_options():
    """Get available options for time, energy, and emotional state."""
    return {
        "time_options": [
            {"value": t.value, "label": f"{t.value} minutes"} 
            for t in TimeAvailable
        ],
        "energy_options": [
            {"value": e.value, "label": e.value.capitalize()} 
            for e in EnergyLevel
        ],
        "emotional_options": [
            {"value": e.value, "label": e.value.capitalize()} 
            for e in EmotionalState
        ]
    }


class CompleteQuickWinRequest(BaseModel):
    """Request to mark a quick win as completed."""
    text: str
    category: str = "quickwin"
    estimated_minutes: int = 5


@app.post("/api/quickwin/complete")
async def complete_quickwin(request: CompleteQuickWinRequest):
    """Save a completed quick win as a task."""
    from tools import save_task_with_details
    from datetime import datetime
    import uuid
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    task_data = {
        "id": str(uuid.uuid4()),
        "text": request.text,
        "status": "completed",
        "category": request.category.lower() if request.category else "quickwin",
        "tags": ["quick-win"],
        "created_at": datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat(),
        "estimated_minutes": request.estimated_minutes,
        "energy_required": "low",
        "task_type": "quick_win"
    }
    
    save_task_with_details(task_data, today)
    
    print(f"✅ Quick win completed and saved: {request.text[:50]}...")
    
    return {
        "success": True,
        "task_id": task_data["id"],
        "message": "Quick win saved as completed task!"
    }


@app.post("/api/quickwin")
async def get_ai_quickwin(request: dict = None):
    """Get an AI-generated quick win from the QuickWin agent."""
    try:
        # Get context from request or use defaults
        time_available = request.get("time_available", 10) if request else 10
        energy_level = request.get("energy_level", "medium") if request else "medium"
        mood = request.get("mood", "neutral") if request else "neutral"
        
        # Create context
        context = UserContext(
            time_available=TimeAvailable(time_available),
            energy_level=EnergyLevel(energy_level),
            emotional_state=EmotionalState(mood) if mood else None
        )
        
        print("\n" + "=" * 60)
        print("🤖 ORCHESTRATOR: Generating quick win...")
        print(f"   Using agent: QuickWin")
        print("=" * 60)
        
        # Get AI-generated quick win
        quickwin = await karma_orchestrator.generate_quickwin(context)
        
        return {
            "success": True,
            "quickwin": quickwin,
            "agent": "QuickWin"
        }
    except ValueError as e:
        # AI not configured - return error
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate quick win: {e}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "3.0.0 - Multi-Agent AI",
        "ai_enabled": bool(settings.openai_api_key),
        "agents": [
            "TaskAnalyzer - Analyzes task properties",
            "TaskSuggester - Matches tasks to context",
            "TaskEnricher - Adds research & resources",
            "QuickWin - Generates micro-tasks",
            "Breakdown - Creates step-by-step plans"
        ],
        "capabilities": [
            "multi_agent_orchestration",
            "specialized_agents",
            "persistent_memory",
            "learning_from_feedback",
            "reasoning_traces"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
