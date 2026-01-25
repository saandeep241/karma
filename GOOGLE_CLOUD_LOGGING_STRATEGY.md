# Google Cloud Logging Strategy for Karma Application

## Overview
Yes, it's absolutely possible to push these files to **Google Cloud Logging** instead of (or in addition to) Cloud Storage. However, different types of files have different use cases, so a hybrid approach is recommended.

---

## What Should Go to Cloud Logging vs Cloud Storage

### ✅ **Best for Cloud Logging** (Event-based, time-series data)

1. **Reasoning Files** (`reasoning/`)
   - ✅ **Perfect fit** - These are audit/debugging logs
   - Event-based: Each AI decision is an event
   - Time-series: Chronological sequence of decisions
   - Searchable: Need to query "what did the AI decide when..."
   - **Recommendation**: Primary storage in Cloud Logging

2. **Application Logs** (already using Python logging)
   - ✅ **Already suitable** - Standard application logs
   - API requests, errors, warnings
   - **Recommendation**: Continue using Cloud Logging

### ⚠️ **Hybrid Approach** (Logs + Storage)

3. **Task Operations** (from `tasks/` and `task_details/`)
   - ⚠️ **Log events** for task creation/updates
   - ⚠️ **Keep files** in Cloud Storage for backup/recovery
   - **Recommendation**: Log events to Cloud Logging, keep JSON files in Storage

4. **User Feedback** (from `memory/`)
   - ⚠️ **Log events** for feedback received
   - ⚠️ **Keep files** in Cloud Storage for learning data
   - **Recommendation**: Log events to Cloud Logging, keep JSON files in Storage

### ❌ **Not Suitable for Cloud Logging** (Data files, not logs)

5. **Task Detail Files** (`task_details/`)
   - ❌ **Data files** - Not event logs
   - Large JSON structures
   - Need to be retrieved as complete objects
   - **Recommendation**: Keep in Cloud Storage only

6. **Date-based Task Files** (`tasks/YYYY-MM-DD.json`)
   - ❌ **Snapshot files** - Complete state at a point in time
   - Used for backup/recovery
   - **Recommendation**: Keep in Cloud Storage only

---

## Benefits of Using Cloud Logging

### 1. **Built-in Integration**
- Cloud Run automatically sends stdout/stderr to Cloud Logging
- No additional setup needed for basic logging
- Automatic log aggregation and retention

### 2. **Powerful Querying**
```python
# Query examples in Cloud Logging:
# - "Show all AI reasoning for task breakdowns in the last hour"
# - "Find all errors related to task enrichment"
# - "Show all user feedback events for user X"
```

### 3. **Real-time Monitoring**
- Set up alerts based on log patterns
- Create dashboards from log data
- Monitor AI decision quality in real-time

### 4. **Cost Efficiency**
- **Free tier**: 50 GB/month of logs
- **Pay-as-you-go**: $0.50 per GB after free tier
- **Retention**: 30 days default, up to 7 years
- Much cheaper than Cloud Storage for high-volume logs

### 5. **Automatic Features**
- Log-based metrics
- Error reporting
- Trace correlation
- Integration with Cloud Monitoring

---

## Implementation Strategy

### Option 1: Pure Cloud Logging (Recommended for Reasoning)

Send reasoning files directly to Cloud Logging as structured JSON logs.

**Pros:**
- No file management needed
- Automatic retention and archival
- Built-in search and query
- Real-time monitoring

**Cons:**
- Less control over individual files
- Harder to export for analysis
- Logs are append-only

### Option 2: Hybrid Approach (Recommended Overall)

**Reasoning → Cloud Logging** (primary)
- Send each reasoning event as a structured log entry
- Use Cloud Logging for queries and monitoring
- Optional: Also save to Cloud Storage for long-term archival

**Tasks/Memory → Cloud Storage** (primary)
- Keep JSON files in Cloud Storage
- Also log key events to Cloud Logging for monitoring
- Example: Log "task_created" event, but keep full task data in Storage

---

## Implementation Guide

### Step 1: Install Google Cloud Logging Library

