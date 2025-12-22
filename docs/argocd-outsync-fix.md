# ArgoCD OutOfSync Fix - Documentation

## Problem Summary

ArgoCD applications were showing **OutOfSync** status even though all Kubernetes resources were healthy and running correctly. This was caused by two issues:

### Issue 1: Duplicate ArgoCD Applications Managing Shared Resources

**Root Cause:**
Both `prod` and `staging` environments were deploying ArgoCD applications for shared resources that exist only once in the cluster:

- **keycloak-db**: Single database cluster in `keycloak-system` namespace shared by both `keycloak-instance-prod` and `keycloak-instance-staging`
- **infrastructure-secrets**: SealedSecrets in `keycloak-system` namespace used by both environments

This caused:
- ArgoCD warning: `SharedResourceWarning`
- Applications fighting over ownership of the same resources
- Constant sync loops (Synced → OutOfSync → Synced...)

**Affected Applications:**
- `keycloak-db-prod` / `keycloak-db-staging`
- `infrastructure-secrets-prod` / `infrastructure-secrets-staging`

### Issue 2: Operator Field Normalization Not Ignored

**Root Cause:**
Kubernetes operators (CNPG, RabbitMQ, Keycloak) add default fields and normalize user-provided specs:

**CNPG Operator (PostgreSQL):**
- Adds: `enablePDB`, `maxSyncReplicas`, `monitoring`, `postgresGID`, etc.
- Changes generation on every reconciliation

**RabbitMQ Operator:**
- Normalizes: `persistence.size` → `persistence.storage`
- Adds: `override`, `delayStartSeconds`, `affinity` defaults

**Keycloak Operator:**
- Adds status conditions and observed generation

ArgoCD detected these as drift without proper `ignoreDifferences` configuration.

---

## Solution

### Solution 1: Remove Duplicate Applications (Immediate Fix)

**Manual Commands:**
```bash
# Execute the fix script
./fix-argocd-sync.sh

# Or manually:
kubectl delete application keycloak-db-prod -n argocd
kubectl delete application infrastructure-secrets-prod -n argocd
```

**Result:**
- Only `*-staging` apps manage shared resources
- No more SharedResourceWarning
- Both prod and staging Keycloak instances use the same shared database

### Solution 2: Update Ansible Playbook (Permanent Fix)

**Changes Made to `ansible/playbooks/deploy_applications.yml`:**

1. **Split application deployment into two tasks:**
   - **Shared applications** (staging only): `infrastructure-secrets`, `keycloak-db`
   - **Environment-specific applications**: `postgresql-instance`, `rabbitmq-instance`, `redis-instance`, `keycloak-instance`, `backend`, `ai-service`, `scheduler`

2. **Conditional deployment:**
   ```yaml
   when: current_environment == 'staging'
   ```
   Ensures shared apps are only created when deploying staging.

**Usage:**
```bash
# Deploy staging (creates shared + staging-specific apps)
ansible-playbook -i inventories/hosts.ini playbooks/deploy_applications.yml -e target_environment=staging

# Deploy prod (creates only prod-specific apps)
ansible-playbook -i inventories/hosts.ini playbooks/deploy_applications.yml -e target_environment=prod
```

### Solution 3: Add ignoreDifferences for Operator-Managed Fields

**Changes Made to ArgoCD Application Templates:**

#### `gitops/applications/keycloak-db.yml.j2`
```yaml
ignoreDifferences:
  - group: postgresql.cnpg.io
    kind: Cluster
    jsonPointers:
      - /status
      - /metadata/generation
      - /metadata/resourceVersion
```

#### `gitops/applications/rabbitmq-instance.yml.j2`
```yaml
ignoreDifferences:
  - group: rabbitmq.com
    kind: RabbitmqCluster
    jsonPointers:
      - /status
      - /metadata/generation
      - /metadata/resourceVersion
      - /spec/persistence
      - /spec/override
      - /spec/delayStartSeconds
      - /spec/affinity
```

#### `gitops/applications/keycloak-instance.yml.j2`
```yaml
ignoreDifferences:
  - group: k8s.keycloak.org
    kind: Keycloak
    jsonPointers:
      - /status
      - /metadata/generation
      - /metadata/resourceVersion
  - group: k8s.keycloak.org
    kind: KeycloakRealmImport
    jsonPointers:
      - /status
```

#### `gitops/applications/infrastructure-secrets.yml.j2`
```yaml
ignoreDifferences:
  - group: bitnami.com
    kind: SealedSecret
    jsonPointers:
      - /status
```

---

## Architecture After Fix

