"""
Database service - High-level functions for database operations.
Replaces the JSON file-based tools.py functions.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Any

from app.database.connection import async_session
from app.database.repository import (
    TaskRepository,
    SubtaskRepository,
    FeedbackRepository,
    QuickWinHistoryRepository,
)
from app.database.models import TaskModel, SubtaskModel
from app.logging_config import get_db_logger

logger = get_db_logger()


async def save_task(task_data: dict, date: str = None) -> dict:
    """Save a task to the database."""
    if date:
        task_data["date"] = date
    elif not task_data.get("date"):
        task_data["date"] = datetime.now().strftime("%Y-%m-%d")
    
    task_text = task_data.get("text", "")[:50]
    logger.debug(f"Saving task: {task_text}...")
    
    async with async_session() as session:
        repo = TaskRepository(session)
        task = await repo.create(task_data)
        logger.info(f"Task saved: {task.id}")
        return {"success": True, "task_id": task.id, "task": task.to_dict()}


async def get_task(task_id: str) -> Optional[dict]:
    """Get a task by ID."""
    logger.debug(f"Fetching task: {task_id}")
    async with async_session() as session:
        repo = TaskRepository(session)
        task = await repo.get_by_id(task_id)
        if task:
            logger.debug(f"Task found: {task_id}")
            return task.to_dict()
        logger.debug(f"Task not found: {task_id}")
        return None


async def get_all_tasks() -> List[dict]:
    """Get all tasks."""
    logger.debug("Fetching all tasks")
    async with async_session() as session:
        repo = TaskRepository(session)
        tasks = await repo.get_all()
        logger.debug(f"Retrieved {len(tasks)} tasks")
        return [t.to_dict() for t in tasks]


async def get_tasks_by_date(date: str) -> List[dict]:
    """Get tasks for a specific date."""
    async with async_session() as session:
        repo = TaskRepository(session)
        tasks = await repo.get_by_date(date)
        return [t.to_dict() for t in tasks]


async def get_all_tasks_by_date() -> dict:
    """Get all tasks organized by date."""
    async with async_session() as session:
        repo = TaskRepository(session)
        return await repo.get_tasks_by_date_grouped()


async def update_task(task_id: str, updates: dict) -> Optional[dict]:
    """Update a task."""
    async with async_session() as session:
        repo = TaskRepository(session)
        task = await repo.update(task_id, updates)
        if task:
            return task.to_dict()
        return None


async def update_task_status(task_id: str, status: str, date: str = None) -> dict:
    """Update a task's status."""
    async with async_session() as session:
        repo = TaskRepository(session)
        task = await repo.update_status(task_id, status)
        if task:
            return {"success": True, "task_id": task_id, "new_status": status}
        return {"success": False, "error": "Task not found"}


async def delete_task(task_id: str) -> dict:
    """Delete a task."""
    async with async_session() as session:
        repo = TaskRepository(session)
        deleted = await repo.delete(task_id)
        return {"success": deleted, "task_id": task_id}


async def delete_all_tasks() -> dict:
    """Delete all tasks."""
    async with async_session() as session:
        repo = TaskRepository(session)
        count = await repo.delete_all()
        return {"success": True, "deleted_count": count}


async def get_task_stats() -> dict:
    """Get overall task statistics."""
    async with async_session() as session:
        repo = TaskRepository(session)
        return await repo.get_stats()


async def get_in_progress_tasks() -> List[dict]:
    """Get all tasks that are in progress, sorted by most recently started."""
    logger.debug("Fetching in-progress tasks")
    async with async_session() as session:
        repo = TaskRepository(session)
        tasks = await repo.get_by_status("in_progress")
        result = [t.to_dict() for t in tasks]
        logger.info(f"Found {len(result)} in-progress tasks")
        return result


async def get_continuable_tasks() -> dict:
    """
    Get tasks that user can continue working on.
    Returns:
    - in_progress: Tasks currently being worked on
    - almost_done: Tasks with subtasks where >50% are completed
    """
    logger.debug("Fetching continuable tasks")
    async with async_session() as session:
        repo = TaskRepository(session)
        subtask_repo = SubtaskRepository(session)
        
        # Get in-progress tasks
        in_progress_tasks = await repo.get_by_status("in_progress")
        in_progress_list = []
        
        for task in in_progress_tasks:
            task_dict = task.to_dict()
            # Get subtasks for this task
            subtasks = await subtask_repo.get_by_task(task.id)
            if subtasks:
                completed = sum(1 for s in subtasks if s.status == "completed")
                total = len(subtasks)
                task_dict["subtask_progress"] = {
                    "completed": completed,
                    "total": total,
                    "percentage": round(completed / total * 100) if total > 0 else 0
                }
                task_dict["subtasks"] = [s.to_dict() for s in subtasks]
            in_progress_list.append(task_dict)
        
        # Get tasks with subtasks that are >50% done but task not completed
        almost_done_list = []
        pending_tasks = await repo.get_by_status("pending")
        
        for task in pending_tasks:
            subtasks = await subtask_repo.get_by_task(task.id)
            if subtasks:
                completed = sum(1 for s in subtasks if s.status == "completed")
                total = len(subtasks)
                percentage = round(completed / total * 100) if total > 0 else 0
                
                # If more than 50% done, it's almost finished
                if percentage >= 50 and completed < total:
                    task_dict = task.to_dict()
                    task_dict["subtask_progress"] = {
                        "completed": completed,
                        "total": total,
                        "percentage": percentage
                    }
                    task_dict["subtasks"] = [s.to_dict() for s in subtasks]
                    almost_done_list.append(task_dict)
        
        logger.info(f"Found {len(in_progress_list)} in-progress, {len(almost_done_list)} almost-done tasks")
        
        return {
            "in_progress": in_progress_list,
            "almost_done": almost_done_list,
            "total_continuable": len(in_progress_list) + len(almost_done_list)
        }


