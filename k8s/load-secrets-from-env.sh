#!/bin/bash
# DEPRECATED: This script is no longer used. Secrets are loaded directly via make targets.
# Use: make kind-load-secrets or make eks-load-secrets
#
# Script to load secrets from .env file into Kubernetes secrets.yaml format
# Usage: ./load-secrets-from-env.sh [.env-file] [output-file]

set -e

ENV_FILE=${1:-.env}
OUTPUT_FILE=${2:-secrets.yaml}

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: .env file not found: $ENV_FILE"
    echo "   Create it from env.example: cp env.example .env"
    exit 1
fi

echo "📦 Loading secrets from $ENV_FILE to $OUTPUT_FILE..."

# Create output file with header
cat > "$OUTPUT_FILE" << 'EOF'
# IdeaForge AI - Secrets (Auto-generated from .env file)
# DO NOT commit this file to git
# Generated from: .env

EOF

# Read .env file and extract secret values
while IFS='=' read -r key value || [ -n "$key" ]; do
    # Skip empty lines and comments
    [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
    
    # Remove leading/trailing whitespace
    key=$(echo "$key" | xargs)
    value=$(echo "$value" | xargs)
    
    # Remove quotes if present
    value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
    
    # Only include secret keys
    case "$key" in
        POSTGRES_PASSWORD|SESSION_SECRET|API_KEY_ENCRYPTION_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|GOOGLE_API_KEY|V0_API_KEY|LOVABLE_API_KEY|GITHUB_TOKEN|GITHUB_ORG|ATLASSIAN_EMAIL|ATLASSIAN_API_TOKEN|JIRA_URL|JIRA_EMAIL|JIRA_API_TOKEN|CONFLUENCE_URL|CONFLUENCE_EMAIL|CONFLUENCE_API_TOKEN|OKTA_CLIENT_ID|OKTA_CLIENT_SECRET|OKTA_ISSUER)
            echo "$key: \"$value\"" >> "$OUTPUT_FILE"
            ;;
    esac
done < "$ENV_FILE"

echo "✅ Secrets loaded to $OUTPUT_FILE"
echo ""
echo "⚠️  Next steps:"
echo "   1. Review $OUTPUT_FILE"
echo "   2. Copy to k8s/overlays/kind/secrets.yaml or k8s/overlays/eks/secrets.yaml"
echo "   3. DO NOT commit secrets.yaml to git"