### Shared Resources (Managed by `*-staging` apps)
- **keycloak-db-staging**: Manages `keycloak-db` Cluster in `keycloak-system`
  - Used by: `keycloak-instance-prod`, `keycloak-instance-staging`
- **infrastructure-secrets-staging**: Manages all SealedSecrets
  - `keycloak-system` namespace: `keycloak-db-credentials`, `keycloak-oauth-credentials`, `keycloak-backend-service`
  - `prod` namespace: `postgres-credentials`, `redis-credentials`
  - `staging` namespace: `postgres-credentials`, `redis-credentials`

### Environment-Specific Resources
| Resource | Prod | Staging |
|----------|------|---------|
| PostgreSQL | `database` in `prod` | `database` in `staging` |
| Redis | `redis-replication` in `prod` | `redis-replication` in `staging` |
| RabbitMQ | `queue` in `prod` | `queue` in `staging` |
| Keycloak | `keycloak-instance-prod` in `keycloak-system` | `keycloak-instance-staging` in `keycloak-system` |
| Backend | `backend` in `prod` | `backend` in `staging` |
| AI-Service | `ai-service` in `prod` | `ai-service` in `staging` |
| Scheduler | `scheduler` in `prod` | `scheduler` in `staging` |

---

## Verification

### Check ArgoCD Application Status
```bash
kubectl get applications -n argocd -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status
```

**Expected Output:**
```
NAME                             SYNC      HEALTH
infrastructure-secrets-staging   Synced    Healthy
keycloak-db-staging              Synced    Healthy
keycloak-instance-prod           Synced    Healthy
keycloak-instance-staging        Synced    Healthy
postgresql-instance-prod         Synced    Healthy
postgresql-instance-staging      Synced    Healthy
rabbitmq-instance-prod           Synced    Healthy
rabbitmq-instance-staging        Synced    Healthy
redis-instance-prod              Synced    Healthy
redis-instance-staging           Synced    Healthy
backend-prod                     Unknown   Healthy
backend-staging                  Unknown   Healthy
ai-service-prod                  Unknown   Healthy
ai-service-staging               Unknown   Healthy
scheduler-prod                   Unknown   Healthy
scheduler-staging                Unknown   Healthy
```

**Note:** `Unknown` sync status for backend/ai-service/scheduler is normal if they use external image repositories.

### Check for SharedResourceWarning
```bash
kubectl get applications -n argocd -o yaml | grep -A 2 "SharedResourceWarning"
```

**Expected:** No output (no warnings)

### Verify Keycloak Database Sharing
```bash
# Check that only one keycloak-db Cluster exists
kubectl get clusters.postgresql.cnpg.io -n keycloak-system

# Check that both Keycloak instances connect to it
kubectl get keycloak -n keycloak-system -o yaml | grep "host:"
```

**Expected:**
```
NAME          AGE   INSTANCES   READY   STATUS
keycloak-db   ...   1           1       Cluster in healthy state
```

---

## Rollback Plan

If issues occur after applying the fix:

### 1. Restore Duplicate Applications
```bash
# Re-run Ansible for prod (will recreate keycloak-db-prod)
cd ansible
ansible-playbook -i inventories/hosts.ini playbooks/deploy_applications.yml -e target_environment=prod
```

### 2. Revert Ansible Playbook
```bash
cd infrastructure-kubernetes
git revert <commit-hash>
git push
```

### 3. Manual Recreation
```bash
# If needed, manually create the prod apps
kubectl apply -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: keycloak-db-prod
  namespace: argocd
spec:
  # ... (copy from staging app, change target_env to prod)
EOF
```

---

## Future Improvements

1. **Separate Keycloak Databases**: If prod and staging should have isolated data, create separate keycloak-db clusters:
   - `keycloak-db-prod` in dedicated namespace
   - `keycloak-db-staging` in dedicated namespace

2. **Use ArgoCD ApplicationSets**: Manage environment-specific apps with ApplicationSets instead of Ansible loops

3. **Add Prometheus Alerts**: Alert on `SharedResourceWarning` conditions

4. **Document Shared Resources**: Add to AGENTS.md which resources are shared vs environment-specific

---

## References

- ArgoCD ignoreDifferences: https://argo-cd.readthedocs.io/en/stable/user-guide/diffing/
- ArgoCD Resource Tracking: https://argo-cd.readthedocs.io/en/stable/user-guide/resource_tracking/
- CNPG Operator: https://cloudnative-pg.io/
- RabbitMQ Operator: https://www.rabbitmq.com/kubernetes/operator/operator-overview.html
- Keycloak Operator: https://www.keycloak.org/operator/advanced-configuration
