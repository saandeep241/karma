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
from app.services.storage_service import get_storage_service

# Storage service instance
storage = get_storage_service()


def serialize_for_json(obj: Any) -> Any:
    """Convert an object to be JSON serializable (handles datetime, enums, Pydantic models, etc.)."""
    if obj is None:
        return None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (EnergyLevel, EmotionalState, TaskStatus, SubtaskStatus)):
        return obj.value
    if hasattr(obj, 'model_dump'):
        # Pydantic model - convert to dict first
        return serialize_for_json(obj.model_dump())
    if isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    return obj


# ============================================================================
# Tool Implementations
# ============================================================================

def save_tasks(tasks: list, date: str) -> dict:
    """Save tasks to a date-based file. Accepts list of strings, dicts, or Task objects."""
    filename = f"{date}.json"
    
    # Load existing tasks for this date if any
    existing_data = storage.read_json("tasks", filename) or {"tasks": []}
    
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
    
    success = storage.write_json("tasks", filename, data)
    
    if success:
        print(f"📁 [TOOL] Saved {len(new_tasks)} new tasks for {date}")
        return {
            "success": True,
            "filepath": f"tasks/{filename}",
            "task_count": len(all_tasks),
            "new_tasks": len(new_tasks),
            "message": f"Saved {len(new_tasks)} new tasks for {date}"
        }
    else:
        return {
            "success": False,
            "error": "Failed to save tasks",
            "task_count": len(all_tasks),
            "new_tasks": len(new_tasks)
        }


def save_task_with_details(task: dict, date: str) -> dict:
    """Save a single task with full details."""
    task_id = task.get("id", str(uuid.uuid4()))
    task_filename = f"{task_id}.json"
    
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
    storage.write_json("task_details", task_filename, task_data)
    
    # Also update/create the date-based file
    date_filename = f"{date}.json"
    date_data = storage.read_json("tasks", date_filename)
    
    if not date_data:
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
    
    storage.write_json("tasks", date_filename, date_data)
    
    print(f"📁 [TOOL] Saved task for {date} (total: {len(tasks)} tasks)")
    
    return {"success": True, "task_id": task_id, "filepath": f"task_details/{task_filename}"}


def update_task_status(task_id: str, status: str, date: str = None) -> dict:
    """Update a task's status."""
    # Find the task in task_details
    task_filename = f"{task_id}.json"
    task_data = storage.read_json("task_details", task_filename)
    
    if task_data:
        task_data["status"] = status
        if status == "in_progress" and not task_data.get("started_at"):
            task_data["started_at"] = datetime.now().isoformat()
        elif status == "completed":
            task_data["completed_at"] = datetime.now().isoformat()
        
        storage.write_json("task_details", task_filename, task_data)
        
        # Update in date file too
        date = date or task_data.get("date")
        if date:
            date_filename = f"{date}.json"
            date_data = storage.read_json("tasks", date_filename)
            
            if date_data:
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
                storage.write_json("tasks", date_filename, date_data)
        
        return {"success": True, "task_id": task_id, "new_status": status}
    
    return {"success": False, "error": "Task not found"}


def get_task_details(task_id: str) -> dict:
    """Get full details for a specific task."""
    # First check task_details folder
    task_filename = f"{task_id}.json"
    task_data = storage.read_json("task_details", task_filename)
    
    if task_data:
        # Also get enrichment if available
        enrichment = get_task_enrichment(task_id)
        if "error" not in enrichment:
            task_data["enrichment"] = enrichment
        return task_data
    
    # Note: Files are only available when Cloud Storage is enabled.
    # When disabled, we can't search files (they're not written).
    # The database should be the primary source via db_service.get_task()
    
    return {"error": "Task not found", "task_id": task_id}


def get_all_tasks_by_date() -> dict:
    """
    Get all tasks organized by date.
    
    Note: This function reads from file storage, which is only available when
    Cloud Storage is enabled. The database is the primary source of truth.
    When Cloud Storage is disabled, files are not written, so this returns empty.
    """
    all_dates = {}
    
    # Files are only written when Cloud Storage is enabled
    # When disabled, return empty (database is the source of truth)
    if not storage.is_cloud_storage_enabled:
        return all_dates
    
    # For Cloud Storage, we'd need to list files (expensive operation)
    # For now, return empty - this function is mainly for backward compatibility
    # The database should be used as the primary source via db_service
    # TODO: Implement efficient file listing for Cloud Storage if needed
    return all_dates


