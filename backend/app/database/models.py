"""SQLAlchemy database models for Karma."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class TaskModel(Base):
    """Task database model."""
    __tablename__ = "tasks"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    
    # Status and priority
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    category: Mapped[str] = mapped_column(String(50), default="other")
    
    # Time tracking
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=15)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Task properties
    energy_required: Mapped[str] = mapped_column(String(20), default="medium")
    task_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Tags stored as JSON array
    tags: Mapped[Optional[str]] = mapped_column(JSON, default=list)
    
    # AI-related fields
    ai_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enrichment: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    
    # Tracking
    times_suggested: Mapped[int] = mapped_column(Integer, default=0)
    times_accepted: Mapped[int] = mapped_column(Integer, default=0)
    times_rejected: Mapped[int] = mapped_column(Integer, default=0)
    
    # Subtask management
    subtasks_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dummy: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    subtasks: Mapped[List["SubtaskModel"]] = relationship(
        "SubtaskModel",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="SubtaskModel.order"
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        from sqlalchemy.orm import object_session
        from sqlalchemy import inspect
        
        # Check if subtasks are loaded to avoid lazy loading issues in async context
        subtasks_list = []
        insp = inspect(self)
        if "subtasks" in insp.dict:
            # Subtasks are already loaded
            subtasks_list = [s.to_dict() for s in self.subtasks] if self.subtasks else []
        
        return {
            "id": self.id,
            "text": self.text,
            "date": self.date,
            "status": self.status,
            "priority": self.priority,
            "category": self.category,
            "estimated_minutes": self.estimated_minutes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "energy_required": self.energy_required,
            "task_type": self.task_type,
            "tags": self.tags or [],
            "ai_reasoning": self.ai_reasoning,
            "enrichment": self.enrichment,
            "times_suggested": self.times_suggested,
            "times_accepted": self.times_accepted,
            "times_rejected": self.times_rejected,
            "subtasks_generated": self.subtasks_generated,
            "is_dummy": self.is_dummy,
            "notes": self.notes,
            "subtasks": subtasks_list,
        }


class SubtaskModel(Base):
    """Subtask database model."""
    __tablename__ = "subtasks"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    
    # Subtask content
    text: Mapped[str] = mapped_column(Text, nullable=False)
    instruction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Status and order
    status: Mapped[str] = mapped_column(String(20), default="pending")
    order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Time estimate
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=5)
    
    # AI reasoning
    ai_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationship back to task
    task: Mapped["TaskModel"] = relationship("TaskModel", back_populates="subtasks")
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "text": self.text,
            "instruction": self.instruction,
            "status": self.status,
            "order": self.order,
            "estimated_minutes": self.estimated_minutes,
            "ai_reasoning": self.ai_reasoning,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class FeedbackModel(Base):
    """User feedback database model for learning."""
    __tablename__ = "feedback"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    task_text: Mapped[str] = mapped_column(Text, nullable=False)
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    
    # Context when feedback was given
    context_time_available: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    context_energy_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    context_mood: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    reasoning_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_text": self.task_text,
            "accepted": self.accepted,
            "context": {
                "time_available": self.context_time_available,
                "energy_level": self.context_energy_level,
                "mood": self.context_mood,
            },
            "reasoning_used": self.reasoning_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class QuickWinHistoryModel(Base):
    """Track quick wins that have been shown to avoid repetition."""
    __tablename__ = "quickwin_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quickwin_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="other")
    shown_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    was_added: Mapped[bool] = mapped_column(Boolean, default=False)
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "quickwin_text": self.quickwin_text,
            "category": self.category,
            "shown_at": self.shown_at.isoformat() if self.shown_at else None,
            "was_added": self.was_added,
        }

