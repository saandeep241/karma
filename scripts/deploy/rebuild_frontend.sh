#!/bin/bash
# Rebuild frontend with correct backend URL

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root so relative paths work
cd "$PROJECT_ROOT"

PROJECT_ID="${GCP_PROJECT_ID:-project-67e2b006-527b-40d9-901}"
REGION="${GCP_REGION:-us-central1}"
BACKEND_SERVICE="karma-backend"
FRONTEND_SERVICE="karma-frontend"

echo "🔨 Rebuilding Frontend with Backend URL"
echo "======================================="
echo ""
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Get backend URL
echo "Getting backend URL..."
BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format='value(status.url)' 2>/dev/null)

if [ -z "$BACKEND_URL" ]; then
    echo "❌ Backend service not found!"
    echo "Please deploy the backend first."
    exit 1
fi

echo "✅ Backend URL: $BACKEND_URL"
echo "   API URL: ${BACKEND_URL}/api"
echo ""

# Create cloudbuild.yaml
echo "Creating build configuration..."
cat > /tmp/frontend-cloudbuild.yaml << EOF
steps:
- name: 'gcr.io/cloud-builders/docker'
  args:
    - 'build'
    - '--build-arg'
    - 'VITE_API_URL=${BACKEND_URL}/api'
    - '-t'
    - 'gcr.io/$PROJECT_ID/$FRONTEND_SERVICE'
    - '.'
images:
- 'gcr.io/$PROJECT_ID/$FRONTEND_SERVICE'
EOF

echo "Building frontend image with VITE_API_URL=${BACKEND_URL}/api..."
gcloud builds submit \
    --config=/tmp/frontend-cloudbuild.yaml \
    --project=$PROJECT_ID \
    ./frontend

BUILD_EXIT=$?

# Cleanup
rm -f /tmp/frontend-cloudbuild.yaml

if [ $BUILD_EXIT -eq 0 ]; then
    echo ""
    echo "✅ Frontend image built successfully!"
    echo ""
    echo "Updating Cloud Run service..."
    gcloud run services update $FRONTEND_SERVICE \
        --region=$REGION \
        --project=$PROJECT_ID \
        --image=gcr.io/$PROJECT_ID/$FRONTEND_SERVICE
    
    FRONTEND_URL=$(gcloud run services describe $FRONTEND_SERVICE \
        --region=$REGION \
        --project=$PROJECT_ID \
        --format='value(status.url)')
    
    echo ""
    echo "✅ Frontend updated: $FRONTEND_URL"
    echo ""
    echo "The frontend should now call the backend at: ${BACKEND_URL}/api"
else
    echo ""
    echo "❌ Build failed!"
    exit 1
fi
