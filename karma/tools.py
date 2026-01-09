"""
Agent Tools - Functions the AI agent can call autonomously.
This enables tool-calling capability for the agentic system.
"""

import os
import json
from datetime import datetime
from typing import Optional, Any
from pathlib import Path

from models import Task, UserContext, EnergyLevel, EmotionalState, TaskStatus


# Base directories for persistence
DATA_DIR = Path(__file__).parent / "data"
TASKS_DIR = DATA_DIR / "tasks"
REASONING_DIR = DATA_DIR / "reasoning"
MEMORY_DIR = DATA_DIR / "memory"
TASK_DETAILS_DIR = DATA_DIR / "task_details"


def ensure_directories():
    """Ensure all data directories exist."""
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    REASONING_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    TASK_DETAILS_DIR.mkdir(parents=True, exist_ok=True)


def serialize_for_json(obj: Any) -> Any:
    """Convert an object to be JSON serializable (handles datetime, enums, etc.)."""
    if obj is None:
        return None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (EnergyLevel, EmotionalState, TaskStatus)):
        return obj.value
    if isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    return obj


ensure_directories()


# ============================================================================
# Tool Definitions (for OpenAI function calling)
# ============================================================================

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_tasks",
            "description": "Save user's tasks to a date-based file for persistence",
            "parameters": {
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of task texts to save"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format"
                    }
                },
                "required": ["tasks", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "enrich_task_with_research",
            "description": "Enrich a task with research, probable questions, resources, and success criteria",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "The task ID to enrich"
                    },
                    "task_text": {
                        "type": "string",
                        "description": "The task text to analyze"
                    }
                },
                "required": ["task_id", "task_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_task_stats",
            "description": "Get overall task statistics including completion rate",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "load_tasks",
            "description": "Load tasks from a specific date or recent dates",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format, or 'recent' for last 7 days"
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_reasoning",
            "description": "Save the agent's reasoning process for a decision",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision_type": {
                        "type": "string",
                        "enum": ["task_analysis", "task_suggestion", "task_breakdown", "reflection"],
                        "description": "Type of decision being made"
                    },
                    "input_context": {
                        "type": "string",
                        "description": "The input/context that led to this decision"
                    },
                    "reasoning_steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Step-by-step reasoning process"
                    },
                    "conclusion": {
                        "type": "string",
                        "description": "Final conclusion/decision"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score 0-1"
                    }
                },
                "required": ["decision_type", "input_context", "reasoning_steps", "conclusion"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_user_feedback",
            "description": "Record whether user accepted or rejected a suggestion for learning",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_text": {
                        "type": "string",
                        "description": "The task that was suggested"
                    },
                    "user_context": {
                        "type": "object",
                        "description": "User's context when suggestion was made"
                    },
                    "accepted": {
                        "type": "boolean",
                        "description": "Whether user accepted the suggestion"
                    },
                    "reasoning_used": {
                        "type": "string",
                        "description": "The reasoning that was provided"
                    }
                },
                "required": ["task_text", "accepted"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_learning_insights",
            "description": "Get insights from past user feedback to improve suggestions",
            "parameters": {
                "type": "object",
                "properties": {
                    "context_type": {
                        "type": "string",
                        "enum": ["energy_level", "time_available", "emotional_state", "all"],
                        "description": "What type of context to analyze"
                    }
                },
                "required": ["context_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_task_properties",
            "description": "Analyze a task to determine its properties",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_text": {
                        "type": "string",
                        "description": "The task text to analyze"
                    }
                },
                "required": ["task_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "select_best_task",
            "description": "Select the best task from available options given user context",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_options": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "text": {"type": "string"},
                                "estimated_minutes": {"type": "integer"},
                                "energy_required": {"type": "string"}
                            }
                        },
                        "description": "Available tasks to choose from"
                    },
                    "time_available": {
                        "type": "integer",
                        "description": "Minutes available"
                    },
                    "energy_level": {
                        "type": "string",
                        "description": "User's energy level"
                    },
                    "emotional_state": {
                        "type": "string",
                        "description": "User's emotional state (optional)"
                    }
                },
                "required": ["task_options", "time_available", "energy_level"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "break_into_steps",
            "description": "Break a task into actionable steps",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_text": {
                        "type": "string",
                        "description": "The task to break down"
                    },
                    "time_available": {
                        "type": "integer",
                        "description": "Minutes available"
                    }
                },
                "required": ["task_text", "time_available"]
            }
        }
    }
]


