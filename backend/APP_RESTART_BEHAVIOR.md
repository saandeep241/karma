# App Restart Behavior

## How Database Tables Work on Restart

### SQLAlchemy's `create_all()` is Idempotent

**Key Point**: `Base.metadata.create_all()` is **idempotent** - it only creates tables that don't exist. If tables already exist, it does **nothing** (no errors, no data loss).

### What Happens on Each Restart

1. **App starts** → `lifespan()` function runs
2. **Calls `init_db()`** → Checks database connection
3. **Calls `create_all()`** → Creates only missing tables
4. **Existing tables** → Left completely untouched
5. **Existing data** → Preserved 100%

### Example Flow

#### First Start (Empty Database)
```
App starts → init_db() → create_all() → Creates: tasks, subtasks, feedback, quickwin_history
Result: ✅ 4 tables created, database ready
```

#### Subsequent Restarts (Tables Exist)
```
App starts → init_db() → create_all() → Checks tables → All exist → Does nothing
Result: ✅ No changes, all data preserved
```

#### After Adding New Model (New Table Needed)
```
App starts → init_db() → create_all() → Creates only the new table
Result: ✅ New table created, existing tables/data untouched
```

## Data Persistence

### Local Development (SQLite)

- **Database file**: `backend/data/karma.db`
- **Persists**: Yes, file remains on disk
- **On restart**: Same database file is used, all data intact
- **Data loss**: Only if you delete the `.db` file

### Cloud Run (PostgreSQL)

- **Database**: Cloud SQL PostgreSQL (separate service)
- **Persists**: Yes, Cloud SQL is persistent storage
- **On restart**: 
  - Cloud Run container is **stateless** (ephemeral)
  - Database is **separate** (persistent)
  - Container restarts don't affect database
- **Data loss**: Only if you delete the Cloud SQL instance

## Cloud Run Specifics

### Container Lifecycle

1. **Container starts** → Fresh container, no local state
2. **Connects to Cloud SQL** → Database is external, persistent
3. **Calls `init_db()` → Creates tables if needed
4. **Serves requests** → Uses existing data from Cloud SQL
5. **Container stops** → Local container state lost (but database persists)
6. **Next request** → New container starts, connects to same database

### Important Points

- ✅ **Database is persistent** - Data survives container restarts
- ✅ **Tables are idempotent** - Won't recreate existing tables
- ✅ **No data loss** - Existing data is never touched
- ⚠️ **New columns** - `create_all()` won't add new columns to existing tables (need migrations)

## What `create_all()` Does NOT Do

### ❌ Does NOT:
- Drop existing tables
- Modify existing tables
- Add new columns to existing tables
- Delete data
- Recreate tables

### ✅ Does:
- Create tables that don't exist
- Create indexes defined in models
- Set up foreign key constraints
- Handle both SQLite and PostgreSQL

## Schema Changes (Migrations)

### Current Approach: Auto-Creation

**Limitation**: `create_all()` only creates **new tables**. It won't:
- Add columns to existing tables
- Modify column types
- Drop columns
- Rename columns

### Example Problem

If you add a new column to `TaskModel`:
```python
# New field added
new_field: Mapped[str] = mapped_column(String(50), nullable=True)
```

**What happens:**
- ✅ New deployments: New column exists
- ❌ Existing databases: Column missing (no error, but field won't be used)

### Solution: Use Alembic Migrations

For production schema changes, use Alembic:

```bash
# Install Alembic
pip install alembic

# Create migration
alembic revision --autogenerate -m "Add new_field to tasks"

# Apply migration
alembic upgrade head
```

## Testing Restart Behavior

### Test Locally

```bash
# Start app (creates tables)
cd backend
uvicorn app.main:app --reload

# Add some data via API
curl -X POST http://localhost:8000/api/tasks/add \
  -H "Content-Type: application/json" \
  -d '{"text": "Test task"}'

# Stop app (Ctrl+C)

# Restart app
uvicorn app.main:app --reload

# Verify data still exists
curl http://localhost:8000/api/tasks/all
# ✅ Task should still be there
```

### Test in Cloud Run

```bash
# Deploy app
./scripts/deploy/deploy.sh

# Add data via API
curl -X POST https://your-backend.run.app/api/tasks/add \
  -H "Content-Type: application/json" \
  -d '{"text": "Test task"}'

# Force restart (update env var)
gcloud run services update karma-backend \
  --set-env-vars "TEST_RESTART=1" \
  --region us-central1

# Verify data still exists
curl https://your-backend.run.app/api/tasks/all
# ✅ Task should still be there
```

## Summary

| Scenario | Tables | Data | Notes |
|----------|--------|------|-------|
| **First start** | Created | Empty | Normal initialization |
| **Regular restart** | Unchanged | Preserved | Idempotent behavior |
| **New table added** | New table created | Preserved | Existing tables untouched |
| **New column added** | Unchanged | Preserved | ⚠️ Need migration for new column |
| **Container restart** | Unchanged | Preserved | Database is separate service |

## Best Practices

1. ✅ **Use `create_all()` for initial setup** - Perfect for new deployments
2. ✅ **Use Alembic for schema changes** - For production migrations
3. ✅ **Backup before migrations** - Always backup production data
4. ✅ **Test migrations locally** - Test on SQLite before PostgreSQL
5. ⚠️ **Don't rely on `create_all()` for schema changes** - Use proper migrations

## Troubleshooting

### Tables Not Created

**Symptom**: App starts but tables don't exist

**Check**:
1. Database connection working?
2. User has CREATE TABLE permission?
3. Check logs for errors

**Solution**: 
```bash
# Manually verify connection
gcloud sql connect karma-db --user=karma_user --database=karma
\dt  # Should show tables
```

### Data Missing After Restart

**Symptom**: Data was there, now gone

**Possible causes**:
1. ❌ Wrong database (check connection string)
2. ❌ Database was deleted/recreated
3. ❌ Using different user/database

**Solution**: Check Cloud SQL instance hasn't been recreated

### Schema Mismatch

**Symptom**: Errors about missing columns

**Cause**: Model changed but table wasn't migrated

**Solution**: Use Alembic to add the column:
```bash
alembic revision --autogenerate -m "Add missing column"
alembic upgrade head
```
