#!/bin/bash
# GCP Deployment Script for Karma Application
# This script helps deploy the Karma app to Google Cloud Run

set -e  # Exit on error

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root so relative paths work
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"
BACKEND_SERVICE="karma-backend"
FRONTEND_SERVICE="karma-frontend"
DB_INSTANCE="karma-db"
DB_NAME="karma"
DB_USER="karma_user"
GCS_BUCKET="karma-app-data"
ENABLE_AI="${ENABLE_AI:-false}"  # Set to "true" to enable AI, "false" for dummy mode

# Functions
print_header() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}========================================${NC}"
}

print_error() {
    echo -e "${RED}❌ Error: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI not found. Install from: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    print_success "gcloud CLI found"
    
    # Check docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Install from: https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_success "Docker found"
    
    # Check project ID
    if [ -z "$PROJECT_ID" ]; then
        print_error "GCP_PROJECT_ID not set. Set it with: export GCP_PROJECT_ID=your-project-id"
        exit 1
    fi
    print_success "Project ID: $PROJECT_ID"
    
    # Set project
    gcloud config set project $PROJECT_ID
    print_success "gcloud project set to $PROJECT_ID"
}

enable_apis() {
    print_header "Enabling Required APIs"
    
    gcloud services enable \
        run.googleapis.com \
        sqladmin.googleapis.com \
        storage-component.googleapis.com \
        cloudbuild.googleapis.com \
        secretmanager.googleapis.com \
        artifactregistry.googleapis.com \
        containerregistry.googleapis.com \
        --project=$PROJECT_ID
    
    print_success "APIs enabled"
}

setup_cloud_build_permissions() {
    print_header "Setting Up Cloud Build Permissions"
    
    # Get project number and service accounts
    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
    CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
    COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
    
    print_warning "Granting Cloud Build and Compute Engine service accounts necessary permissions..."
    
    # Grant Cloud Build service account permissions
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${CLOUD_BUILD_SA}" \
        --role="roles/storage.admin" \
        --condition=None \
        --project=$PROJECT_ID
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${CLOUD_BUILD_SA}" \
        --role="roles/run.admin" \
        --condition=None \
        --project=$PROJECT_ID
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${CLOUD_BUILD_SA}" \
        --role="roles/iam.serviceAccountUser" \
        --condition=None \
        --project=$PROJECT_ID
    
    # Grant Container Registry/Artifact Registry permissions (for pushing images)
    # Note: Using admin role because writer doesn't have uploadArtifacts permission
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${CLOUD_BUILD_SA}" \
        --role="roles/artifactregistry.admin" \
        --condition=None \
        --project=$PROJECT_ID
    
    # Also grant storage.objectAdmin for GCR (legacy Container Registry)
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${CLOUD_BUILD_SA}" \
        --role="roles/storage.objectAdmin" \
        --condition=None \
        --project=$PROJECT_ID
    
    # Grant Compute Engine default service account permissions (for local builds)
    # Note: This account is used when running gcloud builds submit from local machine
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${COMPUTE_SA}" \
        --role="roles/storage.admin" \
        --condition=None \
        --project=$PROJECT_ID
    
    # Grant artifactregistry.admin (needed for pushing to GCR)
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${COMPUTE_SA}" \
        --role="roles/artifactregistry.admin" \
        --condition=None \
        --project=$PROJECT_ID
    
    # Grant logging permission (for Cloud Build logs)
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${COMPUTE_SA}" \
        --role="roles/logging.logWriter" \
        --condition=None \
        --project=$PROJECT_ID
    
    print_success "Cloud Build and Compute Engine permissions configured"
    print_warning "Cloud Build SA: ${CLOUD_BUILD_SA}"
    print_warning "Compute Engine SA: ${COMPUTE_SA}"
}

