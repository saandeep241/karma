# Deployment Scripts

This directory contains scripts for deploying the Karma application to Google Cloud Platform.

## Scripts

### `deploy.sh`
Main deployment script that handles the complete deployment process:
- Enables required GCP APIs
- Sets up Cloud Build and Compute Engine permissions
- Creates Cloud SQL PostgreSQL instance
- Creates Cloud Storage bucket
- Creates service accounts
- Builds and pushes Docker images
- Deploys backend and frontend services to Cloud Run

**Usage:**
```bash
export GCP_PROJECT_ID=your-project-id
./scripts/deploy/deploy.sh
```

### `create_database_secret.sh`
Utility script to create or update the database password secret in Secret Manager and configure Cloud Run to use it.

**Usage:**
```bash
export GCP_PROJECT_ID=your-project-id
./scripts/deploy/create_database_secret.sh
```

The script will prompt you for the database password if not provided via `DB_PASSWORD` environment variable.

### `restart_backend.sh`
Utility script to restart the backend Cloud Run service.

**Usage:**
```bash
export GCP_PROJECT_ID=your-project-id
./scripts/deploy/restart_backend.sh
```

### `rebuild_frontend.sh`
Rebuilds the frontend Docker image with the latest code (uses `--no-cache` for fresh builds) and updates the Cloud Run service.

**Usage:**
```bash
export GCP_PROJECT_ID=your-project-id
./scripts/deploy/rebuild_frontend.sh
```

### `create_openai_secret.sh`
Utility script to create or update the OpenAI API key secret in Secret Manager and configure Cloud Run to use it.

**Usage:**
```bash
export GCP_PROJECT_ID=your-project-id
./scripts/deploy/create_openai_secret.sh
```

The script will prompt you for the OpenAI API key.

### `verify_deployment.sh`
Verification script to check deployment status, environment variables, and test endpoints.

**Usage:**
```bash
export GCP_PROJECT_ID=your-project-id
./scripts/deploy/verify_deployment.sh
```

This script checks:
- Service status and URLs
- Environment variables (including admin config)
- Deployed images
- Backend endpoints
- Recent logs

## Prerequisites

- `gcloud` CLI installed and authenticated
- GCP project with billing enabled
- Required GCP APIs enabled (the deploy script handles this)

## Environment Variables

### Required
- `GCP_PROJECT_ID` - Your GCP project ID (required)

### Optional
- `GCP_REGION` - GCP region (defaults to `us-central1`)
- `ENABLE_AI` - Set to `"true"` to enable AI mode, `"false"` for dummy mode (defaults to `false`)
- `DB_PASSWORD` - Database password (for `create_database_secret.sh`)

### Token Rate Limiting (Backend)
- `DEFAULT_MONTHLY_TOKEN_LIMIT` - Default monthly token limit per user (defaults to `1000000` = 1M tokens)
- `ADMIN_USER_IDS` - Comma-separated list of Clerk user IDs for admin access
- `ADMIN_EMAILS` - Comma-separated list of email addresses for admin access

These can be set during deployment or updated later:
```bash
gcloud run services update karma-backend \
  --region us-central1 \
  --update-env-vars ADMIN_USER_IDS=user_abc123,user_def456 \
  --project=$PROJECT_ID
```

## Token Rate Limiting

The deployment script supports configuring token rate limiting during deployment:

1. **During deployment**: The script will prompt you to set admin configuration
2. **After deployment**: Update via `gcloud run services update`:

```bash
# Set admin user IDs
gcloud run services update karma-backend \
  --region us-central1 \
  --update-env-vars ADMIN_USER_IDS=user_abc123,user_def456 \
  --project=$PROJECT_ID

# Set admin emails
gcloud run services update karma-backend \
  --region us-central1 \
  --update-env-vars ADMIN_EMAILS=admin@example.com \
  --project=$PROJECT_ID

# Set custom default token limit
gcloud run services update karma-backend \
  --region us-central1 \
  --update-env-vars DEFAULT_MONTHLY_TOKEN_LIMIT=2000000 \
  --project=$PROJECT_ID
```

For more details on token rate limiting, see the main [README.md](../../README.md#-token-rate-limiting).

## Documentation

For detailed deployment instructions, see:
- [README.md](../../README.md) - Main project documentation with rate limiting details
