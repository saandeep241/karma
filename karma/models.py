"""Data models for the Karma app."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


# ============================================================================
# Enums for structured inputs
# ============================================================================

class TimeAvailable(int, Enum):
    """Available time options in minutes."""
    FIVE = 5
    TEN = 10
    FIFTEEN = 15
    THIRTY = 30
    SIXTY = 60


class EnergyLevel(str, Enum):
    """Energy level options."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EmotionalState(str, Enum):
    """Emotional state options."""
    # Positive/Energized states
    MOTIVATED = "motivated"
    HAPPY = "happy"
    CALM = "calm"
    FOCUSED = "focused"
    CREATIVE = "creative"
    # Low energy/Negative states
    TIRED = "tired"
    SLEEPY = "sleepy"
    STRESSED = "stressed"
    ANXIOUS = "anxious"
    BORED = "bored"
    # Neutral
    NEUTRAL = "neutral"


# ============================================================================
# Task Status
# ============================================================================

class TaskStatus(str, Enum):
    """Status of a task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class TaskCategory(str, Enum):
    """Category/tag for a task - auto-assigned by AI."""
    WORK = "work"
    PERSONAL = "personal"
    HEALTH = "health"
    FINANCE = "finance"
    LEARNING = "learning"
    SOCIAL = "social"
    HOME = "home"
    ERRANDS = "errands"
    CREATIVE = "creative"
    ADMIN = "admin"
    OTHER = "other"


# ============================================================================
# Core Models
# ============================================================================

class Task(BaseModel):
    """Individual task from user's todo list."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    # AI-inferred properties (populated after analysis)
    estimated_minutes: Optional[int] = None
    energy_required: Optional[EnergyLevel] = None
    emotional_fit: Optional[list[EmotionalState]] = None
    suggested_count: int = 0  # Track how many times this was suggested
    # Auto-tagging by AI
    category: Optional[TaskCategory] = None  # work, personal, health, etc.
    tags: list[str] = []  # Additional custom tags
    # Status tracking
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    # Analysis metadata
    task_type: Optional[str] = None  # e.g., "communication", "organization"
    ai_reasoning: Optional[str] = None  # Why AI analyzed it this way
    # Enrichment data from TaskEnricher agent (web search, resources, steps)
    enrichment: Optional[dict] = None
    # History
    times_suggested: int = 0
    times_accepted: int = 0
    times_rejected: int = 0


class TaskStep(BaseModel):
    """A single step in a task breakdown."""
    step_number: int
    instruction: str
    estimated_minutes: Optional[int] = None


class TaskBreakdown(BaseModel):
    """AI-generated breakdown of a task into steps."""
    task_id: str
    task_text: str
    steps: list[TaskStep]
    total_steps: int


class TodoList(BaseModel):
    """Collection of user's tasks."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tasks: list[Task] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserContext(BaseModel):
    """User's current context for task matching."""
    time_available: TimeAvailable
    energy_level: EnergyLevel
    emotional_state: Optional[EmotionalState] = None


class TaskSuggestion(BaseModel):
    """A suggested task with reasoning."""
    task: Task
    reasoning: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    is_generic_quickwin: bool = False


class QuickWinTask(BaseModel):
    """Generic quick win task when no suitable tasks found."""
    text: str
    category: str  # e.g., "exercise", "hydration", "social"
    estimated_minutes: int = 2


# ============================================================================
# Session Models
# ============================================================================

class Session(BaseModel):
    """User session tracking."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    todo_list: Optional[TodoList] = None
    context: Optional[UserContext] = None
    suggested_task_ids: list[str] = []  # Track suggested tasks to avoid repeats
    current_task: Optional[Task] = None
    current_breakdown: Optional[TaskBreakdown] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Agent reasoning tracking
    agent_reasoning: dict = {}  # Full reasoning trace from agent
    current_reasoning: str = ""  # Latest reasoning step
    tool_calls: list[dict] = []  # Track tool calls made during session
    feedback_history: list[dict] = []  # Track user feedback on suggestions


# ============================================================================
# API Request/Response Models
# ============================================================================

class ImportTodoListRequest(BaseModel):
    """Request to import a todo list from text."""
    text_content: str = Field(
        ..., 
        description="Todo list content with one task per line"
    )


class ImportTodoListResponse(BaseModel):
    """Response after importing todo list."""
    session_id: str
    tasks_imported: int
    tasks: list[Task]


class SetContextRequest(BaseModel):
    """Request to set user context."""
    session_id: str
    time_available: TimeAvailable
    energy_level: EnergyLevel
    emotional_state: Optional[EmotionalState] = None


class GetSuggestionRequest(BaseModel):
    """Request to get a task suggestion."""
    session_id: str


class SuggestionResponse(BaseModel):
    """Response with a task suggestion."""
    suggestion: TaskSuggestion
    alternatives_available: bool
    message: str


class AcceptTaskRequest(BaseModel):
    """Request to accept a suggested task."""
    session_id: str
    task_id: str


class AcceptTaskResponse(BaseModel):
    """Response after accepting a task with breakdown."""
    task: Task
    breakdown: TaskBreakdown
    first_step: TaskStep
    message: str


class RequestAlternativeRequest(BaseModel):
    """Request for an alternative task suggestion."""
    session_id: str


# ============================================================================
# Generic Quick Win Tasks
# ============================================================================

GENERIC_QUICKWIN_TASKS = [
    QuickWinTask(
        text="Do 10 squats right where you are",
        category="exercise",
        estimated_minutes=2
    ),
    QuickWinTask(
        text="Drink a full glass of water",
        category="hydration",
        estimated_minutes=1
    ),
    QuickWinTask(
        text="Send a quick message to a friend or colleague",
        category="social",
        estimated_minutes=3
    ),
    QuickWinTask(
        text="Take 5 deep breaths and stretch your arms",
        category="exercise",
        estimated_minutes=2
    ),
    QuickWinTask(
        text="Tidy up your immediate workspace",
        category="organization",
        estimated_minutes=5
    ),
    QuickWinTask(
        text="Write down one thing you're grateful for today",
        category="mindfulness",
        estimated_minutes=2
    ),
    QuickWinTask(
        text="Step outside and get some fresh air for a minute",
        category="wellness",
        estimated_minutes=3
    ),
    QuickWinTask(
        text="Do a quick posture check and adjust how you're sitting",
        category="wellness",
        estimated_minutes=1
    ),
]

