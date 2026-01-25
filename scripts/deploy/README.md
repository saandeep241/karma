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

## Prerequisites

- `gcloud` CLI installed and authenticated
- GCP project with billing enabled
- Required GCP APIs enabled (the deploy script handles this)

## Environment Variables

- `GCP_PROJECT_ID` - Your GCP project ID (required)
- `GCP_REGION` - GCP region (defaults to `us-central1`)
- `ENABLE_AI` - Set to `"true"` to enable AI mode, `"false"` for dummy mode (defaults to `false`)
- `DB_PASSWORD` - Database password (for `create_database_secret.sh`)

## Documentation

For detailed deployment instructions, see:
- [DEPLOYMENT_QUICK_START.md](../../DEPLOYMENT_QUICK_START.md) - Quick start guide
- [GCP_DEPLOYMENT_PLAN.md](../../GCP_DEPLOYMENT_PLAN.md) - Detailed deployment architecture
