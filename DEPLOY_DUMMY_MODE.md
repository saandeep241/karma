# Deploying with Dummy Mode (AI Disabled)

This guide shows how to deploy Karma with AI disabled (dummy mode). This is perfect for:
- Testing the deployment
- Reducing costs (no OpenAI API calls)
- Faster responses (no AI processing)

## Quick Deploy with Dummy Mode

### Option 1: Using the Deployment Script

```bash
# Set your project ID
export GCP_PROJECT_ID=your-project-id

# Set AI to false (dummy mode)
export ENABLE_AI=false

# Run deployment script
./scripts/deploy/deploy.sh
```

When prompted, choose "N" for "Enable AI?" to deploy in dummy mode.

### Option 2: Manual Deployment

#### Step 1: Build Backend Image

```bash
gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/karma-backend ./backend
```

#### Step 2: Deploy Backend (Dummy Mode)

```bash
# Get connection name
CONNECTION_NAME=$(gcloud sql instances describe karma-db --format='value(connectionName)')

# Deploy with OPENAI_KARMA=false
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
```

**Note**: No `OPENAI_API_KEY` secret needed in dummy mode!

#### Step 3: Deploy Frontend

```bash
# Get backend URL
BACKEND_URL=$(gcloud run services describe karma-backend --region us-central1 --format 'value(status.url)')

# Build frontend
gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/karma-frontend ./frontend

# Deploy frontend
gcloud run deploy karma-frontend \
  --image gcr.io/$GCP_PROJECT_ID/karma-frontend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "VITE_API_URL=$BACKEND_URL/api" \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60
```

## What Works in Dummy Mode

✅ **All core features work:**
- Task creation and management
- Task status updates
- Subtask management
- Database operations
- Cloud Storage (if enabled)
- User authentication (if configured)

⚠️ **AI features use dummy data:**
- Task analysis returns basic/default values
- Task enrichment uses heuristics (no web search)
- Quick wins are generated from templates
- Task suggestions use simple matching

## Switching to AI Mode Later

To enable AI after deployment:

```bash
# Store OpenAI API key
echo -n "your-openai-api-key" | gcloud secrets create openai-api-key --data-file=-

# Grant access
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:karma-backend@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Update service
gcloud run services update karma-backend \
  --update-secrets OPENAI_API_KEY=openai-api-key:latest \
  --set-env-vars "OPENAI_KARMA=true" \
  --region us-central1
```

## Benefits of Dummy Mode

1. **No API costs** - No OpenAI charges
2. **Faster deployment** - No need to set up OpenAI keys
3. **Perfect for testing** - Verify infrastructure works
4. **Lower latency** - No AI processing time
5. **Easier debugging** - Predictable responses

## Testing Dummy Mode

After deployment, test with:

```bash
# Get frontend URL
FRONTEND_URL=$(gcloud run services describe karma-frontend --region us-central1 --format 'value(status.url)')

# Test health endpoint
curl $FRONTEND_URL/api/health

# Expected response should show:
# "dummy_mode": true
# "ai_enabled": false
```