# ============================================================================
# Tool Implementations
# ============================================================================

def save_tasks(tasks: list, date: str) -> dict:
    """Save tasks to a date-based file. Accepts list of strings, dicts, or Task objects."""
    filepath = TASKS_DIR / f"{date}.json"
    
    # Load existing tasks for this date if any
    existing_data = {"tasks": []}
    if filepath.exists():
        with open(filepath, 'r') as f:
            existing_data = json.load(f)
    
    existing_task_texts = {t.get("text", t) if isinstance(t, dict) else t for t in existing_data.get("tasks", [])}
    
    # Add new tasks with full details
    new_tasks = []
    for task in tasks:
        # Handle Task objects, dicts, and strings
        if hasattr(task, 'model_dump'):
            # It's a Pydantic model (Task)
            task_data = task.model_dump()
            task_text = task_data.get("text", "")
        elif isinstance(task, dict):
            task_data = task
            task_text = task.get("text", "")
        else:
            # It's a string
            task_text = str(task)
            task_data = None
        
        if task_text not in existing_task_texts:
            if task_data:
                # Use the full task data, serializing properly
                new_tasks.append({
                    "id": task_data.get("id", str(uuid.uuid4())),
                    "text": task_text,
                    "status": serialize_for_json(task_data.get("status", "pending")),
                    "category": serialize_for_json(task_data.get("category")),
                    "tags": task_data.get("tags", []),
                    "created_at": serialize_for_json(task_data.get("created_at")) or datetime.now().isoformat(),
                    "started_at": serialize_for_json(task_data.get("started_at")),
                    "completed_at": serialize_for_json(task_data.get("completed_at")),
                    "estimated_minutes": task_data.get("estimated_minutes"),
                    "energy_required": serialize_for_json(task_data.get("energy_required")),
                    "emotional_fit": serialize_for_json(task_data.get("emotional_fit", [])),
                    "task_type": task_data.get("task_type"),
                    "ai_reasoning": task_data.get("ai_reasoning"),
                    "enrichment": serialize_for_json(task_data.get("enrichment")),
                    "times_suggested": task_data.get("times_suggested", 0),
                    "times_accepted": task_data.get("times_accepted", 0),
                    "times_rejected": task_data.get("times_rejected", 0)
                })
            else:
                # Create a new task from string
                new_tasks.append({
                    "id": str(uuid.uuid4()),
                    "text": task_text,
                    "status": "pending",
                    "category": None,
                    "tags": [],
                    "created_at": datetime.now().isoformat(),
                    "started_at": None,
                    "completed_at": None,
                    "estimated_minutes": None,
                    "energy_required": None,
                    "task_type": None,
                    "ai_reasoning": None,
                    "times_suggested": 0,
                    "times_accepted": 0,
                    "times_rejected": 0
                })
    
    # Merge tasks
    all_tasks = existing_data.get("tasks", [])
    if isinstance(all_tasks, list) and all_tasks and isinstance(all_tasks[0], str):
        # Convert old format to new format
        all_tasks = [{"id": str(uuid.uuid4()), "text": t, "status": "pending", "created_at": datetime.now().isoformat()} for t in all_tasks]
    
    all_tasks.extend(new_tasks)
    
    data = {
        "date": date,
        "tasks": all_tasks,
        "updated_at": datetime.now().isoformat(),
        "count": len(all_tasks)
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"📁 [TOOL] Saved {len(new_tasks)} new tasks to {filepath}")
    
    return {
        "success": True,
        "filepath": str(filepath),
        "task_count": len(all_tasks),
        "new_tasks": len(new_tasks),
        "message": f"Saved {len(new_tasks)} new tasks for {date}"
    }


