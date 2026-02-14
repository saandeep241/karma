"""Database repository with all CRUD operations for Karma."""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import TaskModel, SubtaskModel, FeedbackModel, QuickWinHistoryModel, TokenUsageModel, UserTokenLimitModel


class TaskRepository:
    """Repository for Task operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, user_id: str, task_data: dict) -> TaskModel:
        """Create a new task for a specific user."""
        task_id = task_data.get("id") or str(uuid.uuid4())
        
        # Ensure user_id is set (don't trust client-provided user_id in task_data)
        task_data["user_id"] = user_id
        print(f"📦 [DB] Creating task for user_id={user_id}: {task_data.get('text', '')[:50]}...")
        
        # Helper to parse datetime - handles both string and datetime objects
        def parse_dt(val):
            if val is None:
                return None
            if isinstance(val, datetime):
                return val
            if isinstance(val, str):
                return datetime.fromisoformat(val)
            return None
        
        task = TaskModel(
            id=task_id,
            user_id=user_id,  # Always use the provided user_id
            text=task_data.get("text", ""),
            date=task_data.get("date", datetime.now().strftime("%Y-%m-%d")),
            status=task_data.get("status", "pending"),
            priority=task_data.get("priority", "medium"),
            category=task_data.get("category", "other"),
            estimated_minutes=task_data.get("estimated_minutes", 15),
            created_at=parse_dt(task_data.get("created_at")) or datetime.utcnow(),
            started_at=parse_dt(task_data.get("started_at")),
            completed_at=parse_dt(task_data.get("completed_at")),
            energy_required=task_data.get("energy_required", "medium"),
            task_type=task_data.get("task_type"),
            tags=task_data.get("tags", []),
            ai_reasoning=task_data.get("ai_reasoning"),
            enrichment=task_data.get("enrichment"),
            times_suggested=task_data.get("times_suggested", 0),
            times_accepted=task_data.get("times_accepted", 0),
            times_rejected=task_data.get("times_rejected", 0),
            subtasks_generated=task_data.get("subtasks_generated", False),
            is_dummy=task_data.get("is_dummy", False),
            notes=task_data.get("notes"),
        )
        
        self.session.add(task)
        await self.session.commit()
        
        # Re-fetch with eager loading to avoid lazy load issues
        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.subtasks))
            .where(TaskModel.id == task_id)
            .where(TaskModel.user_id == user_id)  # Verify ownership
        )
        task = result.scalar_one()
        
        print(f"📦 [DB] Created task: {task.text[:50]}...")
        return task
    
    async def get_by_id(self, user_id: str, task_id: str) -> Optional[TaskModel]:
        """Get a task by ID with subtasks, only if it belongs to the user."""
        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.subtasks))
            .where(TaskModel.id == task_id)
            .where(TaskModel.user_id == user_id)  # Filter by user_id
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, user_id: str) -> List[TaskModel]:
        """Get all tasks with subtasks for a specific user."""
        print(f"📦 [DB] Fetching all tasks for user_id={user_id}")
        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.subtasks))
            .where(TaskModel.user_id == user_id)  # Filter by user_id
            .order_by(TaskModel.created_at.desc())
        )
        tasks = list(result.scalars().all())
        print(f"📦 [DB] Found {len(tasks)} tasks for user_id={user_id}")
        return tasks
    
    async def get_by_date(self, user_id: str, date: str) -> List[TaskModel]:
        """Get tasks for a specific date and user."""
        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.subtasks))
            .where(TaskModel.user_id == user_id)  # Filter by user_id
            .where(TaskModel.date == date)
            .order_by(TaskModel.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_by_status(self, user_id: str, status: str) -> List[TaskModel]:
        """Get tasks by status for a specific user."""
        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.subtasks))
            .where(TaskModel.user_id == user_id)  # Filter by user_id
            .where(TaskModel.status == status)
            .order_by(TaskModel.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_recent(self, user_id: str, days: int = 7) -> List[TaskModel]:
        """Get tasks from the last N days for a specific user."""
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.subtasks))
            .where(TaskModel.user_id == user_id)  # Filter by user_id
            .where(TaskModel.date >= start_date)
            .order_by(TaskModel.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_tasks_by_date_grouped(self, user_id: str) -> dict:
        """Get all tasks organized by date for a specific user."""
        tasks = await self.get_all(user_id)
        
        grouped = {}
        for task in tasks:
            date = task.date
            if date not in grouped:
                grouped[date] = {
                    "date": date,
                    "tasks": [],
                    "stats": {"total": 0, "pending": 0, "in_progress": 0, "completed": 0}
                }
            
            grouped[date]["tasks"].append(task.to_dict())
            grouped[date]["stats"]["total"] += 1
            grouped[date]["stats"][task.status] = grouped[date]["stats"].get(task.status, 0) + 1
        
        return grouped
    
    async def update(self, user_id: str, task_id: str, updates: dict) -> Optional[TaskModel]:
        """Update a task, only if it belongs to the user."""
        task = await self.get_by_id(user_id, task_id)
        if not task:
            return None
        
        # Prevent user_id from being changed via updates
        updates.pop("user_id", None)
        
        for key, value in updates.items():
            if hasattr(task, key):
                # Handle datetime fields
                if key in ["started_at", "completed_at", "created_at"] and isinstance(value, str):
                    value = datetime.fromisoformat(value)
                setattr(task, key, value)
        
        await self.session.commit()
        await self.session.refresh(task)
        
        print(f"📦 [DB] Updated task: {task_id}")
        return task
    
    async def update_status(self, user_id: str, task_id: str, status: str) -> Optional[TaskModel]:
        """Update a task's status, only if it belongs to the user."""
        task = await self.get_by_id(user_id, task_id)
        if not task:
            return None
        
        task.status = status
        
        if status == "in_progress" and not task.started_at:
            task.started_at = datetime.utcnow()
        elif status == "completed":
            task.completed_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(task)
        
        print(f"📦 [DB] Updated task status: {task_id} -> {status}")
        return task
    
    async def delete(self, user_id: str, task_id: str) -> bool:
        """Delete a task and its subtasks, only if it belongs to the user."""
        # Load the task with subtasks to ensure cascade delete works
        task = await self.get_by_id(user_id, task_id)
        if not task:
            return False
        
        # Delete the task - this will cascade delete subtasks due to the relationship
        # First, explicitly delete subtasks to avoid foreign key constraint issues
        if task.subtasks:
            for subtask in task.subtasks:
                await self.session.delete(subtask)
        
        # Now delete the task
        await self.session.delete(task)
        await self.session.commit()
        
        print(f"📦 [DB] Deleted task: {task_id} (and {len(task.subtasks) if task.subtasks else 0} subtasks)")
        return True
    
    async def delete_all(self, user_id: str) -> int:
        """Delete all tasks and their subtasks for a specific user."""
        # First, get all tasks with their subtasks
        tasks = await self.get_all(user_id)
        
        # Delete all subtasks first
        subtask_count = 0
        for task in tasks:
            if task.subtasks:
                for subtask in task.subtasks:
                    await self.session.delete(subtask)
                    subtask_count += 1
        
        # Now delete all tasks
        for task in tasks:
            await self.session.delete(task)
        
        await self.session.commit()
        
        print(f"📦 [DB] Deleted all tasks for user: {len(tasks)} tasks and {subtask_count} subtasks")
        return len(tasks)
    
    async def get_stats(self, user_id: str) -> dict:
        """Get overall task statistics for a specific user."""
        from datetime import datetime, timedelta
        
        # Basic counts - filter by user_id
        result = await self.session.execute(
            select(
                func.count(TaskModel.id).label("total"),
                func.sum(func.cast(TaskModel.status == "completed", Integer)).label("completed"),
                func.sum(func.cast(TaskModel.status == "pending", Integer)).label("pending"),
                func.sum(func.cast(TaskModel.status == "in_progress", Integer)).label("in_progress"),
            )
            .where(TaskModel.user_id == user_id)  # Filter by user_id
        )
        row = result.one()
        
        total = row.total or 0
        completed = row.completed or 0
        pending = row.pending or 0
        in_progress = row.in_progress or 0
        
        # Completed today - filter by user_id
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_result = await self.session.execute(
            select(func.count(TaskModel.id))
            .where(TaskModel.user_id == user_id)  # Filter by user_id
            .where(TaskModel.status == "completed")
            .where(TaskModel.completed_at >= today_start)
        )
        completed_today = today_result.scalar() or 0
        
        # Completed this week (last 7 days) - filter by user_id
        week_start = today_start - timedelta(days=7)
        week_result = await self.session.execute(
            select(func.count(TaskModel.id))
            .where(TaskModel.user_id == user_id)  # Filter by user_id
            .where(TaskModel.status == "completed")
            .where(TaskModel.completed_at >= week_start)
        )
        completed_this_week = week_result.scalar() or 0
        
        # Tasks by category - filter by user_id
        category_result = await self.session.execute(
            select(TaskModel.category, func.count(TaskModel.id))
            .where(TaskModel.user_id == user_id)  # Filter by user_id
            .group_by(TaskModel.category)
        )
        tasks_by_category = {cat: count for cat, count in category_result.all() if cat}
        
        # Tasks by priority - filter by user_id
        priority_result = await self.session.execute(
            select(TaskModel.priority, func.count(TaskModel.id))
            .where(TaskModel.user_id == user_id)  # Filter by user_id
            .group_by(TaskModel.priority)
        )
        tasks_by_priority = {pri: count for pri, count in priority_result.all() if pri}
        
        return {
            "total_tasks": total,
            "completed_tasks": completed,
            "pending_tasks": pending + in_progress,
            "total": total,
            "completed": completed,
            "pending": pending,
            "in_progress": in_progress,
            "completed_today": completed_today,
            "completed_this_week": completed_this_week,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
            "tasks_by_category": tasks_by_category,
            "tasks_by_priority": tasks_by_priority,
            "average_completion_time_minutes": 0,  # TODO: Calculate from actual data
        }


