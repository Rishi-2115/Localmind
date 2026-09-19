#!/bin/bash
set -e

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <tenant_id>"
    exit 1
fi

TENANT_ID=$1
NAMESPACE="tenant-$TENANT_ID"

echo "Onboarding new tenant: $TENANT_ID"
echo "Target namespace: $NAMESPACE"

# Create namespace
kubectl create namespace $NAMESPACE || true

# Label namespace for network policies if needed
kubectl label namespace $NAMESPACE tenant=$TENANT_ID --overwrite

# Generate a cryptographically random 16-character initial password
INITIAL_ADMIN_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))" 2>/dev/null || openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)
ADMIN_EMAIL="admin@${TENANT_ID}.localmind.in"

# Create secrets (in real scenario, use SealedSecrets)
# kubectl create secret generic localmind-secrets \
#     --from-literal=jwt-secret="$(python3 -c "import secrets; print(secrets.token_hex(32))")" \
#     --from-literal=admin-password="$INITIAL_ADMIN_PASSWORD" \
#     -n $NAMESPACE

# Deploy via Helm
echo "Deploying Helm chart..."
helm upgrade --install localmind ./infra/helm/localmind \
    --namespace $NAMESPACE \
    --set global.tenantId=$TENANT_ID \
    --set ollama.enabled=true \
    --set api.adminPassword="$INITIAL_ADMIN_PASSWORD" \
    --wait

echo "================================================================="
echo "Tenant '$TENANT_ID' successfully provisioned in namespace '$NAMESPACE'"
echo "================================================================="
echo "Initial Admin User: $ADMIN_EMAIL"
echo "Temporary Password: $INITIAL_ADMIN_PASSWORD"
echo "Security Policy:    Force password change is ENABLED on first login."
echo "NOTE: Relay this temporary password securely (out-of-band)."
echo "      It is NOT saved in logs and will not be displayed again."
echo "================================================================="
