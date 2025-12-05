# Infrastructure Sealed Secrets

This Helm chart contains Sealed Secrets for infrastructure services.

## Structure

```
helm/secrets/
├── Chart.yaml
└── templates/
    ├── redis-sealed-secret-staging.yaml
    ├── postgres-sealed-secret-staging.yaml
    ├── rabbitmq-sealed-secret-staging.yaml
    ├── redis-sealed-secret-prod.yaml
    ├── postgres-sealed-secret-prod.yaml
    └── rabbitmq-sealed-secret-prod.yaml
```

## Generating Sealed Secrets

Sealed secrets are generated using Ansible playbook:

```bash
ansible-playbook ansible/playbooks/generate_sealed_secrets.yml \
  -i ansible/inventories/hosts.ini \
  -e target_environment=staging \
  --ask-vault-pass
```

This will:
1. Read passwords from `ansible/inventories/group_vars/all/vault.yml`
2. Generate Sealed Secrets using `kubeseal`
3. Save to `helm/secrets/templates/`

## Deployment

ArgoCD automatically deploys these secrets via the `infrastructure-secrets-{environment}` application.

## Security

- Sealed Secrets are encrypted and safe to commit to Git
- Only the Sealed Secrets controller in the cluster can decrypt them
- Never commit unencrypted secrets to Git
