#!/bin/bash

# Script to delete failed Cloud Run services
# The X marks indicate failed services

echo "🧹 Cleaning up failed agent deployments..."

# List of failed services to delete
FAILED_SERVICES=(
    "agent-runtime-099b6f5f-d36c-4bd8-ab80-14f7ab0b439c"
    "agent-runtime-0b29fc53-a562-400b-b924-18103b9f3668"
    "agent-runtime-0bf80085-2193-4d2d-bf44-be77d107654c"
    "agent-runtime-453b47be-284e-49bd-8ef9-ab60271d7c2a"
    "agent-runtime-493da592-3181-430f-9569-b5b1d65a2c5f"
    "agent-runtime-54e2fa7a-d124-4f04-80bb-a8465647261e"
    "agent-runtime-6070d449-ae81-4535-9489-02aaf45519fa"
    "agent-runtime-71dbcd2e-fe62-4927-bfca-443deeeb3007"
    "agent-runtime-7910ca01-191b-4883-b035-30db1b1a8943"
    "agent-runtime-8071b745-24ec-4dd8-a123-9a555f63f7b1"
    "agent-runtime-8233094b-5ab8-4351-a7fa-2a1ce017ef43"
    "agent-runtime-a35098eb-e035-4d45-a5b7-f876572da7b3"
    "agent-runtime-a4fe4e7b-a1cb-4808-a8a1-34f1f4986487"
    "agent-runtime-a5b3317b-af26-4e06-a727-fde969598686"
    "agent-runtime-b5a47328-5eeb-487c-906f-9b9d2b813c09"
    "agent-runtime-b8bae803-323f-44d7-92d7-7a13dfdad1e3"
    "agent-runtime-d83897d6-366c-4c71-8a1c-4c20ed63ac52"
    "agent-runtime-f5125035-57ab-4e67-9bae-6e89f301d752"
)

# NOT deleting the working one:
# agent-runtime-f090cc96-2152-49a3-95fa-3b5a8ff0c9f9

REGION="us-central1"

for SERVICE in "${FAILED_SERVICES[@]}"; do
    echo "Deleting $SERVICE..."
    gcloud run services delete "$SERVICE" \
        --region="$REGION" \
        --quiet \
        2>/dev/null || echo "  ⚠️  Service $SERVICE not found or already deleted"
done

echo "✅ Cleanup complete!"
echo ""
echo "Remaining services:"
gcloud run services list --platform managed --region="$REGION" --format="table(SERVICE,URL:wrap)"
