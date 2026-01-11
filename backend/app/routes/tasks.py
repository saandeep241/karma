"""Task management routes."""

from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.models import (
    Task, TodoList, ImportTodoListRequest, ImportTodoListResponse,
    TaskBreakdownRequest, TaskStatusRequest, ReResearchRequest,
    CompleteQuickWinRequest, SubtaskStatusRequest, AddTaskRequest,
    Session, UserContext, TimeAvailable, EnergyLevel
)
from app.services.session_store import session_store
from app.services import db_service
from app.agents import karma_orchestrator
from app.logging_config import get_api_logger

logger = get_api_logger()

router = APIRouter(prefix="/api", tags=["tasks"])


@router.post("/todo/import", response_model=ImportTodoListResponse)
async def import_todo_list(request: ImportTodoListRequest):
    """
    Import a todo list from text content.
    Uses TaskAnalyzer and TaskEnricher agents to process tasks.
    """
    logger.info("Importing todo list from text content")
    session = session_store.create_session()
    
    # Parse tasks from text
    lines = [line.strip() for line in request.text_content.strip().split("\n")]
    tasks = [Task(text=line) for line in lines if line and not line.startswith("#")]
    
    if not tasks:
        logger.warning("No valid tasks found in import request")
        raise HTTPException(
            status_code=400,
            detail="No valid tasks found in the provided text"
        )
    
    logger.info(f"ORCHESTRATOR: Processing {len(tasks)} imported tasks (agents: TaskAnalyzer, TaskEnricher)")
    
    # Use orchestrator to analyze and enrich tasks
    analyzed_tasks, reasoning_trace = await karma_orchestrator.analyze_tasks(tasks)
    
    logger.info(f"Orchestrator processed {len(analyzed_tasks)} tasks successfully")
    
    # Save tasks to database
    today = datetime.now().strftime("%Y-%m-%d")
    for task in analyzed_tasks:
        task_dict = task.model_dump()
        task_dict["date"] = today
        await db_service.save_task(task_dict)
        logger.debug(f"Saved task: {task.id} - {task.text[:50]}...")
    
    # Create todo list and attach to session
    todo_list = TodoList(tasks=analyzed_tasks)
    session.todo_list = todo_list
    session.agent_reasoning = reasoning_trace
    session_store.update_session(session)
    
    logger.info(f"Import complete: {len(analyzed_tasks)} tasks imported to session {session.id}")
    
    return ImportTodoListResponse(
        session_id=session.id,
        tasks_imported=len(analyzed_tasks),
        tasks=analyzed_tasks
    )


@router.post("/task/add")
@router.post("/tasks/add")
async def add_single_task(request: AddTaskRequest):
    """Add a single task and analyze it."""
    logger.info(f"Adding new task: {request.text[:50]}...")
    task = Task(text=request.text)
    
    if request.category:
        from app.models import TaskCategory
        try:
            task.category = TaskCategory(request.category.lower())
            logger.debug(f"Task category set to: {request.category}")
        except ValueError:
            logger.warning(f"Invalid category ignored: {request.category}")
    
    # Analyze and enrich the single task
    logger.debug("Sending task to orchestrator for analysis")
    analyzed_tasks, _ = await karma_orchestrator.analyze_tasks([task])
    
    if analyzed_tasks:
        # Save to database
        today = datetime.now().strftime("%Y-%m-%d")
        task_dict = analyzed_tasks[0].model_dump()
        task_dict["date"] = today
        await db_service.save_task(task_dict)
        
        logger.info(f"Task added successfully: {task_dict['id']}")
        return {
            "success": True,
            "task": task_dict,
            "message": "Task added and analyzed"
        }
    
    logger.error("Failed to analyze task - orchestrator returned empty result")
    raise HTTPException(status_code=500, detail="Failed to analyze task")


@router.get("/tasks/all")
async def get_all_tasks():
    """Get all tasks organized by date."""
    logger.debug("Fetching all tasks")
    tasks_by_date = await db_service.get_all_tasks_by_date()
    stats = await db_service.get_task_stats()
    total_tasks = stats.get("total", 0)
    logger.info(f"Retrieved {total_tasks} tasks across {len(tasks_by_date)} dates")
    return {
        "tasks_by_date": tasks_by_date,
        "total_dates": len(tasks_by_date),
        "stats": stats
    }


@router.get("/tasks/stats")
async def get_stats():
    """Get overall task statistics for UI badges."""
    stats = await db_service.get_task_stats()
    return stats


