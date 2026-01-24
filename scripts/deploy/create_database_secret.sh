#!/bin/bash
# Create database password secret and configure Cloud Run to use it

PROJECT_ID="${GCP_PROJECT_ID:-project-67e2b006-527b-40d9-901}"
REGION="${GCP_REGION:-us-central1}"
BACKEND_SERVICE="karma-backend"
BACKEND_SA="karma-backend@${PROJECT_ID}.iam.gserviceaccount.com"
SECRET_NAME="database-password"

echo "🔐 Creating Database Password Secret"
echo "====================================="
echo ""
echo "Project: $PROJECT_ID"
echo "Service: $BACKEND_SERVICE"
echo "Secret: $SECRET_NAME"
echo ""

# Get the database password
if [ -z "$DB_PASSWORD" ]; then
    echo "Enter the database password (the one used when creating the database):"
    read -sp "Password: " DB_PASSWORD
    echo ""
    echo ""
fi

if [ -z "$DB_PASSWORD" ]; then
    echo "❌ Password is required!"
    exit 1
fi

# Check if secret already exists
if gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID &>/dev/null; then
    echo "⚠️  Secret $SECRET_NAME already exists. Updating it..."
    echo -n "$DB_PASSWORD" | gcloud secrets versions add $SECRET_NAME \
        --data-file=- \
        --project=$PROJECT_ID
    echo "✅ Secret updated"
else
    echo "Creating secret $SECRET_NAME..."
    echo -n "$DB_PASSWORD" | gcloud secrets create $SECRET_NAME \
        --data-file=- \
        --project=$PROJECT_ID
    echo "✅ Secret created"
fi

# Grant access to backend service account
echo ""
echo "Granting access to backend service account..."
gcloud secrets add-iam-policy-binding $SECRET_NAME \
    --member="serviceAccount:${BACKEND_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID \
    --quiet

echo "✅ Access granted"
echo ""

# Update Cloud Run service to use the secret
echo "Updating Cloud Run service to use secret..."
gcloud run services update $BACKEND_SERVICE \
    --region=$REGION \
    --project=$PROJECT_ID \
    --update-secrets="DATABASE_PASSWORD=${SECRET_NAME}:latest"

echo ""
echo "✅ Done! The backend service is now using Secret Manager for the database password."
echo ""
echo "The service will restart automatically with the new configuration."