def save_task_with_details(task: dict, date: str) -> dict:
    """Save a single task with full details."""
    task_id = task.get("id", str(uuid.uuid4()))
    filepath = TASK_DETAILS_DIR / f"{task_id}.json"
    
    task_data = {
        "id": task_id,
        "text": task.get("text", ""),
        "date": date,
        "status": serialize_for_json(task.get("status", "pending")),
        "category": serialize_for_json(task.get("category")),
        "tags": task.get("tags", []),
        "created_at": serialize_for_json(task.get("created_at")) or datetime.now().isoformat(),
        "started_at": serialize_for_json(task.get("started_at")),
        "completed_at": serialize_for_json(task.get("completed_at")),
        "estimated_minutes": task.get("estimated_minutes"),
        "energy_required": serialize_for_json(task.get("energy_required")),
        "emotional_fit": serialize_for_json(task.get("emotional_fit", [])),
        "task_type": task.get("task_type"),
        "ai_reasoning": task.get("ai_reasoning"),
        "enrichment": serialize_for_json(task.get("enrichment")),
        "times_suggested": task.get("times_suggested", 0),
        "times_accepted": task.get("times_accepted", 0),
        "times_rejected": task.get("times_rejected", 0),
        "breakdown": task.get("breakdown"),
        "feedback_history": task.get("feedback_history", [])
    }
    
    with open(filepath, 'w') as f:
        json.dump(task_data, f, indent=2)
    
    # Also update the date-based file
    date_filepath = TASKS_DIR / f"{date}.json"
    if date_filepath.exists():
        with open(date_filepath, 'r') as f:
            date_data = json.load(f)
        
        # Update task in the list
        tasks = date_data.get("tasks", [])
        for i, t in enumerate(tasks):
            if isinstance(t, dict) and t.get("id") == task_id:
                tasks[i] = task_data
                break
        else:
            tasks.append(task_data)
        
        date_data["tasks"] = tasks
        date_data["updated_at"] = datetime.now().isoformat()
        
        with open(date_filepath, 'w') as f:
            json.dump(date_data, f, indent=2)
    
    return {"success": True, "task_id": task_id, "filepath": str(filepath)}


def update_task_status(task_id: str, status: str, date: str = None) -> dict:
    """Update a task's status."""
    # Find the task in task_details
    filepath = TASK_DETAILS_DIR / f"{task_id}.json"
    
    if filepath.exists():
        with open(filepath, 'r') as f:
            task_data = json.load(f)
        
        task_data["status"] = status
        if status == "in_progress" and not task_data.get("started_at"):
            task_data["started_at"] = datetime.now().isoformat()
        elif status == "completed":
            task_data["completed_at"] = datetime.now().isoformat()
        
        with open(filepath, 'w') as f:
            json.dump(task_data, f, indent=2)
        
        # Update in date file too
        date = date or task_data.get("date")
        if date:
            date_filepath = TASKS_DIR / f"{date}.json"
            if date_filepath.exists():
                with open(date_filepath, 'r') as f:
                    date_data = json.load(f)
                
                tasks = date_data.get("tasks", [])
                for i, t in enumerate(tasks):
                    if isinstance(t, dict) and t.get("id") == task_id:
                        tasks[i]["status"] = status
                        if status == "in_progress":
                            tasks[i]["started_at"] = task_data["started_at"]
                        elif status == "completed":
                            tasks[i]["completed_at"] = task_data["completed_at"]
                        break
                
                date_data["tasks"] = tasks
                with open(date_filepath, 'w') as f:
                    json.dump(date_data, f, indent=2)
        
        return {"success": True, "task_id": task_id, "new_status": status}
    
    return {"success": False, "error": "Task not found"}


def get_task_details(task_id: str) -> dict:
    """Get full details for a specific task."""
    # First check task_details folder
    filepath = TASK_DETAILS_DIR / f"{task_id}.json"
    
    if filepath.exists():
        with open(filepath, 'r') as f:
            task_data = json.load(f)
            # Also get enrichment if available
            enrichment = get_task_enrichment(task_id)
            if "error" not in enrichment:
                task_data["enrichment"] = enrichment
            return task_data
    
    # If not found, search in date-based files
    for date_file in sorted(TASKS_DIR.glob("*.json"), reverse=True):
        if date_file.stem.startswith("20"):  # Date files start with year
            with open(date_file, 'r') as f:
                data = json.load(f)
            
            for task in data.get("tasks", []):
                if isinstance(task, dict) and task.get("id") == task_id:
                    # Get enrichment if available
                    enrichment = get_task_enrichment(task_id)
                    if "error" not in enrichment:
                        task["enrichment"] = enrichment
                    return task
    
    return {"error": "Task not found", "task_id": task_id}


