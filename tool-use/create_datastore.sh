#!/usr/bin/env bash
set -euo pipefail

# Configuration
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || echo '')}"
LOCATION="${LOCATION:-global}"
DATA_STORE_ID="${DATA_STORE_ID:-sample-datastore}"
DISPLAY_NAME="${DISPLAY_NAME:-Sample Search Data Store}"
CONTENT_CONFIG="${CONTENT_CONFIG:-CONTENT_REQUIRED}" # CONTENT_REQUIRED, NO_CONTENT, PUBLIC_WEBSITE

if [ -z "$PROJECT_ID" ]; then
  echo "Error: PROJECT_ID is required. Set PROJECT_ID or configure 'gcloud config set project'." >&2
  exit 1
fi

if [ "$LOCATION" = "global" ]; then
  API_ENDPOINT="https://discoveryengine.googleapis.com"
else
  API_ENDPOINT="https://${LOCATION}-discoveryengine.googleapis.com"
fi

echo "==> Ensuring Discovery Engine API is enabled..."
gcloud services enable discoveryengine.googleapis.com --project="${PROJECT_ID}"

echo "==> Creating Vertex AI Search Data Store: ${DATA_STORE_ID} (${DISPLAY_NAME})..."
curl -s -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID}" \
  "${API_ENDPOINT}/v1/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores?dataStoreId=${DATA_STORE_ID}" \
  -d '{
    "displayName": "'"${DISPLAY_NAME}"'",
    "industryVertical": "GENERIC",
    "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
    "contentConfig": "'"${CONTENT_CONFIG}"'"
  }' | jq . || cat

echo ""
echo "==> Done. Verify status with:"
echo "curl -X GET -H \"Authorization: Bearer \$(gcloud auth print-access-token)\" -H \"X-Goog-User-Project: ${PROJECT_ID}\" \"${API_ENDPOINT}/v1/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores/${DATA_STORE_ID}\""
