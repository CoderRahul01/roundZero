#!/usr/bin/env bash
# =============================================================================
# setup_secrets.sh — One-time script to push RoundZero secrets to GCP Secret Manager
#
# Usage:
#   cd backend
#   bash scripts/setup_secrets.sh <GCP_PROJECT_ID>
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (gcloud auth login)
#   - backend/.env file filled in with real values
#   - Cloud Build / Cloud Run APIs enabled on the project
#
# What it does:
#   1. Enables the Secret Manager API
#   2. Creates (or updates) each secret from your local .env
#   3. Creates a dedicated service account for Cloud Run
#   4. Grants that SA secretAccessor on all created secrets
#
# After running, deploy with: gcloud builds submit --config cloudbuild.yaml
# =============================================================================

set -euo pipefail

PROJECT_ID="${1:-}"
if [[ -z "$PROJECT_ID" ]]; then
  echo "ERROR: Pass your GCP project ID as the first argument."
  echo "  Usage: bash scripts/setup_secrets.sh my-gcp-project-id"
  exit 1
fi

ENV_FILE="$(dirname "$0")/../.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: backend/.env not found. Copy .env.example and fill in real values first."
  exit 1
fi

SA_NAME="roundzero-cloudrun"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=== Project: $PROJECT_ID ==="
gcloud config set project "$PROJECT_ID"

# 1. Enable required APIs
echo "--- Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com --project="$PROJECT_ID"

# 2. Create or update secrets from .env
# Only the truly sensitive values go into Secret Manager.
# Non-secret config (ENVIRONMENT, LOG_LEVEL, etc.) stays as plain --set-env-vars.
SECRETS=(
  GOOGLE_API_KEY
  DATABASE_URL
  JWT_SECRET
  PINECONE_API_KEY
  UPSTASH_REDIS_REST_URL
  UPSTASH_REDIS_REST_TOKEN
  SUPERMEMORY_API_KEY
  ANTHROPIC_API_KEY
  NEON_AUTH_JWKS_URL
  NEON_AUTH_ISSUER
  NEON_AUTH_AUDIENCE
)

echo "--- Creating/updating secrets in Secret Manager..."
for SECRET_NAME in "${SECRETS[@]}"; do
  # Extract value from .env (handles quoted and unquoted values)
  VALUE=$(grep -E "^${SECRET_NAME}=" "$ENV_FILE" | head -1 | sed 's/^[^=]*=//' | tr -d '"'"'" | tr -d '\r')

  if [[ -z "$VALUE" || "$VALUE" == your-* || "$VALUE" == sk-ant-api03-your* ]]; then
    echo "  SKIP: $SECRET_NAME (not set or still a placeholder)"
    continue
  fi

  # Create the secret if it doesn't exist, then add a new version
  if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" &>/dev/null; then
    echo "  UPDATE: $SECRET_NAME"
    echo -n "$VALUE" | gcloud secrets versions add "$SECRET_NAME" --data-file=- --project="$PROJECT_ID"
  else
    echo "  CREATE: $SECRET_NAME"
    echo -n "$VALUE" | gcloud secrets create "$SECRET_NAME" \
      --data-file=- \
      --replication-policy=automatic \
      --project="$PROJECT_ID"
  fi
done

# 3. Create dedicated service account for Cloud Run (if not already exists)
echo "--- Setting up Cloud Run service account: $SA_EMAIL"
if ! gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name="RoundZero Cloud Run SA" \
    --project="$PROJECT_ID"
  echo "  Created: $SA_EMAIL"
  echo "  Waiting 20s for IAM propagation..."
  sleep 20
else
  echo "  Already exists: $SA_EMAIL"
fi

# 4. Grant the SA access to read all secrets
echo "--- Granting secretAccessor to $SA_EMAIL..."
for SECRET_NAME in "${SECRETS[@]}"; do
  if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" &>/dev/null; then
    gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
      --member="serviceAccount:${SA_EMAIL}" \
      --role="roles/secretmanager.secretAccessor" \
      --project="$PROJECT_ID" \
      --quiet
  fi
done

# 5. Grant Cloud Build SA permission to deploy with the Cloud Run SA
CLOUDBUILD_SA="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')@cloudbuild.gserviceaccount.com"
echo "--- Granting Cloud Build SA ($CLOUDBUILD_SA) the ability to act as Cloud Run SA..."
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --member="serviceAccount:${CLOUDBUILD_SA}" \
  --role="roles/iam.serviceAccountUser" \
  --project="$PROJECT_ID" \
  --quiet

echo ""
echo "=== Done! ==="
echo "Next: gcloud builds submit --config cloudbuild.yaml --project=$PROJECT_ID"
echo "      (or trigger via Cloud Build GitHub integration)"
