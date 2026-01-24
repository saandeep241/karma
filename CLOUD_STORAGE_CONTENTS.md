# Cloud Storage Contents for Karma Application

## Overview
When migrating to GCP, the following file-based data will be stored in **Cloud Storage** instead of the local filesystem. The database (currently SQLite) will be migrated to **Cloud SQL PostgreSQL**, so it's not included here.

---

## Directory Structure in Cloud Storage

The Cloud Storage bucket will mirror the current local file structure:

```
gs://karma-app-data/
├── tasks/              # Date-based task files
├── reasoning/          # AI agent reasoning traces
├── memory/             # User feedback and learning data
└── task_details/       # Individual task detail files
```

---

## 1. Tasks Directory (`tasks/`)

### Purpose
Stores date-based JSON files containing all tasks for a specific date.

### File Naming Pattern
- Format: `YYYY-MM-DD.json`
- Example: `2026-01-17.json`, `2026-01-16.json`

### File Contents
Each file contains:
- **Date metadata**: The date these tasks belong to
- **Tasks array**: List of all tasks for that date
- **Task properties**:
  - Task ID, text, status, priority, category
  - Timestamps (created_at, started_at, completed_at)
  - Time estimates (estimated_minutes)
  - Energy requirements and emotional fit
  - AI reasoning and enrichment data
  - Tags, subtasks, feedback history
  - Task type and enrichment details

### Example Structure
```json
{
  "date": "2026-01-17",
  "tasks": [
    {
      "id": "c6262c93-dbaa-4745-8e46-cf40c3967a23",
      "text": "See the exercise list for today",
      "status": "pending",
      "priority": "medium",
      "category": "health",
      "tags": ["exercise", "fitness"],
      "estimated_minutes": 5,
      "energy_required": "low",
      "ai_reasoning": "...",
      "enrichment": { ... },
      "subtasks": [ ... ],
      ...
    }
  ],
  "updated_at": "2026-01-17T21:10:03.361171",
  "count": 7
}
```

### Storage Size
- **Per file**: ~5-50 KB (depending on number of tasks)
- **Growth rate**: 1 file per day
- **Estimated monthly**: ~1-2 MB

### Access Pattern
- **Read**: Frequently (when loading tasks for a date)
- **Write**: When tasks are added/updated for a date
- **Update frequency**: Multiple times per day

---

## 2. Reasoning Directory (`reasoning/`)

### Purpose
Stores AI agent reasoning traces - detailed logs of how the AI agents made decisions.

### File Naming Pattern
- Format: `YYYY-MM-DD_HH-MM-SS_{DecisionType}_{Action}.json`
- Examples:
  - `2026-01-17_21-10-03_Breakdown_breakdown.json`
  - `2026-01-17_21-09-46_TaskEnricher_enrichment.json`
  - `2026-01-17_21-09-36_TaskAnalyzer_analysis.json`
  - `2026-01-17_21-14-49_QuickWin_generation.json`

### Decision Types
- **TaskAnalyzer_analysis**: Task analysis decisions
- **TaskEnricher_enrichment**: Task enrichment decisions
- **Breakdown_breakdown**: Task breakdown/subtask generation
- **QuickWin_generation**: Quick win generation decisions
- **TaskSuggester_suggestion**: Task suggestion matching

### File Contents
Each reasoning file contains:
- **Timestamp**: When the decision was made
- **Decision type**: What kind of decision (analysis, enrichment, etc.)
- **Input context**: What the agent was considering
- **Reasoning steps**: Step-by-step thought process
- **Conclusion**: Final decision/outcome
- **Confidence**: Confidence level (0.0-1.0)

### Example Structure
```json
{
  "timestamp": "2026-01-17T21:10:03.357040",
  "decision_type": "Breakdown_breakdown",
  "input_context": "Task: Do a math worksheet, Time: 30min",
  "reasoning_steps": [
    "[observation] Breaking down: Do a math worksheet (30min)",
    "[conclusion] Created 5 subtasks, total 30min"
  ],
  "conclusion": "Created 5 subtasks totaling 30min",
  "confidence": 0.85
}
```

