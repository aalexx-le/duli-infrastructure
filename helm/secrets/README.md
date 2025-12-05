# Infrastructure Secrets - Sealed Secrets Setup

This directory contains Sealed Secret templates for infrastructure services.

## Prerequisites

1. Sealed Secrets controller must be installed in the cluster
2. `kubeseal` CLI tool must be installed locally

## Creating Sealed Secrets

### Redis Credentials

1. **Get the sealed secret value:**
   ```bash
   # Replace 'your-redis-password' with your actual password
   echo -n "your-redis-password" | kubeseal --raw \
     --from-file=/dev/stdin \
     --namespace=staging \
     --name=redis-credentials \
     --controller-name=sealed-secrets-controller \
     --controller-namespace=sealed-secrets
   ```

2. **Update `values-staging.yaml`:**
   ```yaml
   namespace: staging
   redis:
     enabled: true
     password: "AgB..." # Paste the output from step 1
   ```

3. **Deploy via ArgoCD:**
   The `infrastructure-secrets-staging` ArgoCD application will automatically sync and create the secret.

## Manual Secret Creation (Alternative)

If you prefer to create the secret manually:

```bash
kubectl create secret generic redis-credentials \
  --from-literal=password='your-redis-password' \
  --namespace=staging \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > redis-sealed-secret.yaml

kubectl apply -f redis-sealed-secret.yaml
```

## Verification

Check if the secret was created:
```bash
kubectl get secret redis-credentials -n staging
```

Check if the Sealed Secret exists:
```bash
kubectl get sealedsecret redis-credentials -n staging
```

## Security Notes

- **Never commit unencrypted secrets to Git**
- The `helm/secrets/values-*.yaml` files contain **encrypted** values only
- Keep your `vault.yml` file encrypted with Ansible Vault
- The Sealed Secrets controller's private key should be backed up securely
