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
    TokenUsageRepository,
    UserTokenLimitRepository,
    UserPreferencesRepository,
)
from app.database.models import TaskModel, SubtaskModel
from app.logging_config import get_db_logger

logger = get_db_logger()


async def save_task(user_id: str, task_data: dict, date: str = None) -> dict:
    """Save a task to the database for a specific user."""
    if date:
        task_data["date"] = date
    elif not task_data.get("date"):
        task_data["date"] = datetime.now().strftime("%Y-%m-%d")
    
    task_text = task_data.get("text", "")[:50]
    logger.debug(f"Saving task: {task_text}...")
    
    async with async_session() as session:
        repo = TaskRepository(session)
        task = await repo.create(user_id, task_data)
        logger.info(f"Task saved: {task.id}")
        return {"success": True, "task_id": task.id, "task": task.to_dict()}


async def get_task(user_id: str, task_id: str) -> Optional[dict]:
    """Get a task by ID for a specific user."""
    logger.debug(f"Fetching task: {task_id}")
    async with async_session() as session:
        repo = TaskRepository(session)
        task = await repo.get_by_id(user_id, task_id)
        if task:
            logger.debug(f"Task found: {task_id}")
            return task.to_dict()
        logger.debug(f"Task not found: {task_id}")
        return None


async def get_all_tasks(user_id: str) -> List[dict]:
    """Get all tasks for a specific user."""
    logger.debug("Fetching all tasks")
    async with async_session() as session:
        repo = TaskRepository(session)
        tasks = await repo.get_all(user_id)
        logger.debug(f"Retrieved {len(tasks)} tasks")
        return [t.to_dict() for t in tasks]


async def get_tasks_by_date(user_id: str, date: str) -> List[dict]:
    """Get tasks for a specific date and user."""
    async with async_session() as session:
        repo = TaskRepository(session)
        tasks = await repo.get_by_date(user_id, date)
        return [t.to_dict() for t in tasks]


async def get_all_tasks_by_date(user_id: str) -> dict:
    """Get all tasks organized by date for a specific user."""
    async with async_session() as session:
        repo = TaskRepository(session)
        return await repo.get_tasks_by_date_grouped(user_id)


async def update_task(user_id: str, task_id: str, updates: dict) -> Optional[dict]:
    """Update a task for a specific user."""
    async with async_session() as session:
        repo = TaskRepository(session)
        task = await repo.update(user_id, task_id, updates)
        if task:
            return task.to_dict()
        return None


async def update_task_status(user_id: str, task_id: str, status: str, date: str = None) -> dict:
    """Update a task's status for a specific user."""
    async with async_session() as session:
        repo = TaskRepository(session)
        task = await repo.update_status(user_id, task_id, status)
        if task:
            return {"success": True, "task_id": task_id, "new_status": status}
        return {"success": False, "error": "Task not found"}


async def delete_task(user_id: str, task_id: str) -> dict:
    """Delete a task for a specific user."""
    async with async_session() as session:
        repo = TaskRepository(session)
        deleted = await repo.delete(user_id, task_id)
        return {"success": deleted, "task_id": task_id}


async def delete_all_tasks(user_id: str) -> dict:
    """Delete all tasks for a specific user."""
    async with async_session() as session:
        repo = TaskRepository(session)
        count = await repo.delete_all(user_id)
        return {"success": True, "deleted_count": count}


async def get_task_stats(user_id: str) -> dict:
    """Get overall task statistics for a specific user."""
    async with async_session() as session:
        repo = TaskRepository(session)
        stats = await repo.get_stats(user_id)
        prefs_repo = UserPreferencesRepository(session)
        stats["onboarding_completed"] = await prefs_repo.has_completed_onboarding(user_id)
        return stats


async def mark_onboarding_complete(user_id: str) -> None:
    """Persist that a user has completed the onboarding flow."""
    async with async_session() as session:
        prefs_repo = UserPreferencesRepository(session)
        await prefs_repo.mark_onboarding_complete(user_id)


