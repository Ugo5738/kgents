#!/bin/bash
set -e

# GitHub Actions Setup Script for Free Docker Builds
# This script automates the setup of GitHub Actions with Google Cloud
# Works on macOS and Linux (even with old Bash versions)

echo "🚀 GitHub Actions Setup for Free Cross-Platform Docker Builds"
echo "============================================================"

# Check prerequisites
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI not found. Please install it first."
    exit 1
fi

# Get configuration
read -p "Enter your GCP Project ID: " GCP_PROJECT_ID
read -p "Enter your GitHub username: " GITHUB_USERNAME
read -p "Enter your GitHub repository name (default: kgents): " GITHUB_REPO
GITHUB_REPO=${GITHUB_REPO:-kgents}

# Lowercase GitHub username and repo (for OIDC match)
LOWER_GITHUB_USERNAME=$(echo "$GITHUB_USERNAME" | tr '[:upper:]' '[:lower:]')
LOWER_GITHUB_REPO=$(echo "$GITHUB_REPO" | tr '[:upper:]' '[:lower:]')

REPO_ATTRIBUTE="${LOWER_GITHUB_USERNAME}/${LOWER_GITHUB_REPO}"

# Set project
gcloud config set project "${GCP_PROJECT_ID}"

# Get project number
PROJECT_NUMBER=$(gcloud projects describe "${GCP_PROJECT_ID}" --format="value(projectNumber)")
echo "✅ Project Number: ${PROJECT_NUMBER}"

# Step 1: Create Service Account
echo ""
echo "📦 Step 1: Creating Service Account..."
gcloud iam service-accounts create github-actions \
    --display-name="GitHub Actions Builder" \
    --description="Service account for GitHub Actions to build and push Docker images" \
    2>/dev/null || echo "Service account already exists"

SERVICE_ACCOUNT="github-actions@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

# Step 2: Grant Permissions
echo ""
echo "🔐 Step 2: Granting Permissions..."
gcloud projects add-iam-policy-binding "${GCP_PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/artifactregistry.writer" \
    --quiet

# Step 3: Create Workload Identity Pool
echo ""
echo "🏊 Step 3: Creating Workload Identity Pool..."
gcloud iam workload-identity-pools create "github" \
    --location="global" \
    --display-name="GitHub Actions Pool" \
    --description="Workload Identity Pool for GitHub Actions" \
    2>/dev/null || echo "Pool already exists"

# Step 4: Create Workload Identity Provider
echo ""
echo "🔗 Step 4: Creating Workload Identity Provider..."
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
    --location="global" \
    --workload-identity-pool="github" \
    --display-name="GitHub Provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    2>/dev/null || echo "Provider already exists"

# Step 5: Get WIF Resource Names
WIF_PROVIDER="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/providers/github-provider"
WIF_POOL="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github"
echo "✅ WIF Provider: ${WIF_PROVIDER}"

# Step 6: Allow GitHub Actions to impersonate service account
echo ""
echo "🎭 Step 6: Configuring Workload Identity..."
gcloud iam service-accounts add-iam-policy-binding "${SERVICE_ACCOUNT}" \
    --member="principalSet://iam.googleapis.com/${WIF_POOL}/attribute.repository/${REPO_ATTRIBUTE}" \
    --role="roles/iam.workloadIdentityUser" \
    --quiet

# Step 7: Generate GitHub Secrets
echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "📝 Add these secrets to your GitHub repository:"
echo "   (Settings → Secrets and variables → Actions)"
echo ""
echo "WIF_PROVIDER:"
echo "${WIF_PROVIDER}"
echo ""
echo "WIF_SERVICE_ACCOUNT:"
echo "${SERVICE_ACCOUNT}"
echo ""
echo "=========================================="
echo ""
echo "🔑 Next Steps:"
echo "1. Go to: https://github.com/${GITHUB_USERNAME}/${GITHUB_REPO}/settings/secrets/actions"
echo "2. Add the two secrets shown above"
echo "3. Create a GitHub Personal Access Token:"
echo "   https://github.com/settings/tokens"
echo "4. Set environment variables:"
echo "   export BUILD_STRATEGY=github_actions"
echo "   export GITHUB_TOKEN=your_token"
echo "   export GITHUB_OWNER=${GITHUB_USERNAME}"
echo "   export GITHUB_REPO=${GITHUB_REPO}"
echo ""
echo "🎉 You're ready for FREE Docker builds!"