def load_tasks(date: str) -> dict:
    """Load tasks from a specific date or recent dates."""
    if date == "recent":
        # Load last 7 days
        all_tasks = []
        for i in range(7):
            d = datetime.now().date() - timedelta(days=i)
            filename = f"{d.isoformat()}.json"
            data = storage.read_json("tasks", filename)
            if data:
                all_tasks.extend([
                    {"date": data["date"], "task": t}
                    for t in data.get("tasks", [])
                ])
        return {"tasks": all_tasks, "source": "recent_7_days"}
    else:
        filename = f"{date}.json"
        data = storage.read_json("tasks", filename)
        if data:
            return data
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
        data["timestamp"] = timestamp.isoformat()
        success = storage.write_json("reasoning", filename, data)
        if success:
            return {"success": True, "filepath": f"reasoning/{filename}"}
        return {"success": False, "error": "Failed to save reasoning"}
    
    filename = f"{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}_{decision_type}.json"
    
    data = {
        "timestamp": timestamp.isoformat(),
        "decision_type": decision_type,
        "input_context": input_context,
        "reasoning_steps": reasoning_steps,
        "conclusion": conclusion,
        "confidence": confidence
    }
    
    success = storage.write_json("reasoning", filename, data)
    
    # Also append to daily log for easy reading
    daily_log_filename = f"{timestamp.strftime('%Y-%m-%d')}_log.txt"
    log_content = f"\n{'='*60}\n"
    log_content += f"⏰ {timestamp.strftime('%H:%M:%S')} | {decision_type.upper()}\n"
    log_content += f"{'='*60}\n"
    log_content += f"📥 INPUT: {input_context}\n\n"
    log_content += "🧠 REASONING:\n"
    for i, step in enumerate(reasoning_steps, 1):
        log_content += f"  {i}. {step}\n"
    log_content += f"\n✅ CONCLUSION: {conclusion}\n"
    log_content += f"📊 CONFIDENCE: {confidence:.0%}\n"
    
    storage.append_to_file("reasoning", daily_log_filename, log_content)
    
    print(f"💭 [TOOL] Saved reasoning: {filename}")
    
    return {
        "success": success,
        "filepath": f"reasoning/{filename}",
        "daily_log": f"reasoning/{daily_log_filename}"
    }


def record_user_feedback(
    task_text: str,
    accepted: bool,
    task_id: Optional[str] = None,
    user_context: Optional[dict] = None,
    reasoning_used: Optional[str] = None
) -> dict:
    """Record user feedback for learning."""
    feedback_filename = "feedback_history.json"
    rejected_filename = "rejected_tasks.json"
    
    # Load existing feedback
    history = storage.read_json("memory", feedback_filename) or []
    
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
    storage.write_json("memory", feedback_filename, history)
    
    # Track rejected tasks separately for quick lookup
    if not accepted:
        rejected = storage.read_json("memory", rejected_filename) or {}
        
        # Key by context to track rejections per context
        context_key = f"{user_context.get('time_available', 'any') if user_context else 'any'}_{user_context.get('energy_level', 'any') if user_context else 'any'}"
        if context_key not in rejected:
            rejected[context_key] = []
        
        # Add to rejected list if not already there
        rejection_entry = {
            "task_id": task_id,
            "task_text": task_text,
            "rejected_at": datetime.now().isoformat(),
            "context": user_context or {}
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
        
        storage.write_json("memory", rejected_filename, rejected)
        
        print(f"📝 [TOOL] Added to rejected tasks for context: {context_key}")
    
    print(f"📝 [TOOL] Recorded feedback: {'✅ Accepted' if accepted else '❌ Rejected'} - {task_text[:50]}...")
    
    return {
        "success": True,
        "total_feedback_count": len(history),
        "acceptance_rate": sum(1 for f in history if f["accepted"]) / len(history) if history else 0
    }


def get_learning_insights(context_type: str = "all") -> dict:
    """Analyze past feedback to improve suggestions."""
    history = storage.read_json("memory", "feedback_history.json")
    
    if not history:
        return {"insights": [], "message": "No feedback history yet"}
    
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
    enrichment_filename = f"{task_id}_enrichment.json"
    enrichment_data = storage.read_json("task_details", enrichment_filename)
    
    if enrichment_data:
        return enrichment_data
    
    return {"error": "No enrichment found", "task_id": task_id}


def enrich_task_with_research(task_id: str, task_text: str) -> dict:
    """
    Enrich a task with additional context, resources, and questions.
    """
    enrichment_filename = f"{task_id}_enrichment.json"
    
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
    storage.write_json("task_details", enrichment_filename, enrichment)
    
    print(f"🔍 [TOOL] Enriched task: {task_text[:50]}...")
    
    return enrichment

