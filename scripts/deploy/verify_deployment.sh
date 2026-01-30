#!/bin/bash
# Script to verify deployment and troubleshoot admin access

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"
BACKEND_SERVICE="karma-backend"
FRONTEND_SERVICE="karma-frontend"

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: GCP_PROJECT_ID not set${NC}"
    echo "Set it with: export GCP_PROJECT_ID=your-project-id"
    exit 1
fi

echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Karma Deployment Verification     ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

# 1. Check service status
echo -e "${GREEN}1. Checking service status...${NC}"
echo ""

BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE --region $REGION --format 'value(status.url)' --project=$PROJECT_ID 2>/dev/null || echo "")
FRONTEND_URL=$(gcloud run services describe $FRONTEND_SERVICE --region $REGION --format 'value(status.url)' --project=$PROJECT_ID 2>/dev/null || echo "")

if [ -n "$BACKEND_URL" ]; then
    echo -e "${GREEN}✅ Backend: $BACKEND_URL${NC}"
else
    echo -e "${RED}❌ Backend service not found${NC}"
fi

if [ -n "$FRONTEND_URL" ]; then
    echo -e "${GREEN}✅ Frontend: $FRONTEND_URL${NC}"
else
    echo -e "${RED}❌ Frontend service not found${NC}"
fi

echo ""

# 2. Check backend environment variables
echo -e "${GREEN}2. Checking backend environment variables...${NC}"
echo ""

ENV_VARS=$(gcloud run services describe $BACKEND_SERVICE --region $REGION --format='value(spec.template.spec.containers[0].env)' --project=$PROJECT_ID 2>/dev/null || echo "")

if echo "$ENV_VARS" | grep -q "ADMIN_USER_IDS"; then
    ADMIN_USER_IDS=$(gcloud run services describe $BACKEND_SERVICE --region $REGION --format='value(spec.template.spec.containers[0].env[?(@.name=="ADMIN_USER_IDS")].value)' --project=$PROJECT_ID 2>/dev/null || echo "")
    echo -e "${GREEN}✅ ADMIN_USER_IDS: ${ADMIN_USER_IDS:-'(not set)'}${NC}"
else
    echo -e "${YELLOW}⚠️  ADMIN_USER_IDS not found in environment variables${NC}"
fi

if echo "$ENV_VARS" | grep -q "ADMIN_EMAILS"; then
    ADMIN_EMAILS=$(gcloud run services describe $BACKEND_SERVICE --region $REGION --format='value(spec.template.spec.containers[0].env[?(@.name=="ADMIN_EMAILS")].value)' --project=$PROJECT_ID 2>/dev/null || echo "")
    echo -e "${GREEN}✅ ADMIN_EMAILS: ${ADMIN_EMAILS:-'(not set)'}${NC}"
else
    echo -e "${YELLOW}⚠️  ADMIN_EMAILS not found in environment variables${NC}"
fi

OPENAI_KARMA=$(gcloud run services describe $BACKEND_SERVICE --region $REGION --format='value(spec.template.spec.containers[0].env[?(@.name=="OPENAI_KARMA")].value)' --project=$PROJECT_ID 2>/dev/null || echo "false")
echo -e "${BLUE}ℹ️  OPENAI_KARMA: ${OPENAI_KARMA}${NC}"

echo ""

# 3. Check backend secrets
echo -e "${GREEN}3. Checking backend secrets...${NC}"
echo ""

SECRETS=$(gcloud run services describe $BACKEND_SERVICE --region $REGION --format='value(spec.template.spec.containers[0].env[?(@.valueFrom)]' --project=$PROJECT_ID 2>/dev/null || echo "")

if echo "$SECRETS" | grep -q "OPENAI_API_KEY"; then
    echo -e "${GREEN}✅ OPENAI_API_KEY secret configured${NC}"
else
    echo -e "${YELLOW}⚠️  OPENAI_API_KEY secret not found${NC}"
fi

if echo "$SECRETS" | grep -q "DATABASE_PASSWORD"; then
    echo -e "${GREEN}✅ DATABASE_PASSWORD secret configured${NC}"
else
    echo -e "${YELLOW}⚠️  DATABASE_PASSWORD secret not found${NC}"
fi

echo ""

# 4. Check deployed image
echo -e "${GREEN}4. Checking deployed images...${NC}"
echo ""

