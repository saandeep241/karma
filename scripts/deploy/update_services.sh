#!/bin/bash
# Update Cloud Run services to use the latest images

PROJECT_ID="${GCP_PROJECT_ID:-project-67e2b006-527b-40d9-901}"
REGION="${GCP_REGION:-us-central1}"
BACKEND_SERVICE="karma-backend"
FRONTEND_SERVICE="karma-frontend"

echo "🔄 Updating Cloud Run Services to Use Latest Images"
echo "===================================================="
echo ""
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Update backend
echo "Updating backend service..."
gcloud run services update $BACKEND_SERVICE \
    --region=$REGION \
    --project=$PROJECT_ID \
    --image=gcr.io/$PROJECT_ID/$BACKEND_SERVICE:latest

BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE --region=$REGION --format='value(status.url)' --project=$PROJECT_ID)
echo "✅ Backend updated: $BACKEND_URL"
echo ""

# Update frontend
echo "Updating frontend service..."
gcloud run services update $FRONTEND_SERVICE \
    --region=$REGION \
    --project=$PROJECT_ID \
    --image=gcr.io/$PROJECT_ID/$FRONTEND_SERVICE:latest

FRONTEND_URL=$(gcloud run services describe $FRONTEND_SERVICE --region=$REGION --format='value(status.url)' --project=$PROJECT_ID)
echo "✅ Frontend updated: $FRONTEND_URL"
echo ""

echo "✅ Both services updated to use latest images!"
echo ""
echo "Backend: $BACKEND_URL"
echo "Frontend: $FRONTEND_URL"