def get_all_tasks_by_date() -> dict:
    """Get all tasks organized by date."""
    all_dates = {}
    
    for filepath in sorted(TASKS_DIR.glob("*.json"), reverse=True):
        if filepath.stem.startswith("20"):  # Date files start with year
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            date = data.get("date", filepath.stem)
            tasks = data.get("tasks", [])
            
            # Convert old format if needed
            if tasks and isinstance(tasks[0], str):
                tasks = [{"text": t, "status": "pending"} for t in tasks]
            
            # Calculate stats
            stats = {
                "total": len(tasks),
                "pending": sum(1 for t in tasks if t.get("status") == "pending"),
                "in_progress": sum(1 for t in tasks if t.get("status") == "in_progress"),
                "completed": sum(1 for t in tasks if t.get("status") == "completed"),
                "skipped": sum(1 for t in tasks if t.get("status") == "skipped")
            }
            
            all_dates[date] = {
                "date": date,
                "tasks": tasks,
                "stats": stats,
                "updated_at": data.get("updated_at")
            }
    
    return all_dates


import uuid


def load_tasks(date: str) -> dict:
    """Load tasks from a specific date or recent dates."""
    if date == "recent":
        # Load last 7 days
        all_tasks = []
        for i in range(7):
            d = datetime.now().date() - timedelta(days=i)
            filepath = TASKS_DIR / f"{d.isoformat()}.json"
            if filepath.exists():
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    all_tasks.extend([
                        {"date": data["date"], "task": t}
                        for t in data.get("tasks", [])
                    ])
        return {"tasks": all_tasks, "source": "recent_7_days"}
    else:
        filepath = TASKS_DIR / f"{date}.json"
        if filepath.exists():
            with open(filepath, 'r') as f:
                return json.load(f)
        return {"tasks": [], "source": date, "message": "No tasks found for this date"}


def save_reasoning(
    decision_type: str,
    input_context: str,
    reasoning_steps: list[str],
    conclusion: str,
    confidence: float = 0.0
) -> dict:
    """Save agent's reasoning process."""
    timestamp = datetime.now()
    filename = f"{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}_{decision_type}.json"
    filepath = REASONING_DIR / filename
    
    data = {
        "timestamp": timestamp.isoformat(),
        "decision_type": decision_type,
        "input_context": input_context,
        "reasoning_steps": reasoning_steps,
        "conclusion": conclusion,
        "confidence": confidence
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Also append to daily log for easy reading
    daily_log = REASONING_DIR / f"{timestamp.strftime('%Y-%m-%d')}_log.txt"
    with open(daily_log, 'a') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"⏰ {timestamp.strftime('%H:%M:%S')} | {decision_type.upper()}\n")
        f.write(f"{'='*60}\n")
        f.write(f"📥 INPUT: {input_context}\n\n")
        f.write("🧠 REASONING:\n")
        for i, step in enumerate(reasoning_steps, 1):
            f.write(f"  {i}. {step}\n")
        f.write(f"\n✅ CONCLUSION: {conclusion}\n")
        f.write(f"📊 CONFIDENCE: {confidence:.0%}\n")
    
    print(f"💭 [TOOL] Saved reasoning to {filepath}")
    
    return {
        "success": True,
        "filepath": str(filepath),
        "daily_log": str(daily_log)
    }


