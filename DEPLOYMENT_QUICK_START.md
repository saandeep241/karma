# GCP Deployment Quick Start Guide

This guide will help you deploy the Karma application to Google Cloud Platform.

## Prerequisites

1. **GCP Account** with billing enabled
2. **gcloud CLI** installed and authenticated
3. **Docker** installed
4. **Project ID** - Your GCP project ID

## Quick Start

### 1. Set Environment Variables

```bash
export GCP_PROJECT_ID=your-project-id
export GCP_REGION=us-central1  # Optional, defaults to us-central1
```

### 2. Run Deployment Script

```bash
./scripts/deploy/deploy.sh
```

Choose option `1` for full deployment, or select individual steps as needed.

## Manual Steps

### Step 1: Enable APIs

```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  storage-component.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com
```

### Step 1.5: Set Up Cloud Build Permissions (Important!)

Cloud Build needs permissions to upload source code and deploy:

```bash
# Get project number
PROJECT_NUMBER=$(gcloud projects describe $GCP_PROJECT_ID --format='value(projectNumber)')

# Grant Cloud Build service account permissions
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Also grant Compute Engine default service account (for local builds)
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/storage.admin"

# Grant Container Registry/Artifact Registry permissions (for pushing images)
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

**Note**: The `deploy.sh` script now does this automatically!

**Alternative**: If you still get errors, use your user account for builds:
```bash
gcloud auth application-default login
```

### Step 2: Create Cloud SQL Instance

```bash
# Create PostgreSQL instance
gcloud sql instances create karma-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=YOUR_PASSWORD \
  --storage-type=SSD \
  --storage-size=20GB

# Create database
gcloud sql databases create karma --instance=karma-db

# Create user
gcloud sql users create karma_user \
  --instance=karma-db \
  --password=YOUR_PASSWORD
```

**Save the connection name:**
```bash
gcloud sql instances describe karma-db --format='value(connectionName)'
```

**Note**: Database tables are created automatically when the backend starts. The app uses SQLAlchemy to create all tables from the models. No manual SQL scripts needed!

### Step 3: Create Cloud Storage Bucket

```bash
gsutil mb -p $GCP_PROJECT_ID -l us-central1 gs://karma-app-data
```

### Step 4: Create Service Account

```bash
# Create service account
gcloud iam service-accounts create karma-backend \
  --display-name="Karma Backend Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:karma-backend@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:karma-backend@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

### Step 5: Store Secrets

```bash
# Store OpenAI API key
echo -n "your-openai-api-key" | gcloud secrets create openai-api-key --data-file=-

# Store database password
echo -n "your-database-password" | gcloud secrets create database-password --data-file=-

# Grant access
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:karma-backend@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding database-password \
  --member="serviceAccount:karma-backend@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Step 6: Build and Deploy Backend

**Choose AI Mode:**
- **Dummy Mode (Recommended for testing)**: Set `OPENAI_KARMA=false` - No AI, no OpenAI key needed
- **AI Mode**: Set `OPENAI_KARMA=true` - Requires OpenAI API key

```bash
# Build image
gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/karma-backend ./backend

# Get connection name
CONNECTION_NAME=$(gcloud sql instances describe karma-db --format='value(connectionName)')

# Deploy (DUMMY MODE - no AI)
gcloud run deploy karma-backend \
  --image gcr.io/$GCP_PROJECT_ID/karma-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --service-account karma-backend@$GCP_PROJECT_ID.iam.gserviceaccount.com \
  --add-cloudsql-instances $CONNECTION_NAME \
  --update-secrets DATABASE_PASSWORD=database-password:latest \
  --set-env-vars "USE_CLOUD_STORAGE=true" \
  --set-env-vars "GCS_BUCKET_NAME=karma-app-data" \
  --set-env-vars "CLOUD_SQL_CONNECTION_NAME=$CONNECTION_NAME" \
  --set-env-vars "DATABASE_USER=karma_user" \
  --set-env-vars "DATABASE_NAME=karma" \
  --set-env-vars "OPENAI_KARMA=false" \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300

# For AI MODE, also add:
# --update-secrets OPENAI_API_KEY=openai-api-key:latest \
# --set-env-vars "OPENAI_KARMA=true" \

# Get backend URL
BACKEND_URL=$(gcloud run services describe karma-backend --region us-central1 --format 'value(status.url)')
echo "Backend URL: $BACKEND_URL"
```

### Step 7: Build and Deploy Frontend

```bash
# Build image
gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/karma-frontend ./frontend

