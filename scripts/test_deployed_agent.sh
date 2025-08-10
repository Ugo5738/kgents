#!/bin/bash

# Script to test deployed agents on Cloud Run
# Usage: ./test_deployed_agent.sh [SERVICE_NAME or URL]

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 [SERVICE_NAME or URL]"
    echo ""
    echo "Examples:"
    echo "  $0 agent-runtime-f090cc96-2152-49a3-95fa-3b5a8ff0c9f9"
    echo "  $0 https://agent-runtime-xxx.run.app"
    echo ""
    echo "Available services:"
    gcloud run services list --platform managed --region=us-central1 --format="table(SERVICE:label='Service Name',URL)"
    exit 1
fi

INPUT="$1"

# Check if input is a URL or service name
if [[ "$INPUT" == http* ]]; then
    SERVICE_URL="$INPUT"
    SERVICE_NAME=$(echo "$INPUT" | sed -n 's|https://\([^-]*-[^-]*-[^-]*-[^-]*-[^-]*-[^-]*-[^-]*-[^-]*-[^-]*\).*|\1|p')
else
    SERVICE_NAME="$INPUT"
    # Get the service URL
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --platform managed \
        --region us-central1 \
        --format="value(status.url)" 2>/dev/null)
    
    if [ -z "$SERVICE_URL" ]; then
        echo "❌ Service '$SERVICE_NAME' not found in us-central1"
        exit 1
    fi
fi

echo "🔍 Testing agent: $SERVICE_NAME"
echo "📍 URL: $SERVICE_URL"
echo "=========================================="

# Test 1: Health Check
echo ""
echo "1️⃣ Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/health" 2>/dev/null || echo "000")
if [ "$HEALTH_RESPONSE" = "200" ]; then
    echo "✅ Health check passed"
    curl -s "$SERVICE_URL/health" | jq . 2>/dev/null || curl -s "$SERVICE_URL/health"
else
    echo "⚠️  Health check returned: $HEALTH_RESPONSE"
fi

# Test 2: API Documentation
echo ""
echo "2️⃣ Testing API documentation..."
DOCS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/docs" 2>/dev/null || echo "000")
if [ "$DOCS_RESPONSE" = "200" ]; then
    echo "✅ API docs available at: $SERVICE_URL/docs"
else
    echo "⚠️  API docs returned: $DOCS_RESPONSE"
fi

# Test 3: Langflow-specific endpoints (if applicable)
echo ""
echo "3️⃣ Testing Langflow endpoints..."
API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/api/v1/flows" 2>/dev/null || echo "000")
if [ "$API_RESPONSE" = "200" ] || [ "$API_RESPONSE" = "401" ]; then
    echo "✅ Langflow API endpoint responsive (status: $API_RESPONSE)"
else
    echo "ℹ️  Langflow API returned: $API_RESPONSE (might not be a Langflow agent)"
fi

# Test 4: Get recent logs
echo ""
echo "4️⃣ Recent logs from Cloud Run:"
echo "----------------------------------"
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=\"$SERVICE_NAME\" AND severity>=WARNING" \
    --limit 10 \
    --format="value(timestamp,severity,textPayload)" \
    --project=kgents \
    2>/dev/null | head -20 || echo "No recent warnings/errors found"

# Test 5: Service details
echo ""
echo "5️⃣ Service configuration:"
echo "----------------------------------"
gcloud run services describe "$SERVICE_NAME" \
    --platform managed \
    --region us-central1 \
    --format="yaml(spec.template.spec.containers[0].resources,status.conditions)" \
    2>/dev/null | grep -E "memory:|cpu:|type:|status:|message:" || echo "Could not retrieve service details"

echo ""
echo "=========================================="
echo "✨ Test complete!"
echo ""
echo "To interact with your agent:"
echo "  - Web UI: $SERVICE_URL"
echo "  - API Docs: $SERVICE_URL/docs"
echo "  - Logs: gcloud logging read 'resource.labels.service_name=\"$SERVICE_NAME\"' --limit 50"
echo ""
echo "To delete this agent:"
echo "  gcloud run services delete $SERVICE_NAME --region us-central1"