```bash
# Add to requirements.txt
google-cloud-logging>=3.8.0
```

### Step 2: Update Logging Configuration

**File: `backend/app/logging_config.py`**

```python
"""
Enhanced logging configuration with Google Cloud Logging support.
"""

import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

# Google Cloud Logging (optional, only in production)
try:
    import google.cloud.logging
    from google.cloud.logging.handlers import CloudLoggingHandler
    GCP_LOGGING_AVAILABLE = True
except ImportError:
    GCP_LOGGING_AVAILABLE = False

# ... existing ColoredFormatter and JSONFormatter classes ...

def setup_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_file: Optional[str] = None,
    use_cloud_logging: bool = False
) -> logging.Logger:
    """
    Setup comprehensive logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to also log to a file
        log_file: Custom log file path
        use_cloud_logging: Whether to send logs to Google Cloud Logging
    """
    logger = logging.getLogger("karma")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()
    
    # Console handler (always)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(ColoredFormatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    ))
    logger.addHandler(console_handler)
    
    # Google Cloud Logging handler (if enabled and available)
    if use_cloud_logging and GCP_LOGGING_AVAILABLE:
        try:
            client = google.cloud.logging.Client()
            cloud_handler = CloudLoggingHandler(client, name="karma-backend")
            cloud_handler.setLevel(logging.INFO)  # Only INFO and above to Cloud
            cloud_handler.setFormatter(JSONFormatter())
            logger.addHandler(cloud_handler)
            logger.info("✅ Google Cloud Logging enabled")
        except Exception as e:
            logger.warning(f"⚠️ Failed to setup Cloud Logging: {e}")
    
    # File handler (for local development)
    if log_to_file and not use_cloud_logging:
        # ... existing file handler code ...
        pass
    
    logger.propagate = False
    return logger
```

### Step 3: Create Reasoning Logger

**File: `backend/app/services/reasoning_logger.py`** (new file)

```python
"""
Dedicated logger for AI reasoning events to Google Cloud Logging.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

from app.logging_config import get_logger

# Create dedicated logger for reasoning
reasoning_logger = get_logger("ai.reasoning")


def log_reasoning_event(
    decision_type: str,
    input_context: str,
    reasoning_steps: List[str],
    conclusion: str,
    confidence: float,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an AI reasoning event to Google Cloud Logging.
    
    This replaces the file-based save_reasoning() function when using Cloud Logging.
    
    Args:
        decision_type: Type of decision (e.g., "TaskAnalyzer_analysis", "Breakdown_breakdown")
        input_context: What the agent was considering
        reasoning_steps: Step-by-step reasoning process
        conclusion: Final decision/outcome
        confidence: Confidence level (0.0-1.0)
        metadata: Additional structured data (task_id, user_id, etc.)
    """
    # Create structured log entry
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "decision_type": decision_type,
        "input_context": input_context,
        "reasoning_steps": reasoning_steps,
        "conclusion": conclusion,
        "confidence": confidence,
        "metadata": metadata or {}
    }
    
    # Determine log level based on decision type
    if "error" in decision_type.lower() or confidence < 0.5:
        level = logging.WARNING
    else:
        level = logging.INFO
    
    # Log with structured data
    reasoning_logger.log(
        level,
        f"[{decision_type}] {conclusion}",
        extra={
            "json_fields": log_data,  # Cloud Logging will parse this
            "decision_type": decision_type,
            "confidence": confidence,
            "reasoning_steps_count": len(reasoning_steps)
        }
    )


def log_task_operation(
    operation: str,  # "created", "updated", "deleted", "enriched"
    task_id: str,
    task_text: str,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log task operations to Cloud Logging for monitoring.
    
    Args:
        operation: Type of operation
        task_id: Task identifier
        task_text: Task description
        user_id: User who performed the operation
        metadata: Additional data (status, priority, etc.)
    """
    task_logger = get_logger("tasks.operations")
    
    task_logger.info(
        f"Task {operation}: {task_text[:50]}...",
        extra={
            "json_fields": {
                "operation": operation,
                "task_id": task_id,
                "task_text": task_text,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                **metadata or {}
            }
        }
    )


def log_user_feedback(
    task_id: str,
    task_text: str,
    accepted: bool,
    user_id: str,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log user feedback events to Cloud Logging.
    
    Args:
        task_id: Task identifier
        task_text: Task description
        accepted: Whether user accepted the suggestion
        user_id: User identifier
        context: User context when feedback was given
    """
    feedback_logger = get_logger("user.feedback")
    
    level = logging.INFO if accepted else logging.WARNING
    
    feedback_logger.log(
        level,
        f"User {'accepted' if accepted else 'rejected'} task suggestion",
        extra={
            "json_fields": {
                "task_id": task_id,
                "task_text": task_text,
                "accepted": accepted,
                "user_id": user_id,
                "context": context or {},
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )
```