### Additional Files
- **Daily log files**: `YYYY-MM-DD_log.txt` - Human-readable daily summaries
  - Format: Plain text with timestamps and reasoning summaries
  - Purpose: Easy debugging and review of AI decisions

### Storage Size
- **Per file**: ~1-5 KB
- **Growth rate**: 10-50 files per day (depending on usage)
- **Estimated monthly**: ~5-15 MB

### Access Pattern
- **Read**: Occasionally (for debugging, analysis)
- **Write**: Every time an AI agent makes a decision
- **Update frequency**: Very frequent (multiple times per user action)

---

## 3. Memory Directory (`memory/`)

### Purpose
Stores user feedback and learning data to improve future suggestions.

### Files

#### `feedback_history.json`
- **Purpose**: Complete history of user feedback on task suggestions
- **Contents**: Array of feedback entries
- **Structure**:
```json
[
  {
    "timestamp": "2026-01-17T21:10:03.357040",
    "task_id": "c6262c93-dbaa-4745-8e46-cf40c3967a23",
    "task_text": "See the exercise list for today",
    "accepted": true,
    "user_context": {
      "time_available": 30,
      "energy_level": "medium",
      "mood": "neutral"
    },
    "reasoning_used": "AI reasoning that led to suggestion"
  }
]
```

#### `rejected_tasks.json`
- **Purpose**: Track tasks that were rejected, organized by context
- **Contents**: Dictionary keyed by context (time_available + energy_level)
- **Structure**:
```json
{
  "30_medium": [
    {
      "task_id": "...",
      "task_text": "...",
      "rejected_at": "...",
      "context": { ... }
    }
  ]
}
```

### Storage Size
- **Per file**: ~10-100 KB (grows with usage)
- **Growth rate**: Slow (only when user provides feedback)
- **Estimated monthly**: ~100-500 KB

### Access Pattern
- **Read**: When generating suggestions (to learn from past feedback)
- **Write**: When user accepts/rejects a suggestion
- **Update frequency**: Moderate (whenever user provides feedback)

---

## 4. Task Details Directory (`task_details/`)

### Purpose
Stores detailed information for individual tasks, including enrichment data.

### File Naming Pattern
- Format: `{task_id}.json` or `{task_id}_enrichment.json`
- Examples:
  - `006f7e5a-2e62-483e-86ca-b4b9b4fe0a87.json`
  - `006f7e5a-2e62-483e-86ca-b4b9b4fe0a87_enrichment.json`

### File Contents

#### Main Task File (`{task_id}.json`)
Contains complete task information:
- Task metadata (id, text, date, status)
- Time tracking (estimated, started, completed)
- AI analysis (reasoning, enrichment)
- Subtasks and breakdowns
- Feedback history
- Tags and categories

#### Enrichment File (`{task_id}_enrichment.json`)
Contains detailed enrichment data:
- Steps to complete the task
- Probable questions
- Suggested resources
- Potential blockers
- Success criteria
- Weather information (if applicable)
- Raw tool results from web searches

### Example Structure
```json
{
  "id": "006f7e5a-2e62-483e-86ca-b4b9b4fe0a87",
  "text": "Help Advay with math worksheet",
  "date": "2026-01-17",
  "status": "pending",
  "enrichment": {
    "task_id": "...",
    "enriched_at": "...",
    "enriched_by": "TaskEnricher",
    "steps": [ ... ],
    "probable_questions": [ ... ],
    "suggested_resources": [ ... ],
    "raw_tool_results": [ ... ]
  },
  "subtasks": [ ... ],
  ...
}
```

### Storage Size
- **Per file**: ~5-50 KB (enrichment files can be larger)
- **Growth rate**: 1-2 files per task created
- **Estimated monthly**: ~2-10 MB (depends on task creation rate)

### Access Pattern
- **Read**: When viewing task details
- **Write**: When task is created or enriched
- **Update frequency**: Moderate (when tasks are created/enriched)

---