BACKEND_IMAGE=$(gcloud run services describe $BACKEND_SERVICE --region $REGION --format='value(spec.template.spec.containers[0].image)' --project=$PROJECT_ID 2>/dev/null || echo "")
FRONTEND_IMAGE=$(gcloud run services describe $FRONTEND_SERVICE --region $REGION --format='value(spec.template.spec.containers[0].image)' --project=$PROJECT_ID 2>/dev/null || echo "")

echo -e "${BLUE}Backend image: ${BACKEND_IMAGE}${NC}"
echo -e "${BLUE}Frontend image: ${FRONTEND_IMAGE}${NC}"

# Get image creation time
if [ -n "$BACKEND_IMAGE" ]; then
    IMAGE_TAG=$(echo "$BACKEND_IMAGE" | cut -d':' -f2)
    if [ "$IMAGE_TAG" = "latest" ]; then
        IMAGE_DIGEST=$(gcloud container images describe "$BACKEND_IMAGE" --format='value(image_summary.digest)' 2>/dev/null || echo "")
        if [ -n "$IMAGE_DIGEST" ]; then
            IMAGE_TIME=$(gcloud container images describe "$BACKEND_IMAGE" --format='value(image_summary.create_time)' 2>/dev/null || echo "")
            echo -e "${BLUE}Backend image created: ${IMAGE_TIME}${NC}"
        fi
    fi
fi

echo ""

# 5. Test backend health and admin endpoint
echo -e "${GREEN}5. Testing backend endpoints...${NC}"
echo ""

if [ -n "$BACKEND_URL" ]; then
    # Test health endpoint
    HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/health" 2>/dev/null || echo "000")
    if [ "$HEALTH_RESPONSE" = "200" ]; then
        echo -e "${GREEN}✅ Backend health check: OK${NC}"
    else
        echo -e "${RED}❌ Backend health check failed (HTTP $HEALTH_RESPONSE)${NC}"
    fi
    
    # Check if admin endpoint exists (will return 401/403 without auth, but that's expected)
    ADMIN_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/api/admin/check" 2>/dev/null || echo "000")
    if [ "$ADMIN_CHECK" = "401" ] || [ "$ADMIN_CHECK" = "403" ] || [ "$ADMIN_CHECK" = "200" ]; then
        echo -e "${GREEN}✅ Admin endpoint exists (HTTP $ADMIN_CHECK - auth required)${NC}"
    else
        echo -e "${RED}❌ Admin endpoint not found (HTTP $ADMIN_CHECK)${NC}"
        echo -e "${YELLOW}   This might mean the latest code wasn't deployed${NC}"
    fi
else
    echo -e "${RED}❌ Cannot test endpoints - backend URL not found${NC}"
fi

echo ""

# 6. Check recent logs for errors
echo -e "${GREEN}6. Checking recent backend logs (last 10 lines)...${NC}"
echo ""

gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$BACKEND_SERVICE" \
    --limit 10 \
    --format="table(timestamp,severity,textPayload)" \
    --project=$PROJECT_ID 2>/dev/null | head -15 || echo -e "${YELLOW}Could not fetch logs${NC}"

echo ""

# 7. Recommendations
echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Recommendations                   ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

if [ -z "$ADMIN_USER_IDS" ] && [ -z "$ADMIN_EMAILS" ]; then
    echo -e "${YELLOW}⚠️  Admin configuration not found!${NC}"
    echo ""
    echo "To set admin user IDs:"
    echo "  gcloud run services update $BACKEND_SERVICE \\"
    echo "    --region $REGION \\"
    echo "    --update-env-vars ADMIN_USER_IDS=your_user_id_here \\"
    echo "    --project=$PROJECT_ID"
    echo ""
    echo "To set admin emails:"
    echo "  gcloud run services update $BACKEND_SERVICE \\"
    echo "    --region $REGION \\"
    echo "    --update-env-vars ADMIN_EMAILS=admin@example.com \\"
    echo "    --project=$PROJECT_ID"
    echo ""
fi

echo "To rebuild and redeploy:"
echo "  ./scripts/deploy/deploy.sh"
echo "  (Choose option 3 or 4 to rebuild and deploy)"
echo ""

echo "To check your Clerk user ID:"
echo "  1. Log in to your app"
echo "  2. Open browser console"
echo "  3. Check the JWT token or API responses"
echo "  4. Or check Clerk dashboard for user IDs"
echo ""

echo "To verify admin access:"
echo "  1. Make sure ADMIN_USER_IDS or ADMIN_EMAILS is set"
echo "  2. Restart the backend service:"
echo "     gcloud run services update $BACKEND_SERVICE --region $REGION --project=$PROJECT_ID"
echo "  3. Log in and check if Admin link appears in navigation"
echo ""
