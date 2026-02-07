"""Suggestion and quick win routes."""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends

from app.models import (
    Task, TodoList, TaskSuggestion, UserContext,
    GetSuggestionRequest, SuggestFromStorageRequest,
    TimeAvailable, EnergyLevel, EmotionalState
)
from app.auth import require_auth, AuthUser
from app.services.session_store import session_store
from app.services import db_service
from app.agents import karma_orchestrator
from app.logging_config import get_api_logger

logger = get_api_logger()

router = APIRouter(prefix="/api", tags=["suggestions"])


@router.post("/suggestion/from-storage")
async def get_suggestion_from_storage(request: SuggestFromStorageRequest, user: AuthUser = Depends(require_auth)):
    """Get a task suggestion directly from stored tasks without re-importing.
    
    If a task has subtasks, suggests the next pending subtask.
    Otherwise suggests the full task.
    """
    logger.info(f"Getting suggestion from storage (time: {request.time_available}min, energy: {request.energy_level})")
    
    # Load all tasks from storage for this user
    tasks_by_date = await db_service.get_all_tasks_by_date(user.user_id)
    
    # Collect ALL pending tasks (with and without subtasks) to send to agent
    all_tasks = []
    
    for date, date_data in tasks_by_date.items():
        for task_data in date_data.get("tasks", []):
            task_status = task_data.get("status", "pending")
            
            # Only include pending or in_progress tasks
            if task_status not in ["pending", "in_progress"]:
                continue
            
            # Convert subtasks from dict to Subtask models
            subtasks_data = task_data.get("subtasks", [])
            subtasks = []
            for st_data in subtasks_data:
                from app.models import Subtask, SubtaskStatus
                
                # Parse datetime safely
                started_at = None
                completed_at = None
                if st_data.get("started_at"):
                    try:
                        if isinstance(st_data["started_at"], str):
                            started_at = datetime.fromisoformat(st_data["started_at"].replace('Z', '+00:00'))
                        else:
                            started_at = st_data["started_at"]
                    except (ValueError, AttributeError):
                        started_at = None
                
                if st_data.get("completed_at"):
                    try:
                        if isinstance(st_data["completed_at"], str):
                            completed_at = datetime.fromisoformat(st_data["completed_at"].replace('Z', '+00:00'))
                        else:
                            completed_at = st_data["completed_at"]
                    except (ValueError, AttributeError):
                        completed_at = None
                
                subtask = Subtask(
                    id=st_data.get("id", ""),
                    step_number=st_data.get("order", 0),
                    instruction=st_data.get("instruction") or st_data.get("text", ""),
                    estimated_minutes=st_data.get("estimated_minutes", 5),
                    status=SubtaskStatus(st_data.get("status", "pending")),
                    started_at=started_at,
                    completed_at=completed_at,
                    ai_reasoning=st_data.get("ai_reasoning")
                )
                subtasks.append(subtask)
            
            # Create Task model with all information including subtasks
            task = Task(
                id=task_data.get("id"),
                text=task_data.get("text"),
                estimated_minutes=task_data.get("estimated_minutes"),
                energy_required=task_data.get("energy_required"),
                category=task_data.get("category"),
                tags=task_data.get("tags", []),
                status=task_status,
                subtasks=subtasks,
                subtasks_generated=task_data.get("subtasks_generated", False)
            )
            all_tasks.append(task)
    
    if not all_tasks:
        # No tasks - use QuickWin agent
        context = UserContext(
            time_available=TimeAvailable(request.time_available),
            energy_level=EnergyLevel(request.energy_level)
        )
        quickwin = await karma_orchestrator.generate_quickwin(context, user_id=user.user_id)
        
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
            "suggestion": suggestion.model_dump(by_alias=False),
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
    session = session_store.create_session(user.user_id)
    session.context = context
    session.todo_list = TodoList(tasks=all_tasks)
    session.suggested_task_ids = request.excluded_task_ids
    session_store.update_session(session)
    
    # Get suggestion from agent - now includes ALL tasks with subtask information
    suggestion, reasoning_trace = await karma_orchestrator.suggest_task(
        tasks=all_tasks,
        context=context,
        excluded_task_ids=request.excluded_task_ids,
        user_id=user.user_id
    )
    
    if not suggestion:
        # No matching tasks - use QuickWin
        quickwin = await karma_orchestrator.generate_quickwin(context, user_id=user.user_id)
        
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
            "suggestion": suggestion.model_dump(by_alias=False),
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
    
    # Build response with subtask information if applicable
    response_data = {
        "session_id": session.id,
        "suggestion": suggestion.model_dump(by_alias=False),
        "alternatives_available": len(remaining_tasks) > 0,
        "message": f"Based on your {request.time_available} minutes and {request.energy_level} energy:"
    }
    
    # Add subtask info if this is a subtask suggestion
    if suggestion.suggested_subtask:
        response_data["has_subtask"] = True
        response_data["next_subtask"] = suggestion.suggested_subtask.model_dump(by_alias=False)
        if suggestion.subtask_instruction:
            response_data["subtask_instruction"] = suggestion.subtask_instruction
        if suggestion.subtask_estimated_minutes:
            response_data["subtask_estimated_minutes"] = suggestion.subtask_estimated_minutes
    
    return response_data