@router.get("/tasks/date/{date}")
async def get_tasks_by_date(date: str):
    """Get tasks for a specific date."""
    tasks = await db_service.get_tasks_by_date(date)
    return {"date": date, "tasks": tasks}


@router.get("/tasks/{task_id}")
async def get_task_detail(task_id: str):
    """Get full details for a specific task including enrichment."""
    logger.debug(f"Fetching task details: {task_id}")
    task = await db_service.get_task(task_id)
    if not task:
        logger.warning(f"Task not found: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    logger.debug(f"Task found: {task.get('text', '')[:30]}...")
    return task


class StatusUpdateRequest(BaseModel):
    status: str
    date: Optional[str] = None

@router.put("/tasks/{task_id}/status")
async def update_task_status_endpoint(task_id: str, request: StatusUpdateRequest):
    """Update a task's status."""
    logger.info(f"Updating task {task_id} status to: {request.status}")
    valid_statuses = ["pending", "in_progress", "completed", "skipped"]
    if request.status not in valid_statuses:
        logger.warning(f"Invalid status attempted: {request.status}")
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    result = await db_service.update_task_status(task_id, request.status, request.date)
    if not result.get("success"):
        logger.error(f"Failed to update task {task_id}: {result.get('error')}")
        raise HTTPException(status_code=404, detail=result.get("error", "Failed to update"))
    logger.info(f"Task {task_id} status updated to {request.status}")
    return result


@router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str):
    """Mark a task as completed."""
    result = await db_service.update_task_status(task_id, "completed")
    return result