# Need to import Integer for the cast
from sqlalchemy import Integer


class SubtaskRepository:
    """Repository for Subtask operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, user_id: str, task_id: str, subtask_data: dict) -> SubtaskModel:
        """Create a new subtask. Verifies task belongs to user."""
        # Verify task belongs to user before creating subtask
        task_result = await self.session.execute(
            select(TaskModel).where(TaskModel.id == task_id).where(TaskModel.user_id == user_id)
        )
        task = task_result.scalar_one_or_none()
        if not task:
            raise ValueError(f"Task {task_id} not found or doesn't belong to user {user_id}")
        
        subtask_id = subtask_data.get("id") or str(uuid.uuid4())
        
        subtask = SubtaskModel(
            id=subtask_id,
            user_id=user_id,  # Set user_id from task owner
            task_id=task_id,
            text=subtask_data.get("text") or subtask_data.get("instruction", ""),
            instruction=subtask_data.get("instruction"),
            status=subtask_data.get("status", "pending"),
            order=subtask_data.get("order", 0),
            estimated_minutes=subtask_data.get("estimated_minutes", 5),
            ai_reasoning=subtask_data.get("ai_reasoning"),
        )
        
        self.session.add(subtask)
        await self.session.commit()
        await self.session.refresh(subtask)
        
        return subtask
    
    async def create_many(self, user_id: str, task_id: str, subtasks_data: List[dict]) -> List[SubtaskModel]:
        """Create multiple subtasks for a task. Verifies task belongs to user."""
        subtasks = []
        for i, data in enumerate(subtasks_data):
            data["order"] = data.get("order", i)
            subtask = await self.create(user_id, task_id, data)
            subtasks.append(subtask)
        return subtasks
    
    async def get_by_task(self, user_id: str, task_id: str) -> List[SubtaskModel]:
        """Get all subtasks for a task, only if task belongs to user."""
        # Verify task belongs to user
        task_result = await self.session.execute(
            select(TaskModel).where(TaskModel.id == task_id).where(TaskModel.user_id == user_id)
        )
        task = task_result.scalar_one_or_none()
        if not task:
            return []  # Return empty list if task doesn't belong to user
        
        result = await self.session.execute(
            select(SubtaskModel)
            .where(SubtaskModel.task_id == task_id)
            .where(SubtaskModel.user_id == user_id)  # Also filter by user_id for safety
            .order_by(SubtaskModel.order)
        )
        return list(result.scalars().all())
    
    async def update_status(self, user_id: str, subtask_id: str, status: str) -> Optional[SubtaskModel]:
        """Update a subtask's status, only if it belongs to the user."""
        result = await self.session.execute(
            select(SubtaskModel)
            .where(SubtaskModel.id == subtask_id)
            .where(SubtaskModel.user_id == user_id)  # Verify ownership
        )
        subtask = result.scalar_one_or_none()
        
        if not subtask:
            return None
        
        subtask.status = status
        if status == "completed":
            subtask.completed_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(subtask)
        
        print(f"📦 [DB] Updated subtask status: {subtask_id} -> {status}")
        return subtask


