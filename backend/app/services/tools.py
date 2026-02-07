"""
Agent Tools - Functions the AI agent can call autonomously.
This enables tool-calling capability for the agentic system.
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Any
from pathlib import Path

from app.models import Task, UserContext, EnergyLevel, EmotionalState, TaskStatus, SubtaskStatus


# Base directories for persistence
DATA_DIR = Path(__file__).parent.parent.parent / "data"
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
    """Convert an object to be JSON serializable (handles datetime, enums, Pydantic models, etc.)."""
    if obj is None:
        return None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (EnergyLevel, EmotionalState, TaskStatus, SubtaskStatus)):
        return obj.value
    if hasattr(obj, 'model_dump'):
        # Pydantic model - convert to dict (by_alias=False to avoid NoneType errors)
        try:
            return serialize_for_json(obj.model_dump(by_alias=False))
        except TypeError:
            return serialize_for_json(obj.model_dump())
    if isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    return obj


ensure_directories()


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
            task_data = task.model_dump(by_alias=False)
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
        "priority": task.get("priority", "medium"),
        "category": serialize_for_json(task.get("category")) or "other",
        "tags": task.get("tags", []),
        "created_at": serialize_for_json(task.get("created_at")) or datetime.now().isoformat(),
        "started_at": serialize_for_json(task.get("started_at")),
        "completed_at": serialize_for_json(task.get("completed_at")),
        "estimated_minutes": task.get("estimated_minutes") or 15,
        "energy_required": serialize_for_json(task.get("energy_required")) or "medium",
        "emotional_fit": serialize_for_json(task.get("emotional_fit", [])),
        "task_type": task.get("task_type"),
        "ai_reasoning": task.get("ai_reasoning"),
        "enrichment": serialize_for_json(task.get("enrichment")),
        "times_suggested": task.get("times_suggested", 0),
        "times_accepted": task.get("times_accepted", 0),
        "times_rejected": task.get("times_rejected", 0),
        "breakdown": task.get("breakdown"),
        "feedback_history": task.get("feedback_history", []),
        # Subtask tracking
        "subtasks": serialize_for_json(task.get("subtasks", [])),
        "subtasks_generated": task.get("subtasks_generated", False),
        "is_dummy": task.get("is_dummy", False)
    }
    
    # Save to task_details folder
    with open(filepath, 'w') as f:
        json.dump(task_data, f, indent=2)
    
    # Also update/create the date-based file
    date_filepath = TASKS_DIR / f"{date}.json"
    
    if date_filepath.exists():
        with open(date_filepath, 'r') as f:
            date_data = json.load(f)
    else:
        # Create new date file
        date_data = {
            "date": date,
            "tasks": [],
            "created_at": datetime.now().isoformat()
        }
    
    # Update task in the list or add it
    tasks = date_data.get("tasks", [])
    task_found = False
    for i, t in enumerate(tasks):
        if isinstance(t, dict) and t.get("id") == task_id:
            tasks[i] = task_data
            task_found = True
            break
    
    if not task_found:
        tasks.append(task_data)
    
    date_data["tasks"] = tasks
    date_data["updated_at"] = datetime.now().isoformat()
    date_data["count"] = len(tasks)
    
    with open(date_filepath, 'w') as f:
        json.dump(date_data, f, indent=2)
    
    print(f"📁 [TOOL] Saved task to {date_filepath} (total: {len(tasks)} tasks)")
    
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
    data: dict = None,
    decision_type: str = None,
    input_context: str = None,
    reasoning_steps: list[str] = None,
    conclusion: str = None,
    confidence: float = 0.0
) -> dict:
    """Save agent's reasoning process."""
    timestamp = datetime.now()
    
    # Handle both dict-based and parameter-based calls
    if data and isinstance(data, dict):
        filename = f"{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}_{decision_type or 'reasoning'}.json"
        filepath = REASONING_DIR / filename
        data["timestamp"] = timestamp.isoformat()
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return {"success": True, "filepath": str(filepath)}
    
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
    
    return insights


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


def get_task_enrichment(task_id: str) -> dict:
    """Get enrichment data for a task."""
    enrichment_filepath = TASK_DETAILS_DIR / f"{task_id}_enrichment.json"
    
    if enrichment_filepath.exists():
        with open(enrichment_filepath, 'r') as f:
            return json.load(f)
    
    return {"error": "No enrichment found", "task_id": task_id}


def enrich_task_with_research(task_id: str, task_text: str) -> dict:
    """
    Enrich a task with additional context, resources, and questions.
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