@router.post("/tasks/{task_id}/breakdown")
async def breakdown_task_by_id(task_id: str):
    """Break down a task into steps by task ID."""
    logger.info(f"Breaking down task: {task_id}")
    
    # Get task from database
    task_data = await db_service.get_task(task_id)
    if not task_data:
        logger.warning(f"Task not found for breakdown: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = Task(**{k: v for k, v in task_data.items() if k in Task.model_fields})
    logger.debug(f"Task to break down: {task.text[:50]}...")
    
    # Break task into steps with default 30 min
    breakdown, reasoning_trace = await karma_orchestrator.break_task_into_steps(
        task=task,
        time_available=30
    )
    
    # Save subtasks to database
    subtask_count = 0
    if breakdown and breakdown.subtasks:
        subtask_count = len(breakdown.subtasks)
        await db_service.save_subtasks(task_id, [s.model_dump() for s in breakdown.subtasks])
        logger.info(f"Task {task_id} broken down into {subtask_count} subtasks")
    else:
        logger.warning(f"No subtasks generated for task {task_id}")
    
    return {
        "task_id": task_id,
        "subtasks": [s.model_dump() for s in breakdown.subtasks] if breakdown else [],
        "reasoning": reasoning_trace
    }


@router.post("/tasks/{task_id}/reresearch")
async def reresearch_task_by_id(task_id: str):
    """Re-research a task by ID."""
    # Get task from database
    task_data = await db_service.get_task(task_id)
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = Task(**{k: v for k, v in task_data.items() if k in Task.model_fields})
    
    print("\n" + "=" * 60)
    print("🤖 ORCHESTRATOR: Re-researching task...")
    print(f"   Task: {task.text}")
    print("=" * 60)
    
    # Re-enrich the task
    enriched_tasks, reasoning_trace = await karma_orchestrator.enrich_tasks([task])
    
    if enriched_tasks:
        enriched_task = enriched_tasks[0]
        # Update task in database with new enrichment
        await db_service.update_task_enrichment(task_id, enriched_task.enrichment.model_dump() if enriched_task.enrichment else None)
        return enriched_task.model_dump()
    
    return task_data


@router.post("/task/breakdown")
async def breakdown_task_from_browse(request: TaskBreakdownRequest):
    """Break down a task into steps (called from browse view)."""
    # Get or create session
    session = session_store.get_session(request.session_id)
    if not session:
        # Create a minimal session for this operation
        session = Session(id=request.session_id)
        session.context = UserContext(
            time_available=TimeAvailable.THIRTY,
            energy_level=EnergyLevel.MEDIUM
        )
        session_store.update_session(session)
    
    # Get task details from database
    task_data = await db_service.get_task(request.task_id)
    if not task_data:
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
    
    # Save subtasks to database
    subtasks_data = [
        {
            "id": str(uuid.uuid4()),
            "text": step.instruction,
            "instruction": step.instruction,
            "estimated_minutes": step.estimated_minutes,
            "order": step.step_number,
            "status": "pending"
        }
        for step in breakdown.steps
    ]
    await db_service.create_subtasks(request.task_id, subtasks_data)
    
    print(f"\n✅ Breakdown Agent: Created {breakdown.total_steps} steps")
    
    return {
        "task": task.model_dump(),
        "breakdown": breakdown.model_dump(),
        "first_step": breakdown.steps[0].model_dump(),
        "message": "Here's your task broken down into steps:",
        "agent_reasoning": f"Breakdown Agent: Created {breakdown.total_steps} actionable steps"
    }


@router.post("/task/status")
async def update_task_status_post(request: TaskStatusRequest):
    """Update task status (POST version for easier frontend calls)."""
    valid_statuses = ["pending", "in_progress", "completed", "skipped"]
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    result = await db_service.update_task_status(request.task_id, request.status)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Failed to update"))
    return result


@router.post("/task/reresearch")
async def reresearch_task(request: ReResearchRequest):
    """Re-research a task, optionally with user correction/feedback."""
    print("\n" + "=" * 60)
    print("🤖 ORCHESTRATOR: Re-researching task with user feedback...")
    print(f"   Task: {request.task_text}")
    if request.correction_text:
        print(f"   Correction type: {request.correction_type}")
        print(f"   User feedback: {request.correction_text[:100]}...")
    print(f"   Using agent: TaskEnricher")
    print("=" * 60)
    
    # Get existing task from database
    task_data = await db_service.get_task(request.task_id)
    if not task_data:
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
    
    # Save enrichment to database
    await db_service.save_enrichment(request.task_id, enrichment)
    
    print(f"\n✅ TaskEnricher: Re-researched with {len(enrichment.get('steps', []))} steps")
    
    return {
        "task_id": request.task_id,
        "enrichment": enrichment,
        "message": "Task re-researched successfully!",
        "used_correction": bool(request.correction_text)
    }


@router.delete("/tasks/delete-all")
async def delete_all_tasks():
    """Delete all tasks - DANGER ZONE."""
    print("\n" + "=" * 60)
    print("⚠️  DELETING ALL TASKS...")
    print("=" * 60)
    
    result = await db_service.delete_all_tasks()
    
    print(f"✅ Deleted {result['deleted_count']} tasks")
    
    return {
        "success": True,
        "deleted_count": result["deleted_count"],
        "message": "All tasks have been deleted"
    }


@router.post("/task/subtask/status")
async def update_subtask_status_endpoint(request: SubtaskStatusRequest):
    """Update a subtask's status."""
    valid_statuses = ["pending", "in_progress", "completed", "skipped"]
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    result = await db_service.update_subtask_status(request.subtask_id, request.status)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Subtask not found"))
    
    return {
        "success": True,
        "task_id": request.task_id,
        "subtask_id": request.subtask_id,
        "new_status": request.status
    }


@router.get("/task/{task_id}/subtasks")
async def get_task_subtasks(task_id: str):
    """Get subtasks for a specific task."""
    task = await db_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    subtasks = task.get("subtasks", [])
    
    # Calculate progress
    total = len(subtasks)
    completed = sum(1 for s in subtasks if s.get("status") == "completed")
    in_progress = sum(1 for s in subtasks if s.get("status") == "in_progress")
    total_time = sum(s.get("estimated_minutes", 0) for s in subtasks)
    completed_time = sum(s.get("estimated_minutes", 0) for s in subtasks if s.get("status") == "completed")
    
    return {
        "task_id": task_id,
        "task_text": task.get("text", ""),
        "task_status": task.get("status", "pending"),
        "subtasks": subtasks,
        "progress": {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": total - completed - in_progress,
            "percent": (completed / total * 100) if total > 0 else 0,
            "total_minutes": total_time,
            "completed_minutes": completed_time,
            "remaining_minutes": total_time - completed_time
        }
    }


@router.post("/quickwin/complete")
async def add_quickwin_as_task(request: CompleteQuickWinRequest):
    """Save a quick win as a pending task to the task list."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    task_data = {
        "id": str(uuid.uuid4()),
        "text": request.text,
        "date": today,
        "status": "pending",  # Save as pending so user can mark done later
        "priority": "medium",
        "category": request.category.lower() if request.category else "other",
        "tags": ["quick-win"],
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "estimated_minutes": request.estimated_minutes or 10,
        "energy_required": "low",
        "task_type": "quick_win",
        "subtasks": [],
        "subtasks_generated": False
    }
    
    result = await db_service.save_task(task_data)
    
    print(f"➕ Quick win added to tasks: {request.text[:50]}...")
    
    return {
        "success": True,
        "task_id": result["task_id"],
        "message": "Quick win added to your task list!"
    }