# Subtask operations

async def create_subtasks(task_id: str, subtasks_data: List[dict]) -> List[dict]:
    """Create subtasks for a task."""
    async with async_session() as session:
        # First mark the task as having subtasks generated
        task_repo = TaskRepository(session)
        await task_repo.update(task_id, {"subtasks_generated": True})
        
        # Create subtasks
        subtask_repo = SubtaskRepository(session)
        subtasks = await subtask_repo.create_many(task_id, subtasks_data)
        return [s.to_dict() for s in subtasks]


async def get_subtasks(task_id: str) -> List[dict]:
    """Get subtasks for a task."""
    async with async_session() as session:
        repo = SubtaskRepository(session)
        subtasks = await repo.get_by_task(task_id)
        return [s.to_dict() for s in subtasks]


async def update_subtask_status(subtask_id: str, status: str) -> dict:
    """Update a subtask's status."""
    async with async_session() as session:
        repo = SubtaskRepository(session)
        subtask = await repo.update_status(subtask_id, status)
        if subtask:
            return {"success": True, "subtask_id": subtask_id, "new_status": status}
        return {"success": False, "error": "Subtask not found"}


async def save_subtasks(task_id: str, subtasks_data: List[dict]) -> List[dict]:
    """Save subtasks for a task (alias for create_subtasks)."""
    return await create_subtasks(task_id, subtasks_data)


async def update_task_enrichment(task_id: str, enrichment: Optional[dict]) -> dict:
    """Update a task's enrichment data."""
    async with async_session() as session:
        repo = TaskRepository(session)
        task = await repo.update(task_id, {"enrichment": enrichment})
        if task:
            return {"success": True, "task_id": task_id}
        return {"success": False, "error": "Task not found"}


# Feedback operations

async def record_feedback(
    task_text: str,
    accepted: bool,
    task_id: Optional[str] = None,
    context: Optional[dict] = None,
    reasoning_used: Optional[str] = None
) -> dict:
    """Record user feedback."""
    async with async_session() as session:
        repo = FeedbackRepository(session)
        feedback = await repo.create(
            task_text=task_text,
            accepted=accepted,
            task_id=task_id,
            context=context,
            reasoning_used=reasoning_used
        )
        
        # Get updated stats
        all_feedback = await repo.get_all()
        total = len(all_feedback)
        accepted_count = sum(1 for f in all_feedback if f.accepted)
        
        return {
            "success": True,
            "total_feedback_count": total,
            "acceptance_rate": accepted_count / total if total > 0 else 0
        }


async def get_learning_insights() -> dict:
    """Get learning insights from feedback."""
    async with async_session() as session:
        repo = FeedbackRepository(session)
        return await repo.get_insights()


# Quick win history

async def record_quickwin_shown(quickwin_text: str, category: str, was_added: bool = False) -> dict:
    """Record a quick win that was shown."""
    async with async_session() as session:
        repo = QuickWinHistoryRepository(session)
        entry = await repo.record(quickwin_text, category, was_added)
        return {"success": True, "id": entry.id}


async def get_recent_quickwins(hours: int = 24) -> List[str]:
    """Get quick wins shown recently to avoid repetition."""
    async with async_session() as session:
        repo = QuickWinHistoryRepository(session)
        return await repo.get_recent(hours)


# Enrichment operations (stored in task.enrichment JSON field)

async def save_enrichment(task_id: str, enrichment: dict) -> dict:
    """Save enrichment data for a task."""
    async with async_session() as session:
        repo = TaskRepository(session)
        task = await repo.update(task_id, {"enrichment": enrichment})
        if task:
            return {"success": True, "task_id": task_id}
        return {"success": False, "error": "Task not found"}


async def get_enrichment(task_id: str) -> Optional[dict]:
    """Get enrichment data for a task."""
    async with async_session() as session:
        repo = TaskRepository(session)
        task = await repo.get_by_id(task_id)
        if task and task.enrichment:
            return task.enrichment
        return None

