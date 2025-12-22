#!/bin/bash
# Manual fix script for ArgoCD OutOfSync issues
# Run this to immediately resolve shared resource conflicts

set -e

echo "=== ArgoCD OutOfSync Manual Fix ==="
echo ""

# 1. Delete duplicate ArgoCD applications managing shared resources
echo "Step 1: Removing duplicate ArgoCD apps for shared resources..."
kubectl delete application keycloak-db-prod -n argocd --ignore-not-found=true
kubectl delete application infrastructure-secrets-prod -n argocd --ignore-not-found=true
echo "✓ Duplicate apps removed"
echo ""

# 2. Verify RabbitMQ has correct ignoreDifferences
echo "Step 2: Checking RabbitMQ ignoreDifferences configuration..."
kubectl get application rabbitmq-instance-prod -n argocd -o yaml | grep -A 10 "ignoreDifferences:" || echo "⚠ ignoreDifferences not found"
kubectl get application rabbitmq-instance-staging -n argocd -o yaml | grep -A 10 "ignoreDifferences:" || echo "⚠ ignoreDifferences not found"
echo ""

# 3. Force refresh ArgoCD applications
echo "Step 3: Forcing ArgoCD to refresh application status..."
kubectl patch application rabbitmq-instance-prod -n argocd --type merge -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"hard"}}}'
kubectl patch application rabbitmq-instance-staging -n argocd --type merge -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"hard"}}}'
kubectl patch application keycloak-instance-prod -n argocd --type merge -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"hard"}}}'
kubectl patch application keycloak-instance-staging -n argocd --type merge -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"hard"}}}'
echo "✓ Applications refreshed"
echo ""

# 4. Wait for sync
echo "Step 4: Waiting 30 seconds for ArgoCD to reconcile..."
sleep 30
echo ""

# 5. Check final status
echo "Step 5: Final status check..."
echo ""
kubectl get applications -n argocd -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status | grep -E "(NAME|prod|staging)"
echo ""
echo "=== Fix Complete ==="
echo ""
echo "Expected result:"
echo "  - keycloak-db-staging: Synced (manages shared keycloak-db)"
echo "  - infrastructure-secrets-staging: Synced (manages all secrets)"
echo "  - rabbitmq-instance-*: Synced (with ignoreDifferences)"
echo "  - keycloak-instance-*: Synced (with ignoreDifferences)"