### Step 4: Update Tools to Use Cloud Logging

**File: `backend/app/services/tools.py`**

Update `save_reasoning()` to use Cloud Logging:

```python
from app.services.reasoning_logger import log_reasoning_event
from app.config import get_settings

def save_reasoning(
    data: dict = None,
    decision_type: str = None,
    input_context: str = None,
    reasoning_steps: list[str] = None,
    conclusion: str = None,
    confidence: float = 0.0
) -> dict:
    """Save agent's reasoning process to Cloud Logging and optionally to file."""
    settings = get_settings()
    
    # Always log to Cloud Logging (if enabled)
    if settings.use_cloud_logging:
        log_reasoning_event(
            decision_type=decision_type or data.get("decision_type", "reasoning"),
            input_context=input_context or data.get("input_context", ""),
            reasoning_steps=reasoning_steps or data.get("reasoning_steps", []),
            conclusion=conclusion or data.get("conclusion", ""),
            confidence=confidence or data.get("confidence", 0.0),
            metadata={
                "task_id": data.get("task_id") if data else None,
                "user_id": data.get("user_id") if data else None
            }
        )
    
    # Optionally also save to file (for local dev or backup)
    if settings.save_reasoning_to_file:
        # ... existing file saving code ...
        pass
    
    return {"success": True, "logged_to_cloud": settings.use_cloud_logging}
```

### Step 5: Update Configuration

**File: `backend/app/config.py`**

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Cloud Logging settings
    use_cloud_logging: bool = False  # Enable Cloud Logging in production
    save_reasoning_to_file: bool = True  # Also save to files (for backup)
    
    # Cloud Storage settings (for data files)
    use_cloud_storage: bool = False
    gcs_bucket_name: str = "karma-app-data"
```

### Step 6: Environment Variables

**For Cloud Run deployment:**

```bash
# Enable Cloud Logging
USE_CLOUD_LOGGING=true

# Optional: Also save to files for backup
SAVE_REASONING_TO_FILE=false  # Set to false to use only Cloud Logging