@router.post("/suggestion/get")
async def get_task_suggestion(request: GetSuggestionRequest, user: AuthUser = Depends(require_auth)):
    """Get a task suggestion using the TaskSuggester agent."""
    session = session_store.get_session(user.user_id, request.session_id)
    
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
        quickwin = await karma_orchestrator.generate_quickwin(session.context, user_id=user.user_id)
        
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
            "suggestion": suggestion.model_dump(by_alias=False),
            "alternatives_available": True,
            "message": "You don't have any tasks imported. Here's a quick activity!",
            "agent_reasoning": f"QuickWin Agent: {quickwin['reasoning']}"
        }
    
    # Get suggestion with reasoning
    suggestion, reasoning_trace = await karma_orchestrator.suggest_task(
        tasks=session.todo_list.tasks,
        context=session.context,
        excluded_task_ids=session.suggested_task_ids,
        user_id=user.user_id
    )
    
    if not suggestion:
        # No matching tasks - use QuickWin agent
        print("   No matching tasks - delegating to QuickWin agent")
        quickwin = await karma_orchestrator.generate_quickwin(session.context, user_id=user.user_id)
        
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
            "suggestion": suggestion.model_dump(by_alias=False),
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
        "suggestion": suggestion.model_dump(by_alias=False),
        "alternatives_available": len(remaining_tasks) > 0,
        "message": f"Based on your {session.context.time_available.value} minutes and {session.context.energy_level.value} energy:",
        "agent_reasoning": f"TaskSuggester: {suggestion.reasoning}"
    }


@router.post("/quickwin")
async def post_ai_quickwin(request: dict = None, user: AuthUser = Depends(require_auth)):
    """Get an AI-generated quick win from the QuickWin agent (POST version)."""
    return await _generate_quickwin(request, user.user_id)


@router.get("/quickwin/get")
async def get_ai_quickwin(user: AuthUser = Depends(require_auth)):
    """Get an AI-generated quick win from the QuickWin agent (GET version)."""
    return await _generate_quickwin(None, user.user_id)


async def _generate_quickwin(request: dict = None, user_id: str = None):
    """Internal helper to generate a quick win."""
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
        quickwin = await karma_orchestrator.generate_quickwin(context, user_id=user_id)
        
        # Record quickwin shown to user (if user_id provided)
        if user_id:
            await db_service.record_quickwin_shown(
                user_id,
                quickwin["text"],
                quickwin.get("category", "other"),
                was_added=False
            )
        
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


@router.get("/options")
async def get_options(user: AuthUser = Depends(require_auth)):
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


@router.get("/agent/insights")
async def get_agent_insights(user: AuthUser = Depends(require_auth)):
    """Get learning insights from all agents for the authenticated user."""
    insights = await db_service.get_learning_insights(user.user_id)
    return {
        "insights": insights,
        "message": "Learning insights from agent interactions",
        "agents": ["TaskAnalyzer", "TaskSuggester", "TaskEnricher", "QuickWin", "Breakdown"]
    }