def record_user_feedback(
    task_text: str,
    accepted: bool,
    task_id: Optional[str] = None,
    user_context: Optional[dict] = None,
    reasoning_used: Optional[str] = None
) -> dict:
    """Record user feedback for learning."""
    filepath = MEMORY_DIR / "feedback_history.json"
    rejected_filepath = MEMORY_DIR / "rejected_tasks.json"
    
    # Load existing feedback
    history = []
    if filepath.exists():
        with open(filepath, 'r') as f:
            history = json.load(f)
    
    # Add new feedback
    feedback = {
        "timestamp": datetime.now().isoformat(),
        "task_id": task_id,
        "task_text": task_text,
        "accepted": accepted,
        "user_context": user_context or {},
        "reasoning_used": reasoning_used
    }
    history.append(feedback)
    
    # Save updated history
    with open(filepath, 'w') as f:
        json.dump(history, f, indent=2)
    
    # Track rejected tasks separately for quick lookup
    if not accepted:
        rejected = {}
        if rejected_filepath.exists():
            with open(rejected_filepath, 'r') as f:
                rejected = json.load(f)
        
        # Key by context to track rejections per context
        context_key = f"{user_context.get('time_available', 'any')}_{user_context.get('energy_level', 'any')}"
        if context_key not in rejected:
            rejected[context_key] = []
        
        # Add to rejected list if not already there
        rejection_entry = {
            "task_id": task_id,
            "task_text": task_text,
            "rejected_at": datetime.now().isoformat(),
            "context": user_context
        }
        
        # Check if already in list
        existing_ids = [r.get("task_id") for r in rejected[context_key]]
        if task_id and task_id not in existing_ids:
            rejected[context_key].append(rejection_entry)
        elif not task_id:
            # Match by text if no ID
            existing_texts = [r.get("task_text") for r in rejected[context_key]]
            if task_text not in existing_texts:
                rejected[context_key].append(rejection_entry)
        
        with open(rejected_filepath, 'w') as f:
            json.dump(rejected, f, indent=2)
        
        print(f"📝 [TOOL] Added to rejected tasks for context: {context_key}")
    
    print(f"📝 [TOOL] Recorded feedback: {'✅ Accepted' if accepted else '❌ Rejected'} - {task_text[:50]}...")
    
    return {
        "success": True,
        "total_feedback_count": len(history),
        "acceptance_rate": sum(1 for f in history if f["accepted"]) / len(history) if history else 0
    }


def get_rejected_task_ids(time_available: int = None, energy_level: str = None) -> list[str]:
    """Get list of task IDs that were rejected for a given context."""
    rejected_filepath = MEMORY_DIR / "rejected_tasks.json"
    
    if not rejected_filepath.exists():
        return []
    
    with open(rejected_filepath, 'r') as f:
        rejected = json.load(f)
    
    rejected_ids = []
    
    # Get rejections for specific context
    context_key = f"{time_available or 'any'}_{energy_level or 'any'}"
    if context_key in rejected:
        rejected_ids.extend([r.get("task_id") for r in rejected[context_key] if r.get("task_id")])
    
    # Also get rejections from "any" contexts
    for key, rejections in rejected.items():
        if "any" in key:
            rejected_ids.extend([r.get("task_id") for r in rejections if r.get("task_id")])
    
    return list(set(rejected_ids))  # Remove duplicates


def clear_session_rejections(session_id: str = None) -> dict:
    """Clear rejections for a new session (optional - call when starting fresh)."""
    rejected_filepath = MEMORY_DIR / "rejected_tasks.json"
    
    # We don't actually clear - we just return info
    # Rejections persist to learn user preferences
    if rejected_filepath.exists():
        with open(rejected_filepath, 'r') as f:
            rejected = json.load(f)
        
        total_rejections = sum(len(v) for v in rejected.values())
        return {"total_rejections_tracked": total_rejections}
    
    return {"total_rejections_tracked": 0}


def get_learning_insights(context_type: str = "all") -> dict:
    """Analyze past feedback to improve suggestions."""
    filepath = MEMORY_DIR / "feedback_history.json"
    
    if not filepath.exists():
        return {"insights": [], "message": "No feedback history yet"}
    
    with open(filepath, 'r') as f:
        history = json.load(f)
    
    if not history:
        return {"insights": [], "message": "No feedback history yet"}
    
    insights = {
        "total_suggestions": len(history),
        "accepted": sum(1 for f in history if f["accepted"]),
        "rejected": sum(1 for f in history if not f["accepted"]),
        "acceptance_rate": sum(1 for f in history if f["accepted"]) / len(history),
        "patterns": []
    }
    
    # Analyze patterns by energy level
    if context_type in ["energy_level", "all"]:
        energy_stats = {}
        for f in history:
            energy = f.get("user_context", {}).get("energy_level", "unknown")
            if energy not in energy_stats:
                energy_stats[energy] = {"total": 0, "accepted": 0}
            energy_stats[energy]["total"] += 1
            if f["accepted"]:
                energy_stats[energy]["accepted"] += 1
        
        for energy, stats in energy_stats.items():
            if stats["total"] >= 2:
                rate = stats["accepted"] / stats["total"]
                insights["patterns"].append({
                    "type": "energy_level",
                    "value": energy,
                    "acceptance_rate": rate,
                    "sample_size": stats["total"]
                })
    
    # Analyze patterns by time
    if context_type in ["time_available", "all"]:
        time_stats = {}
        for f in history:
            time_val = f.get("user_context", {}).get("time_available", "unknown")
            if time_val not in time_stats:
                time_stats[time_val] = {"total": 0, "accepted": 0}
            time_stats[time_val]["total"] += 1
            if f["accepted"]:
                time_stats[time_val]["accepted"] += 1
        
        for time_val, stats in time_stats.items():
            if stats["total"] >= 2:
                rate = stats["accepted"] / stats["total"]
                insights["patterns"].append({
                    "type": "time_available",
                    "value": time_val,
                    "acceptance_rate": rate,
                    "sample_size": stats["total"]
                })
    
    # Find commonly rejected task types
    rejected_tasks = [f["task_text"].lower() for f in history if not f["accepted"]]
    if rejected_tasks:
        # Simple keyword analysis
        keywords = {}
        for task in rejected_tasks:
            for word in task.split():
                if len(word) > 3:
                    keywords[word] = keywords.get(word, 0) + 1
        
        common_rejected = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:5]
        insights["commonly_rejected_keywords"] = common_rejected
    
    return insights