class FeedbackRepository:
    """Repository for Feedback operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        user_id: str,
        task_text: str,
        accepted: bool,
        task_id: Optional[str] = None,
        context: Optional[dict] = None,
        reasoning_used: Optional[str] = None
    ) -> FeedbackModel:
        """Record user feedback for a specific user."""
        context = context or {}
        
        feedback = FeedbackModel(
            user_id=user_id,  # Set user_id
            task_id=task_id,
            task_text=task_text,
            accepted=accepted,
            context_time_available=context.get("time_available"),
            context_energy_level=context.get("energy_level"),
            context_mood=context.get("emotional_state") or context.get("mood"),
            reasoning_used=reasoning_used,
        )
        
        self.session.add(feedback)
        await self.session.commit()
        await self.session.refresh(feedback)
        
        print(f"📦 [DB] Recorded feedback: {'✅' if accepted else '❌'} - {task_text[:50]}...")
        return feedback
    
    async def get_all(self, user_id: str) -> List[FeedbackModel]:
        """Get all feedback for a specific user."""
        result = await self.session.execute(
            select(FeedbackModel)
            .where(FeedbackModel.user_id == user_id)  # Filter by user_id
            .order_by(FeedbackModel.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_insights(self, user_id: str) -> dict:
        """Get learning insights from feedback for a specific user."""
        feedback_list = await self.get_all(user_id)
        
        if not feedback_list:
            return {"insights": [], "message": "No feedback history yet"}
        
        total = len(feedback_list)
        accepted = sum(1 for f in feedback_list if f.accepted)
        
        return {
            "total_suggestions": total,
            "accepted": accepted,
            "rejected": total - accepted,
            "acceptance_rate": accepted / total if total > 0 else 0,
            "patterns": []
        }


class QuickWinHistoryRepository:
    """Repository for QuickWin history operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def record(self, user_id: str, quickwin_text: str, category: str, was_added: bool = False) -> QuickWinHistoryModel:
        """Record a quick win that was shown to a specific user."""
        entry = QuickWinHistoryModel(
            user_id=user_id,  # Set user_id
            quickwin_text=quickwin_text,
            category=category,
            was_added=was_added,
        )
        
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        
        return entry
    
    async def get_recent(self, user_id: str, hours: int = 24) -> List[str]:
        """Get quick wins shown to a specific user in the last N hours."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        result = await self.session.execute(
            select(QuickWinHistoryModel.quickwin_text)
            .where(QuickWinHistoryModel.user_id == user_id)  # Filter by user_id
            .where(QuickWinHistoryModel.shown_at >= since)
        )
        
        return [row[0] for row in result.all()]


class TokenUsageRepository:
    """Repository for Token Usage operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        user_id: str,
        agent_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        model: str,
        task_id: Optional[str] = None,
        operation_type: Optional[str] = None
    ) -> TokenUsageModel:
        """Record token usage for a user."""
        usage = TokenUsageModel(
            user_id=user_id,
            agent_name=agent_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=model,
            task_id=task_id,
            operation_type=operation_type,
        )
        
        self.session.add(usage)
        await self.session.commit()
        await self.session.refresh(usage)
        
        print(f"📊 [TOKEN USAGE] User {user_id[:8]}... | Agent: {agent_name} | Tokens: {total_tokens} ({prompt_tokens} prompt + {completion_tokens} completion)")
        return usage
    
    async def get_user_stats(self, user_id: str, days: int = 30) -> dict:
        """Get token usage statistics for a user."""
        from datetime import timedelta
        
        since = datetime.utcnow() - timedelta(days=days)
        
        # Total usage
        result = await self.session.execute(
            select(
                func.sum(TokenUsageModel.prompt_tokens).label("total_prompt"),
                func.sum(TokenUsageModel.completion_tokens).label("total_completion"),
                func.sum(TokenUsageModel.total_tokens).label("total"),
                func.count(TokenUsageModel.id).label("request_count")
            )
            .where(TokenUsageModel.user_id == user_id)
            .where(TokenUsageModel.created_at >= since)
        )
        row = result.one()
        
        # Usage by agent
        agent_result = await self.session.execute(
            select(
                TokenUsageModel.agent_name,
                func.sum(TokenUsageModel.total_tokens).label("tokens"),
                func.count(TokenUsageModel.id).label("count")
            )
            .where(TokenUsageModel.user_id == user_id)
            .where(TokenUsageModel.created_at >= since)
            .group_by(TokenUsageModel.agent_name)
        )
        by_agent = {agent: {"tokens": tokens, "count": count} for agent, tokens, count in agent_result.all()}
        
        # Usage by model
        model_result = await self.session.execute(
            select(
                TokenUsageModel.model,
                func.sum(TokenUsageModel.total_tokens).label("tokens"),
                func.count(TokenUsageModel.id).label("count")
            )
            .where(TokenUsageModel.user_id == user_id)
            .where(TokenUsageModel.created_at >= since)
            .group_by(TokenUsageModel.model)
        )
        by_model = {model: {"tokens": tokens, "count": count} for model, tokens, count in model_result.all()}
        
        return {
            "user_id": user_id,
            "period_days": days,
            "total_prompt_tokens": row.total_prompt or 0,
            "total_completion_tokens": row.total_completion or 0,
            "total_tokens": row.total or 0,
            "request_count": row.request_count or 0,
            "by_agent": by_agent,
            "by_model": by_model,
        }