# Cloud Storage (for data files)
USE_CLOUD_STORAGE=true
GCS_BUCKET_NAME=karma-app-data
```

---

## Cloud Logging Query Examples

Once logs are in Cloud Logging, you can query them:

### 1. Find All AI Reasoning Events
```
resource.type="cloud_run_revision"
jsonPayload.decision_type="TaskAnalyzer_analysis"
```

### 2. Find Low Confidence Decisions
```
resource.type="cloud_run_revision"
jsonPayload.decision_type=~"Breakdown|Enrichment"
jsonPayload.confidence<0.7
```

### 3. Find All Task Creations
```
resource.type="cloud_run_revision"
jsonPayload.operation="created"
jsonPayload.task_id!=""
```

### 4. Find User Feedback Patterns
```
resource.type="cloud_run_revision"
jsonPayload.accepted=false
```

### 5. Find Errors in Reasoning
```
resource.type="cloud_run_revision"
severity>=ERROR
jsonPayload.decision_type!=""
```

---

## Cost Comparison

### Cloud Logging
- **Free tier**: 50 GB/month
- **After free tier**: $0.50/GB
- **Retention**: 30 days (default), up to 7 years
- **Estimated cost**: 
  - Reasoning logs: ~5-15 MB/month = **FREE** (within free tier)
  - Even at 100 MB/month = **$0.05/month**

### Cloud Storage
- **Standard storage**: $0.020/GB/month
- **Operations**: $0.05 per 10,000 operations
- **Estimated cost**: 
  - 8-28 MB/month = **$0.0002-0.0006/month**
  - Very cheap, but less queryable

### Recommendation
- Use **Cloud Logging** for reasoning (free tier covers it)
- Use **Cloud Storage** for data files (tasks, task_details)
- **Total cost**: Essentially free for small-medium usage

---

## Best Practices

### 1. Structured Logging
Always use structured JSON in logs:
```python
logger.info("Task created", extra={
    "json_fields": {
        "task_id": "...",
        "user_id": "...",
        "operation": "created"
    }
})
```

### 2. Log Levels
- **DEBUG**: Detailed debugging info
- **INFO**: Normal operations (reasoning events, task operations)
- **WARNING**: Low confidence decisions, rejected suggestions
- **ERROR**: Failures, exceptions
- **CRITICAL**: System failures

### 3. Don't Log Sensitive Data
- Never log passwords, API keys, or PII
- Sanitize user input in logs
- Use log redaction if needed

### 4. Log Retention
- Set appropriate retention based on needs
- 30 days for most logs
- 90 days for reasoning (for analysis)
- 1 year for compliance/audit logs

### 5. Monitor Log Volume
- Set up alerts for excessive log volume
- Use log-based metrics to track patterns
- Archive old logs if needed

---

## Migration Path

### Phase 1: Add Cloud Logging (Non-Breaking)
1. Install `google-cloud-logging`
2. Update logging config to support Cloud Logging
3. Add reasoning logger
4. Keep existing file-based saving
5. Deploy and verify logs appear in Cloud Logging

### Phase 2: Switch Primary Storage
1. Make Cloud Logging primary for reasoning
2. Keep file saving as backup (optional)
3. Update queries to use Cloud Logging
4. Monitor and adjust

### Phase 3: Optimize
1. Remove file-based saving if not needed
2. Set up log-based metrics
3. Create dashboards
4. Set up alerts

---

## Example: Complete Reasoning Log Entry

```json
{
  "timestamp": "2026-01-17T21:10:03.357040Z",
  "severity": "INFO",
  "resource": {
    "type": "cloud_run_revision",
    "labels": {
      "service_name": "karma-backend",
      "revision_name": "karma-backend-00001-abc"
    }
  },
  "jsonPayload": {
    "timestamp": "2026-01-17T21:10:03.357040",
    "decision_type": "Breakdown_breakdown",
    "input_context": "Task: Do a math worksheet, Time: 30min",
    "reasoning_steps": [
      "[observation] Breaking down: Do a math worksheet (30min)",
      "[conclusion] Created 5 subtasks, total 30min"
    ],
    "conclusion": "Created 5 subtasks totaling 30min",
    "confidence": 0.85,
    "metadata": {
      "task_id": "006f7e5a-2e62-483e-86ca-b4b9b4fe0a87",
      "user_id": "user_123"
    }
  },
  "labels": {
    "decision_type": "Breakdown_breakdown",
    "confidence": "0.85"
  }
}
```

---

## Summary

### ✅ Use Cloud Logging For:
- **Reasoning events** (primary storage)
- **Application logs** (API, errors, warnings)
- **Task operation events** (created, updated, deleted)
- **User feedback events** (accepted, rejected)

### ✅ Use Cloud Storage For:
- **Task detail files** (complete task data)
- **Date-based task files** (backup snapshots)
- **Memory/feedback JSON files** (learning data)
- **Large enrichment data** (if needed for export)

### 💡 Hybrid Approach Benefits:
- **Best of both worlds**: Queryable logs + persistent data files
- **Cost effective**: Free tier covers most logging needs
- **Flexible**: Can query logs in real-time, export data when needed
- **Scalable**: Cloud Logging handles high volume automatically

---

**Last Updated**: 2026-01-17  
**Document Version**: 1.0
