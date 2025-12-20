# Infrastructure Troubleshooting Report - 2025-12-20

## Executive Summary

Full infrastructure audit and fix session covering secrets management, database connectivity, Cloudflare tunnel configuration, and TLS certificate issuance.

---

## Issue 1: Vault Variables Mismatch

### Investigation
Compared actual `vault.yml` with `vault.yml.example` and codebase usage.

### Findings
| Variable | Status | Notes |
|----------|--------|-------|
| `vault_rabbitmq_password` | **Unused** | RabbitMQ operator auto-generates `queue-default-user` secret |
| `vault_cloudflare_tunnel_id` | **Unused** | Auto-generated, stored in `~/.cloudflared/` |
| `vault_cloudflare_tunnel_secret` | **Unused** | Auto-generated, stored in `~/.cloudflared/` |
| `vault_postgres_app_password` | **Missing** | Required for Keycloak DB connection |
| `vault_oauth_google_client_id` | **Missing** | Required for Keycloak OAuth |
| `vault_oauth_google_client_secret` | **Missing** | Required for Keycloak OAuth |
| `vault_keycloak_backend_service_secret` | **Missing** | Required for backend authentication |

### Resolution
- Removed unused variables from `vault.yml.example`
- Added missing variables to user's vault
- Updated `deploy_applications.yml` to remove rabbitmq from sealed secret verification

---

## Issue 2: Keycloak CrashLoopBackOff

### Investigation
```bash
kubectl get pods -n keycloak-system
kubectl logs -n keycloak-system keycloak-instance-staging-0
kubectl describe pod -n keycloak-system keycloak-instance-staging-0
```

### Findings
1. **Database connection refused** - Keycloak couldn't connect to PostgreSQL
2. **Wrong password** - `keycloak-system/database-app` secret had different password than CloudNativePG generated

```bash
# keycloak-system had:
kubectl get secret -n keycloak-system database-app -o jsonpath='{.data.password}' | base64 -d
# Output: abcd1234 (from sealed secret)

# staging had (CloudNativePG generated):
kubectl get secret -n staging database-app -o jsonpath='{.data.password}' | base64 -d
# Output: gfaBO2INRN9KFD9S1zayNbQOEZig4Pe6tPlyeOkrs9OH78uuPXwkbIAp0WGiVOyA
```

### Root Cause
Sealed secret was generated with a test password, but CloudNativePG auto-generates its own password for the application user.

### Resolution
```bash
STAGING_PASS=$(kubectl get secret -n staging database-app -o jsonpath='{.data.password}')
kubectl patch secret -n keycloak-system database-app -p "{\"data\":{\"password\":\"$STAGING_PASS\"}}"
kubectl delete pod -n keycloak-system keycloak-instance-staging-0
```

### Long-term Fix
Either:
1. Configure CloudNativePG to use password from sealed secret, or
2. Use a secret copier/reflector to sync secrets between namespaces

---

## Issue 3: HTTPS Services Not Accessible

### Investigation
```bash
curl -v https://auth.staging.duli.one
curl -v https://argocd.duli.one
dig +short auth.staging.duli.one
dig +short argocd.duli.one
```

### Findings

| Domain | DNS Resolution | Issue |
|--------|----------------|-------|
| `auth.staging.duli.one` | 172.67.x (Cloudflare proxy) | SSL handshake failure |
| `argocd.duli.one` | `fd10:...` (WARP IPv6) | Requires WARP client |

### Root Cause 1: Cloudflare Tunnel Remote Config
The tunnel was configured via Cloudflare Zero Trust dashboard (remote config), which overrides local configmap.

```bash
kubectl logs -n staging cloudflared-xxx --tail=10
# Shows: "Updated to new configuration ... version=3"
# This is the REMOTE config, not local!
```

Local configmap had HTTP routes, but tunnel ignored them because remote config took precedence.

### Root Cause 2: DNS Configuration
- HTTP subdomains were configured as CNAME → `duli.one`
- But `duli.one` A record was only created for production
- Staging had no origin server to route to

### Resolution

**Option A: Use LoadBalancer directly (implemented)**

Changed DNS from CNAME to A records pointing to ingress-nginx LoadBalancer IP:

```yaml
# setup_cloudflare.yml - Before
subdomains:
  - name: "auth.staging"
    type: "CNAME"
    content: "duli.one"

# After
subdomains:
  - name: "auth.staging"
    type: "A"
```

Added task to delete existing CNAMEs before creating A records:
```yaml
- name: Delete existing CNAME records for A record subdomains
  community.general.cloudflare_dns:
    zone: "{{ cloudflare_zone }}"
    record: "{{ item.name }}.{{ cloudflare_zone }}"
    type: CNAME
    api_token: "{{ vault_cloudflare_api_token }}"
    state: absent
  loop: "{{ env_config.subdomains | selectattr('type', 'equalto', 'A') | list }}"
  ignore_errors: yes
```