async def get_in_progress_tasks(user_id: str) -> List[dict]:
    """Get all tasks that are in progress for a specific user, sorted by most recently started."""
    logger.debug("Fetching in-progress tasks")
    async with async_session() as session:
        repo = TaskRepository(session)
        tasks = await repo.get_by_status(user_id, "in_progress")
        result = [t.to_dict() for t in tasks]
        logger.info(f"Found {len(result)} in-progress tasks")
        return result


async def get_continuable_tasks(user_id: str) -> dict:
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
        in_progress_tasks = await repo.get_by_status(user_id, "in_progress")
        in_progress_list = []
        
        for task in in_progress_tasks:
            task_dict = task.to_dict()
            # Get subtasks for this task
            subtasks = await subtask_repo.get_by_task(user_id, task.id)
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
        pending_tasks = await repo.get_by_status(user_id, "pending")
        
        for task in pending_tasks:
            subtasks = await subtask_repo.get_by_task(user_id, task.id)
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

async def create_subtasks(user_id: str, task_id: str, subtasks_data: List[dict]) -> List[dict]:
    """Create subtasks for a task."""
    async with async_session() as session:
        # First mark the task as having subtasks generated
        task_repo = TaskRepository(session)
        await task_repo.update(user_id, task_id, {"subtasks_generated": True})
        
        # Create subtasks
        subtask_repo = SubtaskRepository(session)
        subtasks = await subtask_repo.create_many(user_id, task_id, subtasks_data)
        return [s.to_dict() for s in subtasks]


async def get_subtasks(user_id: str, task_id: str) -> List[dict]:
    """Get subtasks for a task."""
    async with async_session() as session:
        repo = SubtaskRepository(session)
        subtasks = await repo.get_by_task(user_id, task_id)
        return [s.to_dict() for s in subtasks]


async def update_subtask_status(user_id: str, subtask_id: str, status: str) -> dict:
    """Update a subtask's status and auto-complete parent task if all subtasks are done."""
    async with async_session() as session:
        subtask_repo = SubtaskRepository(session)
        subtask = await subtask_repo.update_status(user_id, subtask_id, status)
        
        if not subtask:
            return {"success": False, "error": "Subtask not found"}
        
        task_id = subtask.task_id
        parent_completed = False
        
        # Check if all subtasks are now completed
        if status == "completed":
            all_subtasks = await subtask_repo.get_by_task(user_id, task_id)
            all_completed = all(s.status == "completed" for s in all_subtasks)
            
            if all_completed and len(all_subtasks) > 0:
                # Auto-complete the parent task
                task_repo = TaskRepository(session)
                from datetime import datetime
                await task_repo.update(user_id, task_id, {
                    "status": "completed",
                    "completed_at": datetime.utcnow()
                })
                parent_completed = True
                logger.info(f"Auto-completed parent task {task_id} - all {len(all_subtasks)} subtasks done")
        
        return {
            "success": True, 
            "subtask_id": subtask_id, 
            "new_status": status,
            "parent_completed": parent_completed,
            "task_id": task_id
        }


async def save_subtasks(user_id: str, task_id: str, subtasks_data: List[dict]) -> List[dict]:
    """Save subtasks for a task (alias for create_subtasks)."""
    return await create_subtasks(user_id, task_id, subtasks_data)


