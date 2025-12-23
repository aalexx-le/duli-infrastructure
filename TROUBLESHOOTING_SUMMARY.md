# Troubleshooting Summary - Staging Deployment Issues

Date: December 23, 2025

## Issues Found and Fixed

### 1. ✅ PostgreSQL Instance Not Created (FIXED)

**Root Cause:** Invalid YAML in `helm/postgres-instance/Chart.yaml` - line 2 had incorrect indentation

**Error Message:**
```
error converting YAML to JSON: yaml: line 2: mapping values are not allowed in this context
```

**Solution:**
- Fixed indentation in `Chart.yaml` (removed extra spaces before `name:`)
- Added missing sections to base `values.yaml`:
  - `postgresql.parameters: {}`
  - `storage.size` and `storage.storageClass`
  - `monitoring.enabled: false`

**Status:** ✅ FIXED - PostgreSQL cluster `database` now running in staging namespace

**Current State:**
```
NAME       AGE    INSTANCES   READY   STATUS                     PRIMARY
database   15m    1           1       Cluster in healthy state   database-1
```

---

### 2. ✅ Keycloak Instance Failing - Secret Name Mismatch (FIXED)

**Root Cause:** `keycloak-instance-staging` was referencing the wrong secret name

- **Expected secret name:** `keycloak-db-credentials` (sealed secret)
- **Actual reference in values-staging.yaml:** `keycloak-db-staging-credentials` (wrong!)

**Error Message:**
```
CreateContainerConfigError: secret "keycloak-db-staging-credentials" not found
```

**Solution:**
Changed `helm/keycloak-instance/values-staging.yaml` line 9:
```yaml
# BEFORE
secretName: keycloak-db-staging-credentials

# AFTER
secretName: keycloak-db-credentials
```

**Status:** ✅ FIXED - Keycloak pod is now initializing (checking logs shows successful startup)

**Current State:**
- Pod status: Running (initializing configuration)
- Database connection: ✅ Working
- Sealed secret: ✅ Found and decrypted
- Expected ready: 2-3 minutes (Keycloak needs to initialize)

---

### 3. ⚠️ RabbitMQ Instance - Out of Memory (NOT FIXED)

**Status:** RabbitMQ pod is crashing due to OOMKilled (Out of Memory)

**Error Details:**
```
Reason: OOMKilled
Exit Code: 137
Memory Limit: 128Mi
```

**Root Cause Analysis:**
- Memory limit (128Mi) is too small for RabbitMQ initialization
- RabbitMQ is rebuilding indices from scratch which consumes significant memory
- Pod is in `CrashLoopBackOff` with 10 restart attempts

**Recommendation:**
Increase memory limits in `helm/rabbitmq/values-staging.yaml`:
```yaml
# Current (too small)
limits:
  cpu: 150m
  memory: 128Mi
requests:
  cpu: 50m
  memory: 128Mi

# Recommended for staging
limits:
  cpu: 500m
  memory: 512Mi
requests:
  cpu: 100m
  memory: 256Mi
```

**Current Status:**
```
NAME    ALLREPLICASREADY   RECONCILESUCCESS   AGE
queue   False              False              40m
```

---

## Summary of Changes Made

### Files Modified:

1. **helm/postgres-instance/Chart.yaml**
   - Fixed indentation on line 2 (`name:` field)

2. **helm/postgres-instance/values.yaml**
   - Added `postgresql.parameters: {}`
   - Added `storage.size: 10Gi` and `storage.storageClass: do-block-storage`
   - Added `monitoring.enabled: false`

3. **helm/keycloak-instance/values-staging.yaml**
   - Changed `secretName: keycloak-db-staging-credentials` → `keycloak-db-credentials`

### Git Commits:
```
cde4a90 Fix: postgres-instance Chart.yaml indentation and keycloak-instance secret reference
```

---

## Current Deployment Status

### Staging Environment (ns: `staging`)

| Resource | Status | Health | Notes |
|----------|--------|--------|-------|
| PostgreSQL DB | ✅ Synced | ✅ Healthy | Cluster `database` running with 1 instance |
| Redis | ✅ Synced | ✅ Healthy | Master-replica setup running |
| RabbitMQ | ✅ Synced | ⚠️ Degraded | OOMKilled - needs memory increase |
| Backend | ❓ Unknown | ✅ Healthy | Waiting for dependencies |
| AI-Service | ❓ Unknown | ✅ Healthy | Waiting for dependencies |
| Scheduler | ❓ Unknown | ✅ Healthy | Waiting for dependencies |

### Keycloak (ns: `keycloak-system`)

| Resource | Status | Health | Notes |
|----------|--------|--------|-------|
| Keycloak DB | ✅ Synced | ✅ Healthy | Single instance PostgreSQL cluster |
| Keycloak Instance | ⚠️ OutOfSync | 🔄 Progressing | Pod initializing, should be ready soon |

---

## Next Steps

1. **Wait for Keycloak to finish initialization** (2-3 minutes)
   ```bash
   kubectl get pods -n keycloak-system keycloak-instance-staging-0 -w
   ```

2. **Fix RabbitMQ memory issue:**
   - Update `helm/rabbitmq/values-staging.yaml` with higher memory limits
   - Force ArgoCD refresh or run deploy playbook again

3. **Verify Redis instance (already working)**
   ```bash
   kubectl get redis -n staging
   ```

4. **After all infrastructure is ready, check application deployment:**
   ```bash
   kubectl get pods -n staging
   kubectl get application -n argocd -o wide | grep staging
   ```

---

## Key Learnings

1. **Helm chart YAML must be valid** - Invalid indentation in Chart.yaml breaks manifest generation
2. **Environment-specific values matter** - Sealed secret names must match exactly
3. **Resource sizing is important** - RabbitMQ needs adequate memory for initialization
4. **ArgoCD caching** - Force refresh may be needed: `kubectl patch application <app> -n argocd -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"hard"}}}'`

---

## Testing Commands

```bash
# Check all staging infrastructure
kubectl get all -n staging

# Check PostgreSQL cluster status
kubectl get clusters.postgresql.cnpg.io -n staging
kubectl describe cluster database -n staging

# Check Keycloak
kubectl get pods -n keycloak-system
kubectl logs -f -n keycloak-system keycloak-instance-staging-0

# Check ArgoCD applications
kubectl get application -n argocd -o wide | grep staging

# Check sealed secrets
kubectl get sealedsecret -n keycloak-system
kubectl get secret -n keycloak-system keycloak-db-credentials
```

