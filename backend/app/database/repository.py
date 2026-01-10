"""Database repository with all CRUD operations for Karma."""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import TaskModel, SubtaskModel, FeedbackModel, QuickWinHistoryModel


class TaskRepository:
    """Repository for Task operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, task_data: dict) -> TaskModel:
        """Create a new task."""
        task_id = task_data.get("id") or str(uuid.uuid4())
        
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
        )
        task = result.scalar_one()
        
        print(f"📦 [DB] Created task: {task.text[:50]}...")
        return task
    
    async def get_by_id(self, task_id: str) -> Optional[TaskModel]:
        """Get a task by ID with subtasks."""
        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.subtasks))
            .where(TaskModel.id == task_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self) -> List[TaskModel]:
        """Get all tasks with subtasks."""
        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.subtasks))
            .order_by(TaskModel.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_by_date(self, date: str) -> List[TaskModel]:
        """Get tasks for a specific date."""
        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.subtasks))
            .where(TaskModel.date == date)
            .order_by(TaskModel.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_by_status(self, status: str) -> List[TaskModel]:
        """Get tasks by status."""
        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.subtasks))
            .where(TaskModel.status == status)
            .order_by(TaskModel.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_recent(self, days: int = 7) -> List[TaskModel]:
        """Get tasks from the last N days."""
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.subtasks))
            .where(TaskModel.date >= start_date)
            .order_by(TaskModel.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_tasks_by_date_grouped(self) -> dict:
        """Get all tasks organized by date."""
        tasks = await self.get_all()
        
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
    
    async def update(self, task_id: str, updates: dict) -> Optional[TaskModel]:
        """Update a task."""
        task = await self.get_by_id(task_id)
        if not task:
            return None
        
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
    
    async def update_status(self, task_id: str, status: str) -> Optional[TaskModel]:
        """Update a task's status."""
        task = await self.get_by_id(task_id)
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
    
    async def delete(self, task_id: str) -> bool:
        """Delete a task."""
        result = await self.session.execute(
            delete(TaskModel).where(TaskModel.id == task_id)
        )
        await self.session.commit()
        
        deleted = result.rowcount > 0
        if deleted:
            print(f"📦 [DB] Deleted task: {task_id}")
        return deleted
    
    async def delete_all(self) -> int:
        """Delete all tasks."""
        result = await self.session.execute(delete(TaskModel))
        await self.session.commit()
        
        print(f"📦 [DB] Deleted all tasks: {result.rowcount}")
        return result.rowcount
    
    async def get_stats(self) -> dict:
        """Get overall task statistics."""
        result = await self.session.execute(
            select(
                func.count(TaskModel.id).label("total"),
                func.sum(func.cast(TaskModel.status == "completed", Integer)).label("completed"),
                func.sum(func.cast(TaskModel.status == "pending", Integer)).label("pending"),
                func.sum(func.cast(TaskModel.status == "in_progress", Integer)).label("in_progress"),
            )
        )
        row = result.one()
        
        total = row.total or 0
        completed = row.completed or 0
        pending = row.pending or 0
        in_progress = row.in_progress or 0
        
        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "in_progress": in_progress,
            "completion_rate": completed / total if total > 0 else 0
        }


# Need to import Integer for the cast
from sqlalchemy import Integer


class SubtaskRepository:
    """Repository for Subtask operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, task_id: str, subtask_data: dict) -> SubtaskModel:
        """Create a new subtask."""
        subtask_id = subtask_data.get("id") or str(uuid.uuid4())
        
        subtask = SubtaskModel(
            id=subtask_id,
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
    
    async def create_many(self, task_id: str, subtasks_data: List[dict]) -> List[SubtaskModel]:
        """Create multiple subtasks for a task."""
        subtasks = []
        for i, data in enumerate(subtasks_data):
            data["order"] = data.get("order", i)
            subtask = await self.create(task_id, data)
            subtasks.append(subtask)
        return subtasks
    
    async def get_by_task(self, task_id: str) -> List[SubtaskModel]:
        """Get all subtasks for a task."""
        result = await self.session.execute(
            select(SubtaskModel)
            .where(SubtaskModel.task_id == task_id)
            .order_by(SubtaskModel.order)
        )
        return list(result.scalars().all())
    
    async def update_status(self, subtask_id: str, status: str) -> Optional[SubtaskModel]:
        """Update a subtask's status."""
        result = await self.session.execute(
            select(SubtaskModel).where(SubtaskModel.id == subtask_id)
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
        task_text: str,
        accepted: bool,
        task_id: Optional[str] = None,
        context: Optional[dict] = None,
        reasoning_used: Optional[str] = None
    ) -> FeedbackModel:
        """Record user feedback."""
        context = context or {}
        
        feedback = FeedbackModel(
            task_id=task_id,
            task_text=task_text,
            accepted=accepted,
            context_time_available=context.get("time_available"),
            context_energy_level=context.get("energy_level"),
            context_mood=context.get("mood"),
            reasoning_used=reasoning_used,
        )
        
        self.session.add(feedback)
        await self.session.commit()
        await self.session.refresh(feedback)
        
        print(f"📦 [DB] Recorded feedback: {'✅' if accepted else '❌'} - {task_text[:50]}...")
        return feedback
    
    async def get_all(self) -> List[FeedbackModel]:
        """Get all feedback."""
        result = await self.session.execute(
            select(FeedbackModel).order_by(FeedbackModel.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_insights(self) -> dict:
        """Get learning insights from feedback."""
        feedback_list = await self.get_all()
        
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
    
    async def record(self, quickwin_text: str, category: str, was_added: bool = False) -> QuickWinHistoryModel:
        """Record a quick win that was shown."""
        entry = QuickWinHistoryModel(
            quickwin_text=quickwin_text,
            category=category,
            was_added=was_added,
        )
        
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        
        return entry
    
    async def get_recent(self, hours: int = 24) -> List[str]:
        """Get quick wins shown in the last N hours."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        result = await self.session.execute(
            select(QuickWinHistoryModel.quickwin_text)
            .where(QuickWinHistoryModel.shown_at >= since)
        )
        
        return [row[0] for row in result.all()]