async def update_subtask_progress(user_id: str, subtask_id: str, progress: int) -> dict:
    """Update a subtask's progress (0-100). Auto-completes if progress is 100."""
    async with async_session() as session:
        subtask_repo = SubtaskRepository(session)
        
        # Get the subtask first - verify it belongs to user
        from sqlalchemy import select
        from app.database.models import SubtaskModel
        result = await session.execute(
            select(SubtaskModel)
            .where(SubtaskModel.id == subtask_id)
            .where(SubtaskModel.user_id == user_id)
        )
        subtask = result.scalar_one_or_none()
        
        if not subtask:
            return {"success": False, "error": "Subtask not found"}
        
        task_id = subtask.task_id
        
        # Update progress and status based on progress value
        new_status = "completed" if progress == 100 else ("in_progress" if progress > 0 else "pending")
        subtask.progress = progress
        subtask.status = new_status
        if progress == 100:
            from datetime import datetime
            subtask.completed_at = datetime.utcnow()
        else:
            subtask.completed_at = None
        
        await session.commit()
        
        parent_completed = False
        
        # Check if all subtasks are now completed
        if progress == 100:
            all_subtasks = await subtask_repo.get_by_task(user_id, task_id)
            all_completed = all(s.progress == 100 or s.status == "completed" for s in all_subtasks)
            
            if all_completed and len(all_subtasks) > 0:
                task_repo = TaskRepository(session)
                from datetime import datetime
                await task_repo.update(user_id, task_id, {
                    "status": "completed",
                    "completed_at": datetime.utcnow()
                })
                parent_completed = True
                logger.info(f"Auto-completed parent task {task_id} - all {len(all_subtasks)} subtasks at 100%")
        
        return {
            "success": True,
            "subtask_id": subtask_id,
            "progress": progress,
            "new_status": new_status,
            "parent_completed": parent_completed,
            "task_id": task_id
        }


async def add_subtask(user_id: str, task_id: str, text: str, estimated_minutes: int = 5) -> dict:
    """Add a manual subtask to a task."""
    async with async_session() as session:
        # Check if task exists and belongs to user
        task_repo = TaskRepository(session)
        task = await task_repo.get_by_id(user_id, task_id)
        if not task:
            return {"success": False, "error": "Task not found"}
        
        # Get current subtasks to determine order
        subtask_repo = SubtaskRepository(session)
        existing_subtasks = await subtask_repo.get_by_task(user_id, task_id)
        next_order = len(existing_subtasks) + 1
        
        # Create the new subtask
        import uuid
        subtask_data = {
            "text": text,
            "instruction": text,
            "estimated_minutes": estimated_minutes,
            "order": next_order,
            "status": "pending",
            "progress": 0
        }
        
        subtasks = await subtask_repo.create_many(user_id, task_id, [subtask_data])
        
        # Mark task as having subtasks
        await task_repo.update(user_id, task_id, {"subtasks_generated": True})
        
        logger.info(f"Added manual subtask to task {task_id}: {text[:50]}...")
        
        return {
            "success": True,
            "subtask": subtasks[0].to_dict() if subtasks else None
        }


async def update_task_enrichment(user_id: str, task_id: str, enrichment: Optional[dict]) -> dict:
    """Update a task's enrichment data."""
    async with async_session() as session:
        repo = TaskRepository(session)
        task = await repo.update(user_id, task_id, {"enrichment": enrichment})
        if task:
            return {"success": True, "task_id": task_id}
        return {"success": False, "error": "Task not found"}


# Feedback operations

async def record_feedback(
    user_id: str,
    task_text: str,
    accepted: bool,
    task_id: Optional[str] = None,
    context: Optional[dict] = None,
    reasoning_used: Optional[str] = None
) -> dict:
    """Record user feedback for a specific user."""
    async with async_session() as session:
        repo = FeedbackRepository(session)
        feedback = await repo.create(
            user_id=user_id,
            task_text=task_text,
            accepted=accepted,
            task_id=task_id,
            context=context,
            reasoning_used=reasoning_used
        )
        
        # Get updated stats for this user
        all_feedback = await repo.get_all(user_id)
        total = len(all_feedback)
        accepted_count = sum(1 for f in all_feedback if f.accepted)
        
        return {
            "success": True,
            "total_feedback_count": total,
            "acceptance_rate": accepted_count / total if total > 0 else 0
        }


