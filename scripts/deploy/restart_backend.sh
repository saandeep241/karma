#!/bin/bash
# Restart the backend Cloud Run service

PROJECT_ID="${GCP_PROJECT_ID:-project-67e2b006-527b-40d9-901}"
REGION="${GCP_REGION:-us-central1}"
BACKEND_SERVICE="karma-backend"

echo "🔄 Restarting Backend Service"
echo "============================="
echo ""
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $BACKEND_SERVICE"
echo ""

# Method 1: Update with a no-op change (forces restart)
echo "Updating service to trigger restart..."
gcloud run services update $BACKEND_SERVICE \
    --region=$REGION \
    --project=$PROJECT_ID \
    --no-traffic

echo ""
echo "✅ Service restarted!"
echo ""
echo "Service URL:"
gcloud run services describe $BACKEND_SERVICE \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format='value(status.url)'