create_cloud_sql() {
    print_header "Creating Cloud SQL PostgreSQL Instance"
    
    # Check if instance already exists
    if gcloud sql instances describe $DB_INSTANCE --project=$PROJECT_ID &>/dev/null; then
        print_warning "Cloud SQL instance $DB_INSTANCE already exists"
        return
    fi
    
    # Prompt for database password
    echo -n "Enter database password (or press Enter to generate): "
    read -s DB_PASSWORD
    echo
    
    if [ -z "$DB_PASSWORD" ]; then
        DB_PASSWORD=$(openssl rand -base64 32)
        print_success "Generated password: $DB_PASSWORD"
        echo "⚠️  SAVE THIS PASSWORD - you'll need it for configuration!"
    fi
    
    # Create instance
    gcloud sql instances create $DB_INSTANCE \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=$REGION \
        --root-password=$DB_PASSWORD \
        --storage-type=SSD \
        --storage-size=20GB \
        --backup-start-time=03:00 \
        --project=$PROJECT_ID
    
    print_success "Cloud SQL instance created"
    
    # Create database
    gcloud sql databases create $DB_NAME \
        --instance=$DB_INSTANCE \
        --project=$PROJECT_ID
    
    print_success "Database '$DB_NAME' created"
    
    # Create user
    gcloud sql users create $DB_USER \
        --instance=$DB_INSTANCE \
        --password=$DB_PASSWORD \
        --project=$PROJECT_ID
    
    print_success "Database user '$DB_USER' created"
    
    # Get connection name
    CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE --format='value(connectionName)' --project=$PROJECT_ID)
    print_success "Connection name: $CONNECTION_NAME"
    
    # Create secret for database password
    print_warning "Creating database password secret..."
    SECRET_NAME="database-password"
    BACKEND_SA="karma-backend@$PROJECT_ID.iam.gserviceaccount.com"
    
    # Check if secret already exists
    if gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID &>/dev/null; then
        print_warning "Secret $SECRET_NAME already exists. Updating it..."
        echo -n "$DB_PASSWORD" | gcloud secrets versions add $SECRET_NAME \
            --data-file=- \
            --project=$PROJECT_ID \
            --quiet
    else
        echo -n "$DB_PASSWORD" | gcloud secrets create $SECRET_NAME \
            --data-file=- \
            --project=$PROJECT_ID \
            --quiet
        print_success "Secret $SECRET_NAME created"
    fi
    
    # Grant access to backend service account
    gcloud secrets add-iam-policy-binding $SECRET_NAME \
        --member="serviceAccount:${BACKEND_SA}" \
        --role="roles/secretmanager.secretAccessor" \
        --project=$PROJECT_ID \
        --quiet
    
    print_success "Database password stored in Secret Manager"
    echo "Save these values:"
    echo "  DATABASE_PASSWORD=$DB_PASSWORD (stored in Secret Manager)"
    echo "  CLOUD_SQL_CONNECTION_NAME=$CONNECTION_NAME"
}

create_cloud_storage() {
    print_header "Creating Cloud Storage Bucket"
    
    BACKEND_SA="karma-backend@$PROJECT_ID.iam.gserviceaccount.com"
    
    # Check if bucket exists
    if gsutil ls -b gs://$GCS_BUCKET &>/dev/null; then
        print_warning "Bucket gs://$GCS_BUCKET already exists"
    else
        gsutil mb -p $PROJECT_ID -l $REGION gs://$GCS_BUCKET
        print_success "Bucket gs://$GCS_BUCKET created"
    fi
    
    # Grant bucket-level permissions to backend service account (least privilege)
    print_warning "Granting bucket-level permissions to backend service account..."
    
    # Grant storage.buckets.get (to check if bucket exists)
    gsutil iam ch serviceAccount:${BACKEND_SA}:roles/storage.legacyBucketReader gs://$GCS_BUCKET
    
    # Grant storage.objects.* (to read/write objects in the bucket)
    gsutil iam ch serviceAccount:${BACKEND_SA}:roles/storage.objectAdmin gs://$GCS_BUCKET
    
    print_success "Bucket-level permissions granted to $BACKEND_SA"
}

create_service_accounts() {
    print_header "Creating Service Accounts"
    
    BACKEND_SA="karma-backend@$PROJECT_ID.iam.gserviceaccount.com"
    
    # Create backend service account
    if ! gcloud iam service-accounts describe karma-backend --project=$PROJECT_ID &>/dev/null; then
        gcloud iam service-accounts create karma-backend \
            --display-name="Karma Backend Service Account" \
            --project=$PROJECT_ID
        print_success "Service account created: karma-backend"
    else
        print_warning "Service account karma-backend already exists"
    fi
    
    # Grant Cloud SQL permission (project-level, needed for database access)
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$BACKEND_SA" \
        --role="roles/cloudsql.client" \
        --condition=None
    
    # Grant bucket-level storage permissions (least privilege - only for this bucket)
    # Note: Bucket must exist before granting permissions
    if gsutil ls -b gs://$GCS_BUCKET &>/dev/null; then
        print_warning "Granting bucket-level permissions to gs://$GCS_BUCKET..."
        
        # Grant storage.buckets.get (to check if bucket exists)
        gsutil iam ch serviceAccount:${BACKEND_SA}:roles/storage.legacyBucketReader gs://$GCS_BUCKET
        
        # Grant storage.objects.* (to read/write objects in the bucket)
        gsutil iam ch serviceAccount:${BACKEND_SA}:roles/storage.objectAdmin gs://$GCS_BUCKET
        
        print_success "Bucket-level permissions granted"
    else
        print_warning "Bucket gs://$GCS_BUCKET does not exist yet. Permissions will be granted when bucket is created."
    fi
    
    print_success "Permissions granted to service account"
}

