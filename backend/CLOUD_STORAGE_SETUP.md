# Cloud Storage Setup Guide

## Overview

The Karma backend now supports configurable storage for backup/audit files:
- **Cloud Storage disabled** (default): Files are **NOT written** - the database is the primary source of truth
- **Cloud Storage enabled**: Files are written to Google Cloud Storage for backup/audit purposes

**Important**: These files are **not functionally required**. They're just backups/audit logs:
- Tasks are stored in the database (primary source)
- Feedback is stored in the database
- Reasoning files are just for debugging/audit
- Task details are in the database

The storage service automatically handles the abstraction, so your code doesn't need to change.

## Configuration

### Environment Variables

Add these to your `.env` file or set them as environment variables:

```bash
# Enable Cloud Storage (set to "true" to enable)
USE_CLOUD_STORAGE=false

# Cloud Storage bucket name (only needed if USE_CLOUD_STORAGE=true)
GCS_BUCKET_NAME=karma-app-data
```

### Local Development (Default)

By default, Cloud Storage is **disabled** and files are **NOT written** at all.

**The database is the primary source of truth** - all tasks, feedback, and data are stored in the database (SQLite locally, PostgreSQL in production).

No additional setup needed! The application works perfectly without writing any files.

### Cloud Storage Setup

#### 1. Create Cloud Storage Bucket

```bash
# Create bucket
gsutil mb -p YOUR_PROJECT_ID -l us-central1 gs://karma-app-data

# Or using gcloud
gcloud storage buckets create gs://karma-app-data \
  --project=YOUR_PROJECT_ID \
  --location=us-central1
```

#### 2. Set Up Authentication

For local development:
```bash
# Authenticate with GCP
gcloud auth application-default login
```

For Cloud Run (automatic):
- Cloud Run automatically uses the service account
- Grant the service account `Storage Object Admin` role:
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

The `google-cloud-storage` package is already in `requirements.txt`.

#### 4. Enable Cloud Storage

Set environment variable:
```bash
export USE_CLOUD_STORAGE=true
export GCS_BUCKET_NAME=karma-app-data
```

Or in `.env`:
```bash
USE_CLOUD_STORAGE=true
GCS_BUCKET_NAME=karma-app-data
```

## How It Works

### Storage Service

The `StorageService` class automatically:
- Detects if Cloud Storage is enabled
- Falls back to local storage if Cloud Storage is unavailable
- Provides the same API regardless of storage backend

### File Operations

All file operations go through the storage service:

```python
from app.services.storage_service import get_storage_service

storage = get_storage_service()

# Write JSON file (no-op if Cloud Storage is disabled)
storage.write_json("tasks", "2026-01-17.json", data)

# Read JSON file (returns None if Cloud Storage is disabled)
data = storage.read_json("tasks", "2026-01-17.json")

# Check if file exists (returns False if Cloud Storage is disabled)
exists = storage.file_exists("tasks", "2026-01-17.json")

# Append to file (no-op if Cloud Storage is disabled)
storage.append_to_file("reasoning", "2026-01-17_log.txt", content)
```

**Note**: When Cloud Storage is disabled, all file operations are no-ops (they return success but don't write anything). The database is used instead.

### Directory Structure

Files are organized in Cloud Storage the same way as local:

```
gs://karma-app-data/
├── tasks/
│   └── 2026-01-17.json
├── reasoning/
│   ├── 2026-01-17_21-10-03_Breakdown_breakdown.json
│   └── 2026-01-17_log.txt
├── memory/
│   ├── feedback_history.json
│   └── rejected_tasks.json
└── task_details/
    └── {task_id}.json
```

## Migration

### Migrating Existing Data to Cloud Storage

```bash
# Upload existing data
gsutil -m cp -r backend/data/tasks gs://karma-app-data/
gsutil -m cp -r backend/data/reasoning gs://karma-app-data/
gsutil -m cp -r backend/data/memory gs://karma-app-data/
gsutil -m cp -r backend/data/task_details gs://karma-app-data/
```

### Verifying Migration

```bash
# List files in bucket
gsutil ls -r gs://karma-app-data/

# Check specific directory
gsutil ls gs://karma-app-data/tasks/
```

## Troubleshooting

### Cloud Storage Not Working

1. **Check authentication:**
   ```bash
   gcloud auth application-default login
   ```

2. **Verify bucket exists:**
   ```bash
   gsutil ls gs://karma-app-data/
   ```

3. **Check permissions:**
   - Service account needs `Storage Object Admin` role
   - Or `roles/storage.objectAdmin` for the bucket

4. **Check logs:**
   - The storage service logs warnings if Cloud Storage fails
   - It automatically falls back to local storage

### Fallback Behavior

If Cloud Storage is enabled but fails to initialize:
- The service automatically falls back to local storage
- A warning is logged
- The application continues to work normally

## Testing

### Test Without Cloud Storage (Default)

```bash
# Default (no files written - database only)
python -m app.main
```

Files are not written, and the application works normally using only the database.

### Test Cloud Storage

```bash
# Enable Cloud Storage
export USE_CLOUD_STORAGE=true
export GCS_BUCKET_NAME=karma-app-data

# Run application
python -m app.main
```

Check logs for:
- `✅ Cloud Storage enabled: gs://karma-app-data` (success)
- `⚠️ Cloud Storage bucket '...' does not exist` (bucket missing)
- `❌ Failed to initialize Cloud Storage: ...` (error)

## Production Deployment

### Cloud Run Environment Variables

Set in Cloud Run service:

```bash
USE_CLOUD_STORAGE=true
GCS_BUCKET_NAME=karma-app-data
```

### Service Account Permissions

Ensure the Cloud Run service account has:
- `roles/storage.objectAdmin` (or `roles/storage.objectCreator` + `roles/storage.objectViewer`)

## Cost Considerations

- **Local Storage**: Free (uses container filesystem, ephemeral)
- **Cloud Storage**: 
  - Storage: ~$0.020/GB/month
  - Operations: $0.05 per 10,000 operations
  - Estimated: ~$0.01-0.10/month for small-medium usage

## Next Steps

- See `GCP_DEPLOYMENT_PLAN.md` for full deployment guide
- See `CLOUD_STORAGE_CONTENTS.md` for what gets stored
- See `GOOGLE_CLOUD_LOGGING_STRATEGY.md` for logging options
