"""Suggestion and quick win routes."""

from fastapi import APIRouter, HTTPException

from app.models import (
    Task, TodoList, TaskSuggestion, UserContext,
    GetSuggestionRequest, SuggestFromStorageRequest,
    TimeAvailable, EnergyLevel, EmotionalState
)
from app.services.session_store import session_store
from app.services.tools import get_all_tasks_by_date
from app.agents import karma_orchestrator
from app.logging_config import get_api_logger

logger = get_api_logger()

router = APIRouter(prefix="/api", tags=["suggestions"])


@router.post("/suggestion/from-storage")
async def get_suggestion_from_storage(request: SuggestFromStorageRequest):
    """Get a task suggestion directly from stored tasks without re-importing.
    
    If a task has subtasks, suggests the next pending subtask.
    Otherwise suggests the full task.
    """
    logger.info(f"Getting suggestion from storage (time: {request.time_available}min, energy: {request.energy_level})")
    
    # Load all tasks from storage
    tasks_by_date = get_all_tasks_by_date()
    
    # Collect pending tasks and tasks with pending subtasks
    all_tasks = []
    tasks_with_subtasks = []
    
    for date, date_data in tasks_by_date.items():
        for task_data in date_data.get("tasks", []):
            task_status = task_data.get("status", "pending")
            subtasks = task_data.get("subtasks", [])
            
            # Check for pending subtasks
            pending_subtasks = [s for s in subtasks if s.get("status") in ["pending", "in_progress"]]
            
            if pending_subtasks:
                # Task has pending subtasks - add both task and first pending subtask info
                task = Task(
                    id=task_data.get("id"),
                    text=task_data.get("text"),
                    estimated_minutes=task_data.get("estimated_minutes"),
                    energy_required=task_data.get("energy_required"),
                    category=task_data.get("category"),
                    tags=task_data.get("tags", []),
                    status=task_status,
                    subtasks_generated=True
                )
                # Add subtask info for suggestion
                next_subtask = pending_subtasks[0]
                tasks_with_subtasks.append({
                    "task": task,
                    "next_subtask": next_subtask,
                    "subtask_time": next_subtask.get("estimated_minutes", 10),
                    "progress": f"{len(subtasks) - len(pending_subtasks)}/{len(subtasks)}"
                })
            elif task_status in ["pending", "in_progress"]:
                # Regular task without subtasks
                task = Task(
                    id=task_data.get("id"),
                    text=task_data.get("text"),
                    estimated_minutes=task_data.get("estimated_minutes"),
                    energy_required=task_data.get("energy_required"),
                    category=task_data.get("category"),
                    tags=task_data.get("tags", []),
                    status=task_status
                )
                all_tasks.append(task)
    
    # Prioritize tasks with pending subtasks that fit the time
    matching_subtask_tasks = [
        t for t in tasks_with_subtasks 
        if t["subtask_time"] <= request.time_available
        and t["task"].id not in request.excluded_task_ids
    ]
    
    if matching_subtask_tasks:
        # Suggest the next subtask of an existing task
        best_match = matching_subtask_tasks[0]
        task = best_match["task"]
        subtask = best_match["next_subtask"]
        progress = best_match["progress"]
        
        # Create a suggestion for the subtask
        suggestion = TaskSuggestion(
            task=task,
            reasoning=f"Continue working on '{task.text}' - Next step: {subtask.get('instruction')} (Progress: {progress} subtasks completed)",
            confidence_score=0.95,
            is_generic_quickwin=False
        )
        
        return {
            "session_id": "subtask_suggestion",
            "suggestion": suggestion.model_dump(),
            "alternatives_available": len(all_tasks) > 0 or len(tasks_with_subtasks) > 1,
            "message": f"Continue your task - {subtask.get('estimated_minutes', 10)} min for next step:",
            "has_subtask": True,
            "next_subtask": subtask,
            "progress": progress
        }
    
    if not all_tasks and not tasks_with_subtasks:
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


@router.post("/suggestion/get")
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


@router.post("/quickwin")
async def post_ai_quickwin(request: dict = None):
    """Get an AI-generated quick win from the QuickWin agent (POST version)."""
    return await _generate_quickwin(request)


@router.get("/quickwin/get")
async def get_ai_quickwin():
    """Get an AI-generated quick win from the QuickWin agent (GET version)."""
    return await _generate_quickwin(None)


async def _generate_quickwin(request: dict = None):
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


@router.get("/options")
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


@router.get("/agent/insights")
async def get_agent_insights():
    """Get learning insights from all agents."""
    insights = karma_orchestrator.get_learning_insights()
    return {
        "insights": insights,
        "message": "Learning insights from agent interactions",
        "agents": ["TaskAnalyzer", "TaskSuggester", "TaskEnricher", "QuickWin", "Breakdown"]
    }