# ============================================================================
# Tool Executor
# ============================================================================

from datetime import timedelta

def get_task_stats() -> dict:
    """Get overall task statistics for displaying in UI."""
    all_dates = get_all_tasks_by_date()
    
    total_tasks = 0
    completed_tasks = 0
    pending_tasks = 0
    in_progress_tasks = 0
    
    for date_data in all_dates.values():
        stats = date_data.get("stats", {})
        total_tasks += stats.get("total", 0)
        completed_tasks += stats.get("completed", 0)
        pending_tasks += stats.get("pending", 0)
        in_progress_tasks += stats.get("in_progress", 0)
    
    return {
        "total": total_tasks,
        "completed": completed_tasks,
        "pending": pending_tasks,
        "in_progress": in_progress_tasks,
        "completion_rate": completed_tasks / total_tasks if total_tasks > 0 else 0
    }


def enrich_task_with_research(task_id: str, task_text: str) -> dict:
    """
    Enrich a task with additional context, resources, and questions.
    This is called by the Add Task Agent after a task is added.
    """
    enrichment_filepath = TASK_DETAILS_DIR / f"{task_id}_enrichment.json"
    
    # Generate probable questions and resources based on task text
    enrichment = {
        "task_id": task_id,
        "task_text": task_text,
        "enriched_at": datetime.now().isoformat(),
        "probable_questions": [],
        "suggested_resources": [],
        "related_topics": [],
        "potential_blockers": [],
        "success_criteria": [],
        "agent_notes": ""
    }
    
    # Simple heuristic-based enrichment (AI will enhance this)
    text_lower = task_text.lower()
    
    # Generate questions based on task type
    if any(word in text_lower for word in ["email", "reply", "message", "contact"]):
        enrichment["probable_questions"] = [
            "What is the main point you want to convey?",
            "What response or action do you need from the recipient?",
            "Is there a deadline for this communication?",
            "Do you have all the information you need to respond?"
        ]
        enrichment["related_topics"] = ["communication", "email etiquette", "follow-up"]
        enrichment["success_criteria"] = ["Message sent", "Key points addressed", "Clear call-to-action included"]
    
    elif any(word in text_lower for word in ["call", "phone", "meeting", "schedule"]):
        enrichment["probable_questions"] = [
            "What is the purpose of this call/meeting?",
            "What topics need to be covered?",
            "What outcome are you hoping for?",
            "Do you need to prepare any materials?"
        ]
        enrichment["related_topics"] = ["scheduling", "meeting preparation", "agenda planning"]
        enrichment["success_criteria"] = ["Call completed", "Key topics discussed", "Next steps agreed"]
    
    elif any(word in text_lower for word in ["research", "find", "look up", "learn", "study"]):
        enrichment["probable_questions"] = [
            "What specific information are you looking for?",
            "How will you use this information?",
            "What sources would be most reliable?",
            "How much depth do you need?"
        ]
        enrichment["related_topics"] = ["research methods", "information evaluation", "note-taking"]
        enrichment["success_criteria"] = ["Key information found", "Notes organized", "Sources documented"]
    
    elif any(word in text_lower for word in ["write", "create", "draft", "document"]):
        enrichment["probable_questions"] = [
            "Who is the audience for this?",
            "What is the main message or purpose?",
            "What format or structure is needed?",
            "What examples or references might help?"
        ]
        enrichment["related_topics"] = ["writing", "documentation", "content creation"]
        enrichment["success_criteria"] = ["First draft complete", "Key points covered", "Reviewed for clarity"]
    
    elif any(word in text_lower for word in ["organize", "clean", "sort", "declutter"]):
        enrichment["probable_questions"] = [
            "What area or items need organizing?",
            "What system or structure would work best?",
            "What can be discarded or donated?",
            "How will you maintain this organization?"
        ]
        enrichment["related_topics"] = ["organization", "productivity", "minimalism"]
        enrichment["success_criteria"] = ["Area organized", "System in place", "Maintenance plan created"]
    
    elif any(word in text_lower for word in ["review", "check", "audit", "assess"]):
        enrichment["probable_questions"] = [
            "What criteria are you reviewing against?",
            "What are the key areas to focus on?",
            "What action will you take based on findings?",
            "Who else needs to see this review?"
        ]
        enrichment["related_topics"] = ["review process", "quality assurance", "feedback"]
        enrichment["success_criteria"] = ["Review completed", "Issues identified", "Recommendations made"]
    
    elif any(word in text_lower for word in ["buy", "purchase", "order", "shop"]):
        enrichment["probable_questions"] = [
            "What exactly do you need to buy?",
            "What is your budget?",
            "Where is the best place to purchase?",
            "Do you need to compare options first?"
        ]
        enrichment["related_topics"] = ["shopping", "budgeting", "comparison shopping"]
        enrichment["success_criteria"] = ["Item purchased", "Within budget", "Delivery arranged"]
    
    elif any(word in text_lower for word in ["exercise", "workout", "run", "gym", "yoga"]):
        enrichment["probable_questions"] = [
            "What type of exercise are you doing?",
            "How long will the session be?",
            "Do you have the right gear ready?",
            "What is your fitness goal?"
        ]
        enrichment["related_topics"] = ["fitness", "health", "exercise routines"]
        enrichment["success_criteria"] = ["Workout completed", "Target duration met", "Felt good after"]
    
    else:
        # Generic questions for any task
        enrichment["probable_questions"] = [
            "What is the first step to get started?",
            "What resources or tools do you need?",
            "What might block you from completing this?",
            "How will you know when it's done?"
        ]
        enrichment["related_topics"] = ["task management", "productivity", "goal setting"]
        enrichment["success_criteria"] = ["Task started", "Progress made", "Task completed"]
    
    # Add potential blockers
    enrichment["potential_blockers"] = [
        "Missing information or resources",
        "Waiting on someone else",
        "Unclear requirements",
        "Time constraints"
    ]
    
    # Save enrichment
    with open(enrichment_filepath, 'w') as f:
        json.dump(enrichment, f, indent=2)
    
    print(f"🔍 [TOOL] Enriched task: {task_text[:50]}...")
    
    return enrichment


def get_task_enrichment(task_id: str) -> dict:
    """Get enrichment data for a task."""
    enrichment_filepath = TASK_DETAILS_DIR / f"{task_id}_enrichment.json"
    
    if enrichment_filepath.exists():
        with open(enrichment_filepath, 'r') as f:
            return json.load(f)
    
    return {"error": "No enrichment found", "task_id": task_id}


TOOL_FUNCTIONS = {
    "save_tasks": save_tasks,
    "load_tasks": load_tasks,
    "save_reasoning": save_reasoning,
    "record_user_feedback": record_user_feedback,
    "get_learning_insights": get_learning_insights,
    "get_task_stats": get_task_stats,
    "enrich_task_with_research": enrich_task_with_research,
    "get_task_enrichment": get_task_enrichment,
}


def execute_tool(tool_name: str, arguments: dict) -> Any:
    """Execute a tool by name with given arguments."""
    if tool_name not in TOOL_FUNCTIONS:
        return {"error": f"Unknown tool: {tool_name}"}
    
    try:
        result = TOOL_FUNCTIONS[tool_name](**arguments)
        return result
    except Exception as e:
        return {"error": str(e)}

