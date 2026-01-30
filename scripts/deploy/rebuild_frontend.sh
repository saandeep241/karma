#!/bin/bash
# Rebuild frontend with correct backend URL (with --no-cache for fresh builds)

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root so relative paths work
cd "$PROJECT_ROOT"

PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"
BACKEND_SERVICE="karma-backend"
FRONTEND_SERVICE="karma-frontend"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: GCP_PROJECT_ID not set${NC}"
    echo "Set it with: export GCP_PROJECT_ID=your-project-id"
    exit 1
fi

echo -e "${GREEN}🔨 Rebuilding Frontend with Backend URL${NC}"
echo ""

# Get backend URL
echo "Getting backend URL..."
BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format='value(status.url)' 2>/dev/null)

if [ -z "$BACKEND_URL" ]; then
    echo -e "${RED}❌ Backend service not found!${NC}"
    echo "Please deploy the backend first."
    exit 1
fi

echo -e "${GREEN}✅ Backend URL: $BACKEND_URL${NC}"
echo "   API URL: ${BACKEND_URL}/api"
echo ""

# Create cloudbuild.yaml with --no-cache for fresh build
echo "Creating build configuration (with --no-cache)..."
cat > /tmp/frontend-cloudbuild.yaml << EOF
steps:
- name: 'gcr.io/cloud-builders/docker'
  args:
    - 'build'
    - '--no-cache'
    - '--build-arg'
    - 'VITE_API_URL=${BACKEND_URL}/api'
    - '-t'
    - 'gcr.io/$PROJECT_ID/$FRONTEND_SERVICE:latest'
    - '.'
images:
- 'gcr.io/$PROJECT_ID/$FRONTEND_SERVICE:latest'
EOF

echo "Building frontend image with VITE_API_URL=${BACKEND_URL}/api (no cache)..."
gcloud builds submit \
    --config=/tmp/frontend-cloudbuild.yaml \
    --project=$PROJECT_ID \
    ./frontend

BUILD_EXIT=$?

# Cleanup
rm -f /tmp/frontend-cloudbuild.yaml

if [ $BUILD_EXIT -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Frontend image built successfully!${NC}"
    echo ""
    echo "Updating Cloud Run service..."
    gcloud run services update $FRONTEND_SERVICE \
        --region=$REGION \
        --project=$PROJECT_ID \
        --image=gcr.io/$PROJECT_ID/$FRONTEND_SERVICE:latest
    
    FRONTEND_URL=$(gcloud run services describe $FRONTEND_SERVICE \
        --region=$REGION \
        --project=$PROJECT_ID \
        --format='value(status.url)')
    
    echo ""
    echo -e "${GREEN}✅ Frontend updated: $FRONTEND_URL${NC}"
    echo ""
    echo "The frontend should now call the backend at: ${BACKEND_URL}/api"
else
    echo ""
    echo -e "${RED}❌ Build failed!${NC}"
    exit 1
fi