## Summary Statistics

### Total Storage Estimates

| Directory | Files/Day | Size/File | Monthly Growth | Annual Estimate |
|-----------|-----------|-----------|----------------|-----------------|
| `tasks/` | 1 | 5-50 KB | ~1-2 MB | ~12-24 MB |
| `reasoning/` | 10-50 | 1-5 KB | ~5-15 MB | ~60-180 MB |
| `memory/` | 0.1-1 | 10-100 KB | ~100-500 KB | ~1-6 MB |
| `task_details/` | 1-10 | 5-50 KB | ~2-10 MB | ~24-120 MB |
| **TOTAL** | **12-61** | **-** | **~8-28 MB** | **~96-330 MB** |

### Notes
- These are estimates for moderate usage (1-5 active users)
- Reasoning files will be the largest contributor
- Consider implementing lifecycle policies to archive old reasoning files
- Task and task_details files are essential and should be retained
- Memory files are important for learning and should be retained

---

## Cloud Storage Configuration Recommendations

### 1. Bucket Structure
```
gs://karma-app-data/
├── tasks/
│   └── YYYY-MM-DD.json
├── reasoning/
│   ├── YYYY-MM-DD_HH-MM-SS_*.json
│   └── YYYY-MM-DD_log.txt
├── memory/
│   ├── feedback_history.json
│   └── rejected_tasks.json
└── task_details/
    ├── {task_id}.json
    └── {task_id}_enrichment.json
```

### 2. Lifecycle Policies

#### Archive Old Reasoning Files (Optional)
- Move reasoning files older than 90 days to **Nearline** storage class
- Move reasoning files older than 365 days to **Coldline** storage class
- Delete reasoning files older than 2 years (if not needed for compliance)

#### Keep Essential Data
- **Tasks**: Keep forever (Standard storage)
- **Task Details**: Keep forever (Standard storage)
- **Memory**: Keep forever (Standard storage)
- **Reasoning**: Archive after 90 days, delete after 2 years

### 3. Access Control
- **Service Account**: Backend service account with `storage.objectAdmin` role
- **Read/Write**: Only backend service can modify files
- **Public Access**: None (all files are private)

### 4. Backup Strategy
- **Automatic Backups**: Cloud Storage provides automatic redundancy
- **Versioning**: Enable object versioning for critical files (optional)
- **Cross-Region Replication**: Consider for high availability (optional)

### 5. Cost Optimization
- Use **Standard** storage for frequently accessed files (tasks, memory)
- Use **Nearline** for reasoning files older than 90 days
- Use **Coldline** for reasoning files older than 365 days
- Enable **Object Lifecycle Management** to automatically transition storage classes

---

## Migration Considerations

### What Stays in Database (Cloud SQL)
- **Task records**: Core task data (id, text, status, dates)
- **Subtask records**: Subtask data linked to tasks
- **Feedback records**: User feedback for learning
- **QuickWin history**: History of quick wins shown
- **Session data**: User context and preferences

### What Moves to Cloud Storage
- **Date-based task files**: JSON snapshots (for backup/recovery)
- **Reasoning traces**: Detailed AI decision logs
- **Task enrichment data**: Detailed enrichment information
- **Memory/feedback files**: JSON backups of learning data

### Why This Split?
- **Database**: Fast queries, relationships, transactions
- **Cloud Storage**: Large JSON files, audit trails, backups
- **Best of both**: Database for operations, storage for history/analysis

---

## Implementation Notes

### File Operations
All file operations will be abstracted through a storage service that:
- Supports both local filesystem (development) and Cloud Storage (production)
- Handles authentication automatically
- Provides consistent API regardless of storage backend
- Handles errors gracefully (retries, fallbacks)

### Performance Considerations
- **Caching**: Consider caching frequently accessed files in memory
- **Batch Operations**: Batch file reads/writes when possible
- **Async Operations**: Use async I/O for file operations
- **Connection Pooling**: Reuse Cloud Storage client connections

---

**Last Updated**: 2026-01-17  
**Document Version**: 1.0