# Deploy
gcloud run deploy karma-frontend \
  --image gcr.io/$GCP_PROJECT_ID/karma-frontend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "VITE_API_URL=$BACKEND_URL/api" \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60

# Get frontend URL
FRONTEND_URL=$(gcloud run services describe karma-frontend --region us-central1 --format 'value(status.url)')
echo "Frontend URL: $FRONTEND_URL"
```

### Step 8: Update Backend CORS

Update the backend to allow the frontend URL:

```bash
gcloud run services update karma-backend \
  --set-env-vars "FRONTEND_URL=$FRONTEND_URL" \
  --region us-central1
```

## Environment Variables Reference

### Backend (Cloud Run)

| Variable | Source | Description |
|----------|--------|-------------|
| `OPENAI_API_KEY` | Secret Manager | OpenAI API key |
| `OPENAI_KARMA` | Env Var | Set to "true" to enable AI |
| `DATABASE_PASSWORD` | Secret Manager | Cloud SQL password |
| `CLOUD_SQL_CONNECTION_NAME` | Env Var | PROJECT:REGION:INSTANCE |
| `DATABASE_USER` | Env Var | Database user (karma_user) |
| `DATABASE_NAME` | Env Var | Database name (karma) |
| `USE_CLOUD_STORAGE` | Env Var | Set to "true" |
| `GCS_BUCKET_NAME` | Env Var | Cloud Storage bucket |
| `FRONTEND_URL` | Env Var | Frontend Cloud Run URL |

### Frontend (Cloud Run)

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend API URL (e.g., https://karma-backend-xxx.run.app/api) |

## Database Tables

**Important**: Database tables are created **automatically** when the backend starts for the first time. No manual SQL scripts needed!

### How It Works

The application uses SQLAlchemy ORM which:
- Creates all tables from models defined in `app/database/models.py`
- Handles both SQLite (local) and PostgreSQL (Cloud SQL)
- **Is idempotent** - won't recreate existing tables on restart

### On App Restart

✅ **Safe behavior**: 
- Tables are **not recreated** if they already exist
- All **data is preserved**
- Only **new tables** are created (if models were added)
- **Existing tables are untouched**

This means:
- **First start**: Creates all tables
- **Subsequent restarts**: Does nothing (tables exist, data preserved)
- **Cloud Run restarts**: Database persists (it's a separate service)

### Tables Created

- `tasks` - User tasks
- `subtasks` - Task subtasks
- `feedback` - User feedback for learning
- `quickwin_history` - Quick win tracking

### Verifying Tables

After deployment, verify tables were created:

```bash
# Connect to Cloud SQL
gcloud sql connect karma-db --user=karma_user --database=karma

# List tables
\dt

# Should show: tasks, subtasks, feedback, quickwin_history

# Exit
\q
```

Or check the backend logs - you should see:
```
📦 PostgreSQL database initialized: karma
```

### Important Notes

- ⚠️ **Schema changes**: `create_all()` won't add new columns to existing tables. Use Alembic migrations for schema changes.
- ✅ **Data persistence**: Data survives all restarts (database is persistent)
- ✅ **Cloud Run**: Containers are stateless, but database is separate and persistent

See `backend/database_schema.md` for detailed schema documentation and SQL scripts (for reference).  
See `backend/APP_RESTART_BEHAVIOR.md` for detailed explanation of restart behavior.

## Troubleshooting

### Backend won't connect to database

1. Check Cloud SQL connection name is correct
2. Verify service account has `cloudsql.client` role
3. Check database password in Secret Manager
4. Verify Cloud SQL instance is running

### Frontend can't reach backend

1. Check CORS settings in backend
2. Verify `FRONTEND_URL` is set correctly
3. Check backend is accessible (test with curl)

### Files not saving to Cloud Storage

1. Verify `USE_CLOUD_STORAGE=true`
2. Check service account has `storage.objectAdmin` role
3. Verify bucket exists and is accessible

## Next Steps

- Set up custom domain (optional)
- Configure monitoring and alerts
- Set up CI/CD pipeline
- Review security settings

## Cost Estimation

- **Cloud Run**: ~$10-30/month (pay-per-use)
- **Cloud SQL**: ~$8/month (db-f1-micro)
- **Cloud Storage**: ~$0.01/month (minimal usage)
- **Total**: ~$18-38/month for small-medium traffic