build_and_push_images() {
    print_header "Building and Pushing Docker Images"
    
    # Get project number and service accounts for debugging
    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
    CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
    
    print_warning "Cloud Build will use service account: ${CLOUD_BUILD_SA}"
    print_warning "Verifying permissions..."
    
    # Check if artifactregistry.admin is granted
    if ! gcloud projects get-iam-policy $PROJECT_ID \
        --flatten="bindings[].members" \
        --filter="bindings.members:serviceAccount:${CLOUD_BUILD_SA} AND bindings.role:roles/artifactregistry.admin" \
        --format="value(bindings.role)" 2>&1 | grep -q "artifactregistry.admin"; then
        print_warning "⚠️  artifactregistry.admin not found! Granting now..."
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member="serviceAccount:${CLOUD_BUILD_SA}" \
            --role="roles/artifactregistry.admin" \
            --quiet
        print_warning "Waiting 10 seconds for permissions to propagate..."
        sleep 10
    fi
    
    # Build backend
    print_warning "Building backend image..."
    gcloud builds submit --tag gcr.io/$PROJECT_ID/$BACKEND_SERVICE ./backend
    
    print_success "Backend image built and pushed"
    
    # Get backend URL for frontend build (needed for VITE_API_URL)
    BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE --region $REGION --format 'value(status.url)' --project=$PROJECT_ID 2>/dev/null || echo "")
    
    # Build frontend with backend URL as build arg
    print_warning "Building frontend image..."
    if [ -n "$BACKEND_URL" ]; then
        print_warning "Using backend URL: $BACKEND_URL/api"
        # Create a cloudbuild.yaml file to pass build args
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
        gcloud builds submit \
            --config=/tmp/frontend-cloudbuild.yaml \
            ./frontend
        rm -f /tmp/frontend-cloudbuild.yaml
    else
        print_warning "Backend URL not found. Building frontend with default /api"
        print_warning "⚠️  Frontend will need to be rebuilt after backend is deployed to get correct API URL"
        gcloud builds submit --tag gcr.io/$PROJECT_ID/$FRONTEND_SERVICE ./frontend
    fi
    
    print_success "Frontend image built and pushed"
}

