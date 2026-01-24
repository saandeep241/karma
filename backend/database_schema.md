# Database Schema Documentation

## Overview

The Karma application uses **SQLAlchemy ORM** to manage the database schema. Tables are created **automatically** when the application starts - no manual SQL scripts are required.

## How Tables Are Created

### Automatic Creation

When the backend application starts, it calls `init_db()` which:

1. Connects to the database (SQLite locally, PostgreSQL in production)
2. Uses SQLAlchemy's `Base.metadata.create_all` to create all tables
3. Tables are created based on the models defined in `app/database/models.py`

### When Tables Are Created

- **Local Development**: Tables created automatically on first run
- **Cloud Run**: Tables created automatically when the service starts for the first time
- **Manual Creation**: Not needed, but SQL scripts are provided below for reference

## Database Models

The application uses the following tables:

### 1. `tasks`
Stores user tasks with all metadata.

**Key Fields:**
- `id` (UUID, primary key)
- `user_id` (string, indexed)
- `text` (task description)
- `date` (YYYY-MM-DD, indexed)
- `status` (pending/in_progress/completed/skipped, indexed)
- `priority`, `category`, `tags`
- `estimated_minutes`, `energy_required`
- `ai_reasoning`, `enrichment` (JSON)
- `subtasks_generated`, `is_dummy`
- Timestamps: `created_at`, `started_at`, `completed_at`

### 2. `subtasks`
Stores subtasks for tasks.

**Key Fields:**
- `id` (UUID, primary key)
- `user_id` (string, indexed)
- `task_id` (foreign key to tasks.id, indexed)
- `text`, `instruction`
- `status`, `order`, `progress` (0-100)
- `estimated_minutes`
- `ai_reasoning`
- Timestamps: `created_at`, `completed_at`

### 3. `feedback`
Stores user feedback for learning.

**Key Fields:**
- `id` (auto-increment, primary key)
- `user_id` (string, indexed)
- `task_id` (optional, string)
- `task_text` (text)
- `accepted` (boolean)
- `context_time_available`, `context_energy_level`, `context_mood`
- `reasoning_used`
- `created_at` (timestamp)

### 4. `quickwin_history`
Tracks quick wins shown to users.

**Key Fields:**
- `id` (auto-increment, primary key)
- `user_id` (string, indexed)
- `quickwin_text` (text)
- `category` (string)
- `shown_at` (timestamp)
- `was_added` (boolean)

## SQL Scripts (For Reference)

While tables are created automatically, here are the SQL scripts for reference:

### PostgreSQL Schema

```sql
-- Tasks table
CREATE TABLE tasks (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    text TEXT NOT NULL,
    date VARCHAR(10) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    priority VARCHAR(20) DEFAULT 'medium',
    category VARCHAR(50) DEFAULT 'other',
    estimated_minutes INTEGER DEFAULT 15,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    energy_required VARCHAR(20) DEFAULT 'medium',
    task_type VARCHAR(50),
    tags JSONB DEFAULT '[]',
    ai_reasoning TEXT,
    enrichment JSONB,
    times_suggested INTEGER DEFAULT 0,
    times_accepted INTEGER DEFAULT 0,
    times_rejected INTEGER DEFAULT 0,
    subtasks_generated BOOLEAN DEFAULT FALSE,
    is_dummy BOOLEAN DEFAULT FALSE,
    notes TEXT
);

CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_date ON tasks(date);
CREATE INDEX idx_tasks_status ON tasks(status);

-- Subtasks table
CREATE TABLE subtasks (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(36) NOT NULL,
    text TEXT NOT NULL,
    instruction TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    "order" INTEGER DEFAULT 0,
    progress INTEGER DEFAULT 0,
    estimated_minutes INTEGER DEFAULT 5,
    ai_reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX idx_subtasks_user_id ON subtasks(user_id);
CREATE INDEX idx_subtasks_task_id ON subtasks(task_id);

-- Feedback table
CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(36),
    task_text TEXT NOT NULL,
    accepted BOOLEAN NOT NULL,
    context_time_available INTEGER,
    context_energy_level VARCHAR(20),
    context_mood VARCHAR(20),
    reasoning_used TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_feedback_user_id ON feedback(user_id);

-- QuickWin history table
CREATE TABLE quickwin_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    quickwin_text TEXT NOT NULL,
    category VARCHAR(50) DEFAULT 'other',
    shown_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    was_added BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_quickwin_history_user_id ON quickwin_history(user_id);
```

## Verifying Tables Were Created

### Using Cloud SQL Console

1. Go to Cloud SQL in GCP Console
2. Select your instance
3. Click "Databases" → Select "karma" database
4. Click "Tables" to see all created tables

### Using gcloud CLI

```bash
# Connect to Cloud SQL
gcloud sql connect karma-db --user=karma_user --database=karma

# List tables
\dt

# Describe a table
\d tasks
```

### Using psql (if you have direct access)

```bash
psql -h <cloud-sql-ip> -U karma_user -d karma

# List tables
\dt

# Check table structure
\d tasks
```

### From Application Logs

When the backend starts, you should see:
```
📦 PostgreSQL database initialized: karma
```

If tables already exist, SQLAlchemy won't recreate them (it's idempotent).

## Migration Strategy

### Current Approach: Auto-Creation

- **Pros**: Simple, no migration scripts needed
- **Cons**: Not ideal for production schema changes

### Future: Alembic Migrations (Recommended)

For production, consider using Alembic for migrations:

```bash
# Install Alembic
pip install alembic

# Initialize
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

## Troubleshooting

### Tables Not Created

1. **Check logs**: Look for database initialization errors
2. **Verify connection**: Ensure Cloud SQL connection is working
3. **Check permissions**: Database user needs CREATE TABLE permission
4. **Manual creation**: Use SQL scripts above if needed

### Schema Mismatch Errors

If you see errors about missing columns:
1. Tables were created with old schema
2. Solution: Drop and recreate tables (data will be lost) OR use Alembic migrations

### Foreign Key Errors

PostgreSQL requires explicit foreign key constraints (unlike SQLite):
- Already handled in the models
- Foreign keys are created automatically

## Notes

- **SQLite vs PostgreSQL**: The same models work for both, but some differences:
  - SQLite: JSON stored as TEXT
  - PostgreSQL: JSON stored as JSONB (more efficient)
  - SQLAlchemy handles these differences automatically

- **Indexes**: Created automatically based on model definitions (`index=True`)

- **Foreign Keys**: 
  - SQLite: Requires `PRAGMA foreign_keys=ON` (handled automatically)
  - PostgreSQL: Enforced by default
