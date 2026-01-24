# GCP Deployment Plan for Karma Application

## Overview
This document outlines the step-by-step plan to deploy the Karma application to Google Cloud Platform using:
- **Cloud Run** for both frontend and backend services
- **Cloud SQL (PostgreSQL)** for the database
- **Cloud Storage** for file-based data (tasks, reasoning, memory)

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Database Migration](#database-migration)
4. [File Storage Migration](#file-storage-migration)
5. [Backend Configuration](#backend-configuration)
6. [Frontend Configuration](#frontend-configuration)
7. [Cloud Run Deployment](#cloud-run-deployment)
8. [Environment Variables](#environment-variables)
9. [Security & Networking](#security--networking)
10. [Testing & Validation](#testing--validation)
11. [Cost Estimation](#cost-estimation)
12. [Rollback Plan](#rollback-plan)

---

## Prerequisites

### 1. GCP Account Setup
- [ ] Create/verify GCP project
- [ ] Enable billing
- [ ] Install and configure `gcloud` CLI
- [ ] Set default project: `gcloud config set project PROJECT_ID`

### 2. Required APIs
Enable the following APIs:
```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  storage-component.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com
```

### 3. Required Tools
- Docker (for building images)
- `gcloud` CLI
- `gsutil` (for Cloud Storage operations)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Cloud Load Balancer                      │
│                    (Optional - for custom domain)            │
└───────────────────────┬─────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                  │
┌───────▼────────┐              ┌──────────▼──────────┐
│  Frontend      │              │   Backend           │
│  (Cloud Run)   │              │   (Cloud Run)       │
│  Port: 80      │              │   Port: 8000        │
│  Nginx         │              │   FastAPI           │
└────────────────┘              └──────────┬──────────┘
                                           │
                          ┌────────────────┼────────────────┐
                          │                │                │
                  ┌───────▼──────┐  ┌─────▼─────┐  ┌──────▼──────┐
                  │  Cloud SQL   │  │  Cloud    │  │  Secret     │
                  │  PostgreSQL  │  │  Storage   │  │  Manager    │
                  │              │  │  (Files)   │  │  (Secrets)  │
                  └──────────────┘  └────────────┘  └─────────────┘
```

---

## Database Migration

### Step 1: Create Cloud SQL PostgreSQL Instance

```bash
# Create PostgreSQL instance
gcloud sql instances create karma-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=CHANGE_ME_STRONG_PASSWORD \
  --storage-type=SSD \
  --storage-size=20GB \
  --backup-start-time=03:00

# Create database
gcloud sql databases create karma --instance=karma-db

# Create database user
gcloud sql users create karma_user \
  --instance=karma-db \
  --password=CHANGE_ME_USER_PASSWORD
```

### Step 2: Update Backend Database Connection

**File: `backend/app/database/connection.py`**

Changes needed:
1. Replace SQLite with PostgreSQL
2. Use Cloud SQL connection (Unix socket or TCP)
3. Update SQLAlchemy engine configuration
4. Add connection pooling for Cloud Run

**New connection string format:**
```python
# For Cloud SQL via Unix socket (recommended for Cloud Run)
DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@/{database}?host=/cloudsql/{connection_name}"

# For Cloud SQL via TCP (alternative)
DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
```

### Step 3: Update Dependencies

**File: `backend/requirements.txt`**

Add:
```
asyncpg>=0.29.0  # PostgreSQL async driver
psycopg2-binary>=2.9.9  # PostgreSQL sync driver (for migrations)
```

Remove:
```
aiosqlite>=0.19.0  # No longer needed
```

### Step 4: Database Schema Migration

1. Export existing SQLite schema
2. Convert to PostgreSQL-compatible SQL
3. Run migrations on Cloud SQL instance
4. Migrate existing data (if any)

---

## File Storage Migration

### Step 1: Create Cloud Storage Bucket

```bash
# Create bucket for application files
gsutil mb -p PROJECT_ID -l us-central1 gs://karma-app-data

# Set bucket permissions
gsutil iam ch serviceAccount:SERVICE_ACCOUNT:objectAdmin gs://karma-app-data
```

### Step 2: Update File Storage Service

**Create new service: `backend/app/services/storage_service.py`**

This service will:
- Abstract file operations (local vs Cloud Storage)
- Handle upload/download from Cloud Storage
- Maintain backward compatibility during migration

**Update: `backend/app/services/tools.py`**

Replace direct file system operations with storage service calls:
- `save_tasks()` → use Cloud Storage
- `save_reasoning()` → use Cloud Storage
- `record_user_feedback()` → use Cloud Storage
- `save_task_with_details()` → use Cloud Storage

### Step 3: Migrate Existing Files

```bash
# Upload existing data to Cloud Storage
gsutil -m cp -r backend/data/tasks gs://karma-app-data/
gsutil -m cp -r backend/data/reasoning gs://karma-app-data/
gsutil -m cp -r backend/data/memory gs://karma-app-data/
gsutil -m cp -r backend/data/task_details gs://karma-app-data/
```

---

## Backend Configuration

### Step 1: Update Dockerfile

**File: `backend/Dockerfile`**

Ensure it:
- Uses Python 3.11
- Installs all dependencies
- Exposes port 8000
- Sets proper working directory
- Includes Cloud SQL proxy (if using TCP connection)

### Step 2: Update Configuration

**File: `backend/app/config.py`**

Add new environment variables:
```python
# Database settings
database_url: str = ""  # Cloud SQL connection string
cloud_sql_connection_name: str = ""  # PROJECT:REGION:INSTANCE
database_user: str = ""
database_password: str = ""
database_name: str = "karma"

# Cloud Storage settings
gcs_bucket_name: str = "karma-app-data"
use_cloud_storage: bool = True  # Toggle between local/cloud storage

# Cloud Run settings
cloud_run_service_url: str = ""  # Backend service URL
```

### Step 3: Update CORS Configuration

**File: `backend/app/main.py`**

Update `frontend_url` to use Cloud Run frontend URL:
```python
allow_origins=[
    settings.frontend_url,  # From environment variable
    "https://karma-frontend-XXXXX.run.app",  # Cloud Run URL
]
```

### Step 4: Create Cloud Run Service Account

```bash
# Create service account
gcloud iam service-accounts create karma-backend \
  --display-name="Karma Backend Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:karma-backend@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:karma-backend@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

---

## Frontend Configuration

### Step 1: Update API Client

**File: `frontend/src/api/client.ts`**

Update `API_BASE` to use environment variable:
```typescript
const API_BASE = import.meta.env.VITE_API_URL || '/api';
```

### Step 2: Update Build Configuration

**File: `frontend/vite.config.ts`**

Add environment variable handling:
```typescript
export default defineConfig({
  // ... existing config
  define: {
    'import.meta.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL || '/api'),
  },
})
```

### Step 3: Update Dockerfile

**File: `frontend/Dockerfile`**

Update nginx configuration to proxy to Cloud Run backend:
```nginx
location /api {
    proxy_pass https://karma-backend-XXXXX.run.app;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Step 4: Create Environment File

**File: `frontend/.env.production`**
```
VITE_API_URL=https://karma-backend-XXXXX.run.app/api
```

---

## Cloud Run Deployment

### Step 1: Build and Push Docker Images

```bash
# Set variables
export PROJECT_ID=your-project-id
export REGION=us-central1

# Build and push backend
cd backend
gcloud builds submit --tag gcr.io/$PROJECT_ID/karma-backend

# Build and push frontend
cd ../frontend
gcloud builds submit --tag gcr.io/$PROJECT_ID/karma-frontend
```

### Step 2: Deploy Backend Service

```bash
gcloud run deploy karma-backend \
  --image gcr.io/$PROJECT_ID/karma-backend \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --service-account karma-backend@$PROJECT_ID.iam.gserviceaccount.com \
  --add-cloudsql-instances $PROJECT_ID:$REGION:karma-db \
  --set-env-vars "OPENAI_API_KEY=..." \
  --set-env-vars "OPENAI_KARMA=true" \
  --set-env-vars "DATABASE_URL=..." \
  --set-env-vars "GCS_BUCKET_NAME=karma-app-data" \
  --set-env-vars "USE_CLOUD_STORAGE=true" \
  --set-env-vars "FRONTEND_URL=https://karma-frontend-XXXXX.run.app" \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0
```

### Step 3: Deploy Frontend Service

```bash
gcloud run deploy karma-frontend \
  --image gcr.io/$PROJECT_ID/karma-frontend \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars "VITE_API_URL=https://karma-backend-XXXXX.run.app/api" \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60 \
  --max-instances 5 \
  --min-instances 0
```

### Step 4: Get Service URLs

```bash
# Get backend URL
BACKEND_URL=$(gcloud run services describe karma-backend --region $REGION --format 'value(status.url)')

# Get frontend URL
FRONTEND_URL=$(gcloud run services describe karma-frontend --region $REGION --format 'value(status.url)')

echo "Backend: $BACKEND_URL"
echo "Frontend: $FRONTEND_URL"
```

---

## Environment Variables

### Backend Environment Variables

Store sensitive values in Secret Manager:

```bash
# Create secrets
echo -n "your-openai-api-key" | gcloud secrets create openai-api-key --data-file=-
echo -n "your-database-password" | gcloud secrets create database-password --data-file=-
echo -n "your-clerk-secret-key" | gcloud secrets create clerk-secret-key --data-file=-

# Grant access to service account
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:karma-backend@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

Update Cloud Run service to use secrets:
```bash
gcloud run services update karma-backend \
  --update-secrets OPENAI_API_KEY=openai-api-key:latest \
  --update-secrets DATABASE_PASSWORD=database-password:latest \
  --update-secrets CLERK_SECRET_KEY=clerk-secret-key:latest
```

### Required Environment Variables

**Backend:**
- `OPENAI_API_KEY` (Secret)
- `OPENAI_KARMA=true`
- `OPENAI_MODEL=gpt-4o-mini`
- `DATABASE_URL` (constructed from Cloud SQL connection)
- `CLOUD_SQL_CONNECTION_NAME` (PROJECT:REGION:INSTANCE)
- `DATABASE_USER=karma_user`
- `DATABASE_PASSWORD` (Secret)
- `DATABASE_NAME=karma`
- `GCS_BUCKET_NAME=karma-app-data`
- `USE_CLOUD_STORAGE=true`
- `FRONTEND_URL` (Cloud Run frontend URL)
- `CLERK_SECRET_KEY` (Secret, optional)
- `CLERK_PUBLISHABLE_KEY` (optional)

**Frontend:**
- `VITE_API_URL` (Backend Cloud Run URL)

---

## Security & Networking

### 1. IAM Roles

**Backend Service Account:**
- `roles/cloudsql.client` - Connect to Cloud SQL
- `roles/storage.objectAdmin` - Access Cloud Storage
- `roles/secretmanager.secretAccessor` - Access secrets

**Frontend Service Account:**
- Minimal permissions (read-only if needed)

### 2. Network Security

- Use Cloud SQL private IP (recommended) or public IP with authorized networks
- Enable VPC connector if needed for private connectivity
- Configure Cloud Run ingress to control access

### 3. CORS Configuration

Ensure backend CORS allows only frontend domain:
```python
allow_origins=[
    "https://karma-frontend-XXXXX.run.app",
    # Add custom domain if used
]
```

### 4. Authentication

- Clerk authentication should work as-is
- Ensure Clerk webhook URLs point to Cloud Run backend
- Configure Clerk allowed origins

---

## Testing & Validation

### 1. Health Check

```bash
# Test backend health
curl https://karma-backend-XXXXX.run.app/api/health

# Expected response:
{
  "status": "healthy",
  "app": "Karma - Smart Task Suggestions",
  "ai_enabled": true,
  "database": "PostgreSQL"
}
```

### 2. Database Connection

```bash
# Connect to Cloud SQL
gcloud sql connect karma-db --user=karma_user --database=karma

# Verify tables exist
\dt
```

### 3. Cloud Storage Access

```bash
# List files in bucket
gsutil ls gs://karma-app-data/

# Verify file structure
gsutil ls -r gs://karma-app-data/
```

### 4. End-to-End Testing

1. Access frontend URL
2. Test authentication (if enabled)
3. Create a task
4. Verify it's saved to database
5. Check reasoning files in Cloud Storage
6. Test AI suggestions
7. Verify subtasks creation

---

## Cost Estimation

### Monthly Cost Estimate (Low-Medium Traffic)

**Cloud Run:**
- Backend: ~$10-30/month (1GB RAM, 1 CPU, pay-per-use)
- Frontend: ~$5-15/month (512MB RAM, 1 CPU, pay-per-use)

**Cloud SQL:**
- db-f1-micro: ~$7.67/month
- Storage (20GB): ~$0.40/month
- Backups: ~$0.20/month

**Cloud Storage:**
- Storage (10GB): ~$0.20/month
- Operations: ~$0.10/month

**Cloud Build:**
- Build minutes: ~$0.50/month

**Total Estimated: ~$25-50/month**

### Cost Optimization Tips

1. Use Cloud Run min-instances=0 for cost savings (cold starts acceptable)
2. Use Cloud SQL db-f1-micro for development, upgrade for production
3. Enable Cloud SQL automatic backups (7-day retention)
4. Use Cloud Storage lifecycle policies to archive old files
5. Monitor usage with Cloud Monitoring

---

## Rollback Plan

### If Deployment Fails:

1. **Keep Previous Version:**
   ```bash
   # Cloud Run keeps previous revisions
   gcloud run services update-traffic karma-backend \
     --to-revisions PREVIOUS_REVISION=100
   ```

2. **Database Rollback:**
   - Restore from Cloud SQL backup
   - Or migrate back to SQLite if needed

3. **File Storage Rollback:**
   - Download from Cloud Storage
   - Restore to local filesystem

4. **Service Rollback:**
   ```bash
   # List revisions
   gcloud run revisions list --service karma-backend
   
   # Rollback to specific revision
   gcloud run services update-traffic karma-backend \
     --to-revisions REVISION_NAME=100
   ```

---

## Implementation Checklist

### Phase 1: Preparation
- [ ] Set up GCP project and billing
- [ ] Enable required APIs
- [ ] Install and configure gcloud CLI
- [ ] Create service accounts
- [ ] Set up Secret Manager

### Phase 2: Database Migration
- [ ] Create Cloud SQL PostgreSQL instance
- [ ] Update backend database connection code
- [ ] Update requirements.txt
- [ ] Test database connection locally
- [ ] Run schema migrations
- [ ] Migrate existing data (if any)

### Phase 3: File Storage Migration
- [ ] Create Cloud Storage bucket
- [ ] Create storage service abstraction
- [ ] Update tools.py to use Cloud Storage
- [ ] Migrate existing files
- [ ] Test file operations

### Phase 4: Backend Deployment
- [ ] Update Dockerfile if needed
- [ ] Update configuration for Cloud Run
- [ ] Build and push Docker image
- [ ] Deploy to Cloud Run
- [ ] Configure environment variables
- [ ] Test backend endpoints

### Phase 5: Frontend Deployment
- [ ] Update API client configuration
- [ ] Update Dockerfile nginx config
- [ ] Build and push Docker image
- [ ] Deploy to Cloud Run
- [ ] Test frontend-backend integration

### Phase 6: Testing & Validation
- [ ] Health check tests
- [ ] Database connectivity tests
- [ ] Cloud Storage access tests
- [ ] End-to-end user flow tests
- [ ] Performance testing
- [ ] Security review

### Phase 7: Production Readiness
- [ ] Set up monitoring and alerts
- [ ] Configure custom domain (optional)
- [ ] Set up CI/CD pipeline (optional)
- [ ] Document deployment process
- [ ] Train team on deployment

---

## Next Steps

1. Review and approve this plan
2. Set up GCP project and prerequisites
3. Begin with Phase 1 (Preparation)
4. Proceed through phases sequentially
5. Test thoroughly before production traffic

---

## Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Cloud Storage Documentation](https://cloud.google.com/storage/docs)
- [SQLAlchemy PostgreSQL Guide](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)
- [Google Cloud Secret Manager](https://cloud.google.com/secret-manager/docs)

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-17  
**Author:** Deployment Planning