async def get_learning_insights(user_id: str) -> dict:
    """Get learning insights from feedback for a specific user."""
    async with async_session() as session:
        repo = FeedbackRepository(session)
        return await repo.get_insights(user_id)


# Quick win history

async def record_quickwin_shown(user_id: str, quickwin_text: str, category: str, was_added: bool = False) -> dict:
    """Record a quick win that was shown to a specific user."""
    async with async_session() as session:
        repo = QuickWinHistoryRepository(session)
        entry = await repo.record(user_id, quickwin_text, category, was_added)
        return {"success": True, "id": entry.id}


async def get_recent_quickwins(user_id: str, hours: int = 24) -> List[str]:
    """Get quick wins shown recently to a specific user to avoid repetition."""
    async with async_session() as session:
        repo = QuickWinHistoryRepository(session)
        return await repo.get_recent(user_id, hours)


# Enrichment operations (stored in task.enrichment JSON field)

async def save_enrichment(user_id: str, task_id: str, enrichment: dict) -> dict:
    """Save enrichment data for a task."""
    async with async_session() as session:
        repo = TaskRepository(session)
        task = await repo.update(user_id, task_id, {"enrichment": enrichment})
        if task:
            return {"success": True, "task_id": task_id}
        return {"success": False, "error": "Task not found"}


async def get_enrichment(user_id: str, task_id: str) -> Optional[dict]:
    """Get enrichment data for a task."""
    async with async_session() as session:
        repo = TaskRepository(session)
        task = await repo.get_by_id(user_id, task_id)
        if task and task.enrichment:
            return task.enrichment
        return None


async def record_token_usage(
    user_id: str,
    agent_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    model: str,
    task_id: Optional[str] = None,
    operation_type: Optional[str] = None
) -> dict:
    """Record token usage for a user."""
    async with async_session() as session:
        repo = TokenUsageRepository(session)
        usage = await repo.create(
            user_id=user_id,
            agent_name=agent_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=model,
            task_id=task_id,
            operation_type=operation_type
        )
        return {"success": True, "usage_id": usage.id}


async def get_token_usage_stats(user_id: str, days: int = 30) -> dict:
    """Get token usage statistics for a user."""
    async with async_session() as session:
        repo = TokenUsageRepository(session)
        return await repo.get_user_stats(user_id, days)


async def check_token_limit(user_id: str, tokens_to_check: int) -> tuple[bool, dict]:
    """
    Check if user can use tokens (without incrementing).
    
    Returns:
        (allowed: bool, limit_info: dict)
    """
    from app.config import get_settings
    settings = get_settings()
    
    async with async_session() as session:
        repo = UserTokenLimitRepository(session)
        return await repo.check_limit(user_id, tokens_to_check, settings.default_monthly_token_limit)


async def increment_token_usage(user_id: str, tokens_used: int) -> dict:
    """
    Increment user's token usage (called after successful API call).
    
    Returns:
        Updated limit_info dict
    """
    from app.config import get_settings
    settings = get_settings()
    
    async with async_session() as session:
        repo = UserTokenLimitRepository(session)
        return await repo.increment_usage(user_id, tokens_used, settings.default_monthly_token_limit)


async def get_token_limit_info(user_id: str) -> dict:
    """Get current token limit and usage for a user."""
    from app.config import get_settings
    settings = get_settings()
    
    async with async_session() as session:
        repo = UserTokenLimitRepository(session)
        return await repo.get_current_usage(user_id, settings.default_monthly_token_limit)


async def reset_user_monthly_usage(user_id: str) -> dict:
    """Reset a user's monthly token usage (admin function)."""
    async with async_session() as session:
        repo = UserTokenLimitRepository(session)
        return await repo.reset_monthly_usage(user_id)


async def update_user_token_limit(user_id: str, new_limit: int) -> dict:
    """Update a user's monthly token limit (admin function)."""
    async with async_session() as session:
        repo = UserTokenLimitRepository(session)
        return await repo.update_limit(user_id, new_limit)

