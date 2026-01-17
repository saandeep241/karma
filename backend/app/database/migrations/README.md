# Database Migrations

This directory contains database migration scripts for the Karma application.

## Migration 001: Add user_id Columns

**File:** `001_add_user_id_columns.py`

**Purpose:** Adds `user_id` columns to all tables to enable user-specific data isolation.

### What This Migration Does

1. **Adds `user_id` columns** to:
   - `tasks` table
   - `subtasks` table
   - `feedback` table
   - `quickwin_history` table

2. **Assigns existing data** to a legacy user (`legacy-user`) so no data is lost

3. **Creates indexes** on `user_id` columns for performance:
   - Single column indexes on all `user_id` columns
   - Composite indexes on `tasks(user_id, date)` and `tasks(user_id, status)`

### Running the Migration

**Before running:**
- Make sure you have a backup of your database
- Ensure the application is not running (to avoid conflicts)

**Run the migration:**
```bash
cd /Users/gayatrimajumdar/dev/karma/backend
source venv/bin/activate
python app/database/migrations/001_add_user_id_columns.py
```

**The migration is idempotent** - it's safe to run multiple times. It will skip steps that have already been completed.

### What Happens to Existing Data

All existing tasks, subtasks, feedback, and quick win history records will be assigned to the user ID `legacy-user`. This ensures:
- No data is lost during migration
- Existing data remains accessible
- New data will require a valid authenticated user ID

### After Migration

After running this migration:
- All new records **must** include a `user_id` when created
- Application code will filter queries by `user_id` to ensure user isolation
- Routes will require authentication to access data

### Rollback

⚠️ **Warning:** Rolling back this migration is complex and not recommended. SQLite doesn't support dropping columns directly, so rollback would require:
1. Creating new tables without `user_id` columns
2. Copying data from old tables
3. Dropping old tables
4. Renaming new tables

If you need to rollback, consider restoring from a backup instead.

To attempt rollback (not recommended):
```bash
python app/database/migrations/001_add_user_id_columns.py --rollback
```

### Verification

After running the migration, you can verify it worked by checking:

```python
# In Python shell
from app.database.connection import async_session
from app.database.models import TaskModel
from sqlalchemy import select

async with async_session() as session:
    result = await session.execute(select(TaskModel).limit(1))
    task = result.scalar_one_or_none()
    if task:
        print(f"Task user_id: {task.user_id}")
```

All tasks should have a `user_id` value (either `legacy-user` for existing data, or a real user ID for new data).
