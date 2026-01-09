"""Task management routes."""

from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException

from app.models import (
    Task, TodoList, ImportTodoListRequest, ImportTodoListResponse,
    TaskBreakdownRequest, TaskStatusRequest, ReResearchRequest,
    CompleteQuickWinRequest, SubtaskStatusRequest, AddTaskRequest,
    Session, UserContext, TimeAvailable, EnergyLevel
)
from app.services.session_store import session_store
from app.services.tools import (
    get_all_tasks_by_date, get_task_stats, load_tasks, get_task_details,
    get_task_enrichment, update_task_status, save_task_with_details,
    save_reasoning, TASKS_DIR, TASK_DETAILS_DIR
)
from app.agents import karma_orchestrator

router = APIRouter(prefix="/api", tags=["tasks"])


@router.post("/todo/import", response_model=ImportTodoListResponse)
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


@router.post("/task/add")
async def add_single_task(request: AddTaskRequest):
    """Add a single task and analyze it."""
    task = Task(text=request.text)
    
    if request.category:
        from app.models import TaskCategory
        try:
            task.category = TaskCategory(request.category.lower())
        except ValueError:
            pass
    
    print(f"\n🤖 Adding and analyzing task: {task.text[:50]}...")
    
    # Analyze and enrich the single task
    analyzed_tasks, _ = await karma_orchestrator.analyze_tasks([task])
    
    if analyzed_tasks:
        return {
            "success": True,
            "task": analyzed_tasks[0].model_dump(),
            "message": "Task added and analyzed"
        }
    
    raise HTTPException(status_code=500, detail="Failed to analyze task")


@router.get("/tasks/all")
async def get_all_tasks():
    """Get all tasks organized by date."""
    tasks_by_date = get_all_tasks_by_date()
    stats = get_task_stats()
    return {
        "tasks_by_date": tasks_by_date,
        "total_dates": len(tasks_by_date),
        "stats": stats
    }


@router.get("/tasks/stats")
async def get_stats():
    """Get overall task statistics for UI badges."""
    stats = get_task_stats()
    return stats


@router.get("/tasks/date/{date}")
async def get_tasks_by_date(date: str):
    """Get tasks for a specific date."""
    data = load_tasks(date)
    return data


@router.get("/tasks/{task_id}")
async def get_task_detail(task_id: str):
    """Get full details for a specific task including enrichment."""
    task = get_task_details(task_id)
    if "error" in task:
        raise HTTPException(status_code=404, detail=task["error"])
    
    # Also get enrichment if available
    enrichment = get_task_enrichment(task_id)
    if "error" not in enrichment:
        task["enrichment"] = enrichment
    
    return task


@router.put("/tasks/{task_id}/status")
async def update_task_status_endpoint(task_id: str, status: str, date: str = None):
    """Update a task's status."""
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


@router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str):
    """Mark a task as completed."""
    result = update_task_status(task_id, "completed")
    return result


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


@router.post("/task/status")
async def update_task_status_post(request: TaskStatusRequest):
    """Update task status (POST version for easier frontend calls)."""
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


@router.delete("/tasks/delete-all")
async def delete_all_tasks():
    """Delete all tasks - DANGER ZONE."""
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


@router.post("/task/subtask/status")
async def update_subtask_status_endpoint(request: SubtaskStatusRequest):
    """Update a subtask's status."""
    from app.models import SubtaskStatus
    
    valid_statuses = ["pending", "in_progress", "completed", "skipped"]
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    # Get task
    task_data = get_task_details(request.task_id)
    if "error" in task_data:
        raise HTTPException(status_code=404, detail=task_data["error"])
    
    # Find and update subtask
    subtasks = task_data.get("subtasks", [])
    subtask_found = False
    all_completed = True
    any_in_progress = False
    
    for subtask in subtasks:
        if subtask.get("id") == request.subtask_id:
            subtask["status"] = request.status
            if request.status == "in_progress":
                subtask["started_at"] = datetime.now().isoformat()
            elif request.status == "completed":
                subtask["completed_at"] = datetime.now().isoformat()
            subtask_found = True
        
        # Check overall status
        if subtask.get("status") != "completed":
            all_completed = False
        if subtask.get("status") == "in_progress":
            any_in_progress = True
    
    if not subtask_found:
        raise HTTPException(status_code=404, detail="Subtask not found")
    
    # Update parent task status based on subtasks
    if all_completed:
        task_data["status"] = "completed"
        task_data["completed_at"] = datetime.now().isoformat()
    elif any_in_progress:
        task_data["status"] = "in_progress"
        if not task_data.get("started_at"):
            task_data["started_at"] = datetime.now().isoformat()
    
    task_data["subtasks"] = subtasks
    
    # Save updated task
    today = datetime.now().strftime("%Y-%m-%d")
    save_task_with_details(task_data, today)
    
    return {
        "success": True,
        "task_id": request.task_id,
        "subtask_id": request.subtask_id,
        "new_status": request.status,
        "task_status": task_data["status"],
        "all_subtasks_completed": all_completed
    }


@router.get("/task/{task_id}/subtasks")
async def get_task_subtasks(task_id: str):
    """Get subtasks for a specific task."""
    task_data = get_task_details(task_id)
    if "error" in task_data:
        raise HTTPException(status_code=404, detail=task_data["error"])
    
    subtasks = task_data.get("subtasks", [])
    
    # Calculate progress
    total = len(subtasks)
    completed = sum(1 for s in subtasks if s.get("status") == "completed")
    in_progress = sum(1 for s in subtasks if s.get("status") == "in_progress")
    total_time = sum(s.get("estimated_minutes", 0) for s in subtasks)
    completed_time = sum(s.get("estimated_minutes", 0) for s in subtasks if s.get("status") == "completed")
    
    return {
        "task_id": task_id,
        "task_text": task_data.get("text", ""),
        "task_status": task_data.get("status", "pending"),
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
async def complete_quickwin(request: CompleteQuickWinRequest):
    """Save a completed quick win as a task."""
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

