# Local Testing Guide

## Quick Test Checklist

### 1. Test Database Connection

```bash
cd backend
source venv/bin/activate

# Test database initialization
python -c "from app.database.connection import init_db; import asyncio; asyncio.run(init_db())"
```

**Expected**: Should see "📦 Using SQLite database: ..." and "Database initialized"

### 2. Test Configuration

```bash
python -c "from app.config import get_settings; s = get_settings(); print(f'Database: {\"PostgreSQL\" if s.use_postgresql else \"SQLite\"}'); print(f'Cloud Storage: {\"Enabled\" if s.use_cloud_storage else \"Disabled\"}')"
```

**Expected**: 
- Database: SQLite
- Cloud Storage: Disabled

### 3. Start Backend Server

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Expected**: Server starts on http://localhost:8000

### 4. Test Health Endpoint

```bash
curl http://localhost:8000/api/health
```

**Expected**: JSON response with status "healthy"

### 5. Verify No Files Written

Since Cloud Storage is disabled by default, check that no files are being written:

```bash
# Check data directory (should only have database file)
ls -la backend/data/
```

**Expected**: Only `karma.db` should exist (or be created). No `tasks/`, `reasoning/`, `memory/`, or `task_details/` directories should be created.

### 6. Test API Endpoints

```bash
# Get all tasks (should return empty or existing tasks)
curl http://localhost:8000/api/tasks/all

# Add a task
curl -X POST http://localhost:8000/api/tasks/add \
  -H "Content-Type: application/json" \
  -d '{"text": "Test task from local testing"}'
```

**Expected**: Task should be saved to database, NOT to files

### 7. Verify Database Storage

```bash
# Check SQLite database
sqlite3 backend/data/karma.db "SELECT COUNT(*) FROM tasks;"
```

**Expected**: Should show task count (tasks are in database, not files)

## Testing Cloud Storage (Optional)

To test Cloud Storage locally, you need:

1. GCP credentials set up
2. Cloud Storage bucket created
3. Set environment variable:

```bash
export USE_CLOUD_STORAGE=true
export GCS_BUCKET_NAME=karma-app-data
```

Then restart the server and verify files are written to Cloud Storage.

## Testing PostgreSQL (Optional)

To test PostgreSQL locally, you need:

1. PostgreSQL running locally or Cloud SQL instance
2. Set environment variables:

```bash
export DATABASE_HOST=localhost
export DATABASE_USER=karma_user
export DATABASE_PASSWORD=your_password
export DATABASE_NAME=karma
```

Or for Cloud SQL:

```bash
export CLOUD_SQL_CONNECTION_NAME=PROJECT:REGION:INSTANCE
export DATABASE_USER=karma_user
export DATABASE_PASSWORD=your_password
export DATABASE_NAME=karma
```

## Common Issues

### Issue: "Module not found: asyncpg"

**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: Database connection fails

**Solution**: Check that SQLite file is writable, or PostgreSQL credentials are correct

### Issue: Files are still being written

**Solution**: Verify `USE_CLOUD_STORAGE` is not set to "true" in environment

### Issue: Import errors

**Solution**: Make sure you're in the backend directory and virtual environment is activated