deploy_backend() {
    print_header "Deploying Backend Service"
    
    CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE --format='value(connectionName)' --project=$PROJECT_ID)
    BACKEND_SA="karma-backend@$PROJECT_ID.iam.gserviceaccount.com"
    
    # Get frontend URL if it exists (for CORS)
    FRONTEND_URL=$(gcloud run services describe $FRONTEND_SERVICE --region $REGION --format 'value(status.url)' --project=$PROJECT_ID 2>/dev/null || echo "")
    if [ -n "$FRONTEND_URL" ]; then
        print_success "Frontend URL found: $FRONTEND_URL (will be used for CORS)"
    else
        print_warning "Frontend not found yet. CORS will use default localhost origins."
        print_warning "Update FRONTEND_URL after frontend is deployed, or it will be set automatically on next deployment."
    fi
    
    # Build env vars
    ENV_VARS="USE_CLOUD_STORAGE=true,GCS_BUCKET_NAME=$GCS_BUCKET,CLOUD_SQL_CONNECTION_NAME=$CONNECTION_NAME,DATABASE_USER=$DB_USER,DATABASE_NAME=$DB_NAME,OPENAI_KARMA=$ENABLE_AI"
    if [ -n "$FRONTEND_URL" ]; then
        ENV_VARS="$ENV_VARS,FRONTEND_URL=$FRONTEND_URL"
    fi
    
    # Add admin configuration if provided
    if [ -n "$ADMIN_USER_IDS" ]; then
        ENV_VARS="$ENV_VARS,ADMIN_USER_IDS=$ADMIN_USER_IDS"
    fi
    if [ -n "$ADMIN_EMAILS" ]; then
        ENV_VARS="$ENV_VARS,ADMIN_EMAILS=$ADMIN_EMAILS"
    fi
    
    # Add token limit configuration if provided (defaults to 1M in code)
    if [ -n "$DEFAULT_MONTHLY_TOKEN_LIMIT" ]; then
        ENV_VARS="$ENV_VARS,DEFAULT_MONTHLY_TOKEN_LIMIT=$DEFAULT_MONTHLY_TOKEN_LIMIT"
    fi
    
    # Deploy with appropriate settings
    # Use secret for database password if it exists
    SECRET_NAME="database-password"
    if gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID &>/dev/null; then
        print_warning "Using Secret Manager for DATABASE_PASSWORD"
        gcloud run deploy $BACKEND_SERVICE \
            --image gcr.io/$PROJECT_ID/$BACKEND_SERVICE \
            --platform managed \
            --region $REGION \
            --allow-unauthenticated \
            --service-account $BACKEND_SA \
            --add-cloudsql-instances $CONNECTION_NAME \
            --update-secrets "DATABASE_PASSWORD=${SECRET_NAME}:latest" \
            --set-env-vars "$ENV_VARS" \
            --memory 1Gi \
            --cpu 1 \
            --timeout 300 \
            --max-instances 10 \
            --min-instances 0 \
            --project=$PROJECT_ID
    else
        print_warning "Secret $SECRET_NAME not found. Deploying without DATABASE_PASSWORD."
        print_warning "You'll need to set it manually or run: ./scripts/deploy/create_database_secret.sh"
        gcloud run deploy $BACKEND_SERVICE \
            --image gcr.io/$PROJECT_ID/$BACKEND_SERVICE \
            --platform managed \
            --region $REGION \
            --allow-unauthenticated \
            --service-account $BACKEND_SA \
            --add-cloudsql-instances $CONNECTION_NAME \
            --set-env-vars "$ENV_VARS" \
            --memory 1Gi \
            --cpu 1 \
            --timeout 300 \
            --max-instances 10 \
            --min-instances 0 \
            --project=$PROJECT_ID
    fi
    
    BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE --region $REGION --format 'value(status.url)' --project=$PROJECT_ID)
    print_success "Backend deployed: $BACKEND_URL"
    
    if [ "$ENABLE_AI" = "true" ]; then
        echo "⚠️  Remember to set these secrets:"
        echo "  - OPENAI_API_KEY (required for AI mode)"
        echo "  - DATABASE_PASSWORD"
        echo "  - CLERK_SECRET_KEY (if using)"
        echo ""
        echo "Optional environment variables (can be set later):"
        echo "  - ADMIN_USER_IDS (comma-separated user IDs for admin access)"
        echo "  - ADMIN_EMAILS (comma-separated emails for admin access)"
        echo "  - DEFAULT_MONTHLY_TOKEN_LIMIT (default: 1000000)"
        echo ""
        echo "Use: gcloud run services update $BACKEND_SERVICE --update-secrets ..."
        echo "Or: gcloud run services update $BACKEND_SERVICE --update-env-vars ADMIN_USER_IDS=user1,user2 ..."
    else
        echo "ℹ️  Deployed in DUMMY MODE (AI disabled)"
        echo "⚠️  Remember to set these secrets:"
        echo "  - DATABASE_PASSWORD"
        echo "  - CLERK_SECRET_KEY (if using)"
        echo ""
        echo "Optional environment variables (can be set later):"
        echo "  - ADMIN_USER_IDS (comma-separated user IDs for admin access)"
        echo "  - ADMIN_EMAILS (comma-separated emails for admin access)"
        echo "  - DEFAULT_MONTHLY_TOKEN_LIMIT (default: 1000000)"
        echo ""
        echo "Use: gcloud run services update $BACKEND_SERVICE --update-secrets ..."
        echo "Or: gcloud run services update $BACKEND_SERVICE --update-env-vars ADMIN_USER_IDS=user1,user2 ..."
    fi
}