class UserTokenLimitRepository:
    """Repository for User Token Limit operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_or_create(self, user_id: str, default_limit: int) -> UserTokenLimitModel:
        """Get user's token limit or create with default."""
        from datetime import datetime
        
        result = await self.session.execute(
            select(UserTokenLimitModel)
            .where(UserTokenLimitModel.user_id == user_id)
        )
        limit = result.scalar_one_or_none()
        
        current_month = datetime.utcnow().strftime("%Y-%m")
        
        if not limit:
            # Create new limit
            limit = UserTokenLimitModel(
                user_id=user_id,
                monthly_limit=default_limit,
                current_month=current_month,
                tokens_used_this_month=0,
            )
            self.session.add(limit)
            await self.session.commit()
            await self.session.refresh(limit)
        else:
            # Check if we need to reset for new month
            if limit.current_month != current_month:
                limit.current_month = current_month
                limit.tokens_used_this_month = 0
                limit.last_reset_at = datetime.utcnow()
                await self.session.commit()
                await self.session.refresh(limit)
        
        return limit
    
    async def check_limit(self, user_id: str, tokens_to_check: int, default_limit: int) -> tuple[bool, dict]:
        """
        Check if user can use tokens (without incrementing).
        
        Returns:
            (allowed: bool, limit_info: dict)
        """
        limit = await self.get_or_create(user_id, default_limit)
        
        # Check if adding tokens would exceed limit
        new_total = limit.tokens_used_this_month + tokens_to_check
        allowed = new_total <= limit.monthly_limit
        
        return allowed, limit.to_dict()
    
    async def increment_usage(self, user_id: str, tokens_to_add: int, default_limit: int) -> dict:
        """
        Increment user's token usage (called after successful API call).
        
        Returns:
            Updated limit_info dict
        """
        limit = await self.get_or_create(user_id, default_limit)
        
        limit.tokens_used_this_month += tokens_to_add
        limit.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(limit)
        
        return limit.to_dict()
    
    async def get_current_usage(self, user_id: str, default_limit: int) -> dict:
        """Get current usage for a user."""
        limit = await self.get_or_create(user_id, default_limit)
        return limit.to_dict()
    
    async def reset_monthly_usage(self, user_id: str) -> dict:
        """Reset a user's monthly token usage (admin function)."""
        result = await self.session.execute(
            select(UserTokenLimitModel)
            .where(UserTokenLimitModel.user_id == user_id)
        )
        limit = result.scalar_one_or_none()
        
        if not limit:
            raise ValueError(f"User {user_id} not found")
        
        limit.tokens_used_this_month = 0
        limit.last_reset_at = datetime.utcnow()
        limit.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(limit)
        
        print(f"🔄 [TOKEN LIMIT] Reset monthly usage for user {user_id[:8]}...")
        return limit.to_dict()
    
    async def update_limit(self, user_id: str, new_limit: int) -> dict:
        """Update a user's monthly token limit (admin function)."""
        limit = await self.get_or_create(user_id, new_limit)
        
        limit.monthly_limit = new_limit
        limit.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(limit)
        
        print(f"📊 [TOKEN LIMIT] Updated limit for user {user_id[:8]}... to {new_limit:,} tokens/month")
        return limit.to_dict()
    
    async def get_all_limits(self) -> List[UserTokenLimitModel]:
        """Get all user limits (admin function)."""
        result = await self.session.execute(
            select(UserTokenLimitModel)
            .order_by(UserTokenLimitModel.user_id)
        )
        return list(result.scalars().all())

