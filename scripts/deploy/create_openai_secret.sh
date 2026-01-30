#!/bin/bash
# Script to create/update OpenAI API key secret in Secret Manager

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get project ID
PROJECT_ID="${GCP_PROJECT_ID:-}"
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: GCP_PROJECT_ID not set${NC}"
    echo "Set it with: export GCP_PROJECT_ID=your-project-id"
    exit 1
fi

SECRET_NAME="openai-api-key"
BACKEND_SERVICE="karma-backend"
REGION="${GCP_REGION:-us-central1}"

echo -e "${GREEN}Creating/updating OpenAI API key secret...${NC}"

# Check if secret exists
if gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID &>/dev/null; then
    echo -e "${YELLOW}Secret $SECRET_NAME already exists. Updating...${NC}"
    read -sp "Enter your OpenAI API key: " API_KEY
    echo ""
    
    # Update existing secret
    echo -n "$API_KEY" | gcloud secrets versions add $SECRET_NAME \
        --data-file=- \
        --project=$PROJECT_ID
    
    echo -e "${GREEN}✅ Secret updated${NC}"
else
    echo -e "${YELLOW}Creating new secret $SECRET_NAME...${NC}"
    read -sp "Enter your OpenAI API key: " API_KEY
    echo ""
    
    # Create new secret
    echo -n "$API_KEY" | gcloud secrets create $SECRET_NAME \
        --data-file=- \
        --replication-policy="automatic" \
        --project=$PROJECT_ID
    
    echo -e "${GREEN}✅ Secret created${NC}"
fi

# Grant backend service account access to the secret
BACKEND_SA="karma-backend@${PROJECT_ID}.iam.gserviceaccount.com"
echo -e "${YELLOW}Granting backend service account access to secret...${NC}"

gcloud secrets add-iam-policy-binding $SECRET_NAME \
    --member="serviceAccount:${BACKEND_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID

echo -e "${GREEN}✅ Service account granted access${NC}"

# Update Cloud Run service to use the secret
echo -e "${YELLOW}Updating Cloud Run service to use secret...${NC}"

gcloud run services update $BACKEND_SERVICE \
    --region $REGION \
    --update-secrets "OPENAI_API_KEY=${SECRET_NAME}:latest" \
    --project=$PROJECT_ID

echo -e "${GREEN}✅ Cloud Run service updated${NC}"
echo ""
echo -e "${GREEN}Done! The backend service will now have access to OPENAI_API_KEY.${NC}"