deploy_frontend() {
    print_header "Deploying Frontend Service"
    
    # Get backend URL
    BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE --region $REGION --format 'value(status.url)' --project=$PROJECT_ID)
    
    if [ -z "$BACKEND_URL" ]; then
        print_error "Backend URL not found. Deploy backend first."
        exit 1
    fi
    
    gcloud run deploy $FRONTEND_SERVICE \
        --image gcr.io/$PROJECT_ID/$FRONTEND_SERVICE \
        --platform managed \
        --region $REGION \
        --allow-unauthenticated \
        --set-env-vars "VITE_API_URL=$BACKEND_URL/api" \
        --memory 512Mi \
        --cpu 1 \
        --timeout 60 \
        --max-instances 5 \
        --min-instances 0 \
        --project=$PROJECT_ID
    
    FRONTEND_URL=$(gcloud run services describe $FRONTEND_SERVICE --region $REGION --format 'value(status.url)' --project=$PROJECT_ID)
    print_success "Frontend deployed: $FRONTEND_URL"
    
    # Update backend with frontend URL for CORS
    echo ""
    echo "Updating backend CORS configuration with frontend URL..."
    gcloud run services update $BACKEND_SERVICE \
        --region $REGION \
        --update-env-vars "FRONTEND_URL=$FRONTEND_URL" \
        --project=$PROJECT_ID 2>/dev/null && \
        print_success "Backend CORS updated with frontend URL" || \
        print_warning "Could not update backend CORS (backend may not exist yet)"
}

# Main menu
main() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════╗"
    echo "║   Karma GCP Deployment Script        ║"
    echo "╚══════════════════════════════════════╝"
    echo -e "${NC}"
    
    check_prerequisites
    
    echo ""
    # Ask about AI mode
    echo "AI Mode Configuration:"
    echo "  Current setting: ENABLE_AI=$ENABLE_AI"
    echo "  - 'true' = Real AI (requires OPENAI_API_KEY)"
    echo "  - 'false' = Dummy mode (no AI, faster, cheaper)"
    echo ""
    read -p "Enable AI? [y/N]: " enable_ai_choice
    if [[ $enable_ai_choice =~ ^[Yy]$ ]]; then
        ENABLE_AI="true"
        print_warning "AI mode enabled - you'll need to set OPENAI_API_KEY secret"
    else
        ENABLE_AI="false"
        print_success "Dummy mode (AI disabled) - no OpenAI key needed"
    fi
    echo ""
    
    # Ask about admin configuration (optional)
    echo "Admin Configuration (optional - can be set later):"
    echo "  You can configure admin access via environment variables:"
    echo "  - ADMIN_USER_IDS: Comma-separated list of Clerk user IDs"
    echo "  - ADMIN_EMAILS: Comma-separated list of email addresses"
    echo ""
    read -p "Set admin configuration now? [y/N]: " admin_choice
    if [[ $admin_choice =~ ^[Yy]$ ]]; then
        read -p "Enter admin user IDs (comma-separated, or press Enter to skip): " ADMIN_USER_IDS
        read -p "Enter admin emails (comma-separated, or press Enter to skip): " ADMIN_EMAILS
        if [ -n "$ADMIN_USER_IDS" ]; then
            print_success "Admin user IDs configured"
        fi
        if [ -n "$ADMIN_EMAILS" ]; then
            print_success "Admin emails configured"
        fi
    else
        print_warning "Skipping admin configuration. You can set it later with:"
        echo "  gcloud run services update $BACKEND_SERVICE --update-env-vars ADMIN_USER_IDS=user1,user2"
    fi
    echo ""
    echo "What would you like to do?"
    echo "1) Full deployment (all steps)"
    echo "2) Setup infrastructure only (Cloud SQL, Storage, Service Accounts)"
    echo "3) Build and deploy services only"
    echo "4) Deploy backend only"
    echo "5) Deploy frontend only"
    echo "6) Exit"
    echo ""
    read -p "Enter choice [1-6]: " choice
    
    case $choice in
        1)
            enable_apis
            setup_cloud_build_permissions
            create_cloud_sql
            create_cloud_storage
            create_service_accounts
            build_and_push_images
            deploy_backend
            deploy_frontend
            print_success "Full deployment complete!"
            ;;
        2)
            enable_apis
            setup_cloud_build_permissions
            create_cloud_sql
            create_cloud_storage
            create_service_accounts
            print_success "Infrastructure setup complete!"
            ;;
        3)
            setup_cloud_build_permissions
            build_and_push_images
            deploy_backend
            deploy_frontend
            print_success "Services deployed!"
            ;;
        4)
            setup_cloud_build_permissions
            build_and_push_images
            deploy_backend
            ;;
        5)
            setup_cloud_build_permissions
            build_and_push_images
            deploy_frontend
            ;;
        6)
            exit 0
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac
}

# Run main
main