**Traffic Flow (After Fix):**
```
User → Cloudflare Edge → LoadBalancer IP (129.212.218.28) → ingress-nginx → Service
```

**Option B: Fix Tunnel (alternative)**
- Delete remote config in Cloudflare Zero Trust dashboard
- Or recreate tunnel with `--config-source local` flag

---

## Issue 4: TLS Certificate Not Issuing

### Investigation
```bash
kubectl get certificate -n cert-manager
kubectl describe certificate -n cert-manager duli-one-wildcard
kubectl get challenges -n cert-manager
kubectl logs -n cert-manager -l app=cert-manager --tail=30 | grep error
```

### Findings
```
Status: False
Reason: DoesNotExist
Message: Issuing certificate as Secret does not exist
```

Challenge stuck with errors:
```
Error: 7003: Could not route to /client/v4/zones/dns_records/xxx, perhaps your object identifier is invalid?
```

### Root Cause
Stale DNS record IDs from previous failed attempts. Cert-manager was trying to delete TXT records that no longer existed.

### Resolution
```bash
# Delete stuck resources
kubectl delete certificate -n cert-manager duli-one-wildcard
kubectl delete challenges --all -n cert-manager
kubectl delete certificaterequest --all -n cert-manager

# Trigger re-sync
kubectl patch application cert-manager-issuers -n argocd --type merge \
  -p '{"operation": {"initiatedBy": {"username": "admin"}, "sync": {"revision": "HEAD"}}}'
```

After cleanup, certificate started issuing:
```
State: pending
Reason: Waiting for DNS-01 challenge propagation
```

---

## Issue 5: Helm Charts Configuration Mismatches

### Audit Findings (via Gemini codebase analyzer)

| Issue | Location | Fix |
|-------|----------|-----|
| Redis service name wrong | All app values | `redis-master` → `redis-replication` |
| Scheduler hardcoded namespace | `scheduler/templates/configmap.yml` | `duli` → `{{ .Release.Namespace }}` |
| Keycloak ingress service name | `keycloak-instance/templates/ingress.yaml` | `keycloak-service` → `{{ .Release.Name }}` |
| Wildcard cert missing namespace | `wildcard-certificate.yaml` | Added `keycloak-system` to reflection namespaces |
| Staging hostname wrong | `keycloak-instance/values-staging.yaml` | `auth.duli.one` → `auth.staging.duli.one` |

### Keycloak Fixes Applied
```yaml
# ingress.yaml - Before
name: keycloak-service

# After
name: {{ .Release.Name }}
```

```yaml
# wildcard-certificate.yaml - Before
reflection-auto-namespaces: "staging,prod,argocd,keycloak"

# After
reflection-auto-namespaces: "staging,prod,argocd,keycloak-system"
```

---

## Architecture Clarification

### HTTP vs TCP Service Routing

```
HTTP Services (api, auth, ai, n8n, queue management UI):
  User → Cloudflare Edge → A Record → LoadBalancer (129.212.218.28)
       → ingress-nginx → Kubernetes Service → Pod

TCP Services (db, redis, mq) - Requires WARP:
  User (WARP Client) → Cloudflare Tunnel → cloudflared pod
       → tcp://service.namespace.svc.cluster.local:port → Pod
```

### Why Two Different Approaches?

| Service Type | Why This Approach |
|--------------|-------------------|
| **HTTP** | Standard web traffic, benefits from Cloudflare CDN/DDoS protection, public access needed |
| **TCP** | Database/cache connections, need authentication via Zero Trust, WARP provides secure tunnel |

---

## Commands Reference

### Check Pod Status
```bash
kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded
```

### Check ArgoCD Applications
```bash
kubectl get applications -n argocd
kubectl describe application <name> -n argocd | grep -E "Message:|Status:"
```

### Test Service Connectivity
```bash
# Direct to LoadBalancer (bypasses Cloudflare)
curl -sI --resolve auth.staging.duli.one:443:129.212.218.28 https://auth.staging.duli.one

# Through Cloudflare
curl -sI https://auth.staging.duli.one
```

### Check Certificate Status
```bash
kubectl get certificate -A
kubectl get challenges -A
kubectl describe certificate -n cert-manager <name>
```

### Restart Cloudflared After Config Change
```bash
helm upgrade cloudflared helm/cloudflared -n staging \
  -f helm/cloudflared/values.yaml \
  -f helm/cloudflared/values-staging.yaml

kubectl rollout restart deployment -n staging cloudflared-cloudflare-tunnel
```

---

## Pending Items

1. **TLS Certificate**: Currently issuing, wait for DNS propagation (~5-10 minutes)
2. **Redis Service Name**: Fix in all app values files (`redis-master` → `redis-replication`)
3. **Scheduler ConfigMap**: Fix hardcoded namespace
4. **Git Push**: Commit all local changes and push to trigger ArgoCD sync
