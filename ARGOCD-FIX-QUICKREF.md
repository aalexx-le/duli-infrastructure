# ArgoCD OutOfSync Fix - Quick Reference

## 🚀 IMMEDIATE FIX (Run Now)

```bash
cd /Users/Na/Projects/duli-ai/infrastructure-kubernetes
./fix-argocd-sync.sh
```

This will:
1. ✅ Delete duplicate ArgoCD apps (`keycloak-db-prod`, `infrastructure-secrets-prod`)
2. ✅ Refresh remaining apps to clear OutOfSync status
3. ✅ Verify final status

**Expected Time:** 30-60 seconds

---

## 🔧 PERMANENT FIX (Already Committed)

### Code Changes Made:

1. **Ansible Playbook** (`ansible/playbooks/deploy_applications.yml`)
   - Split into shared vs environment-specific app deployment
   - Shared apps only created when `target_environment=staging`
   - Prevents duplicate app creation

2. **ArgoCD App Templates** (`gitops/applications/*.yml.j2`)
   - Added `ignoreDifferences` for operator-managed fields
   - Prevents false OutOfSync from operator updates

### Files Changed:
- ✅ `ansible/playbooks/deploy_applications.yml`
- ✅ `gitops/applications/keycloak-db.yml.j2`
- ✅ `gitops/applications/rabbitmq-instance.yml.j2`
- ✅ `gitops/applications/keycloak-instance.yml.j2`
- ✅ `gitops/applications/infrastructure-secrets.yml.j2`

### Commits:
- `8110531` - Add ignoreDifferences for operator-managed resources
- `a9733df` - Add ignoreDifferences for Keycloak operator
- `3227cb8` - Expand RabbitMQ ignoreDifferences
- `8cd2d18` - Prevent duplicate apps for shared resources

---

## 📋 VERIFICATION STEPS

### 1. Check Application Status
```bash
kubectl get applications -n argocd | grep -E "NAME|prod|staging"
```

**Expected Result:**
```
infrastructure-secrets-staging   Synced    Healthy
keycloak-db-staging              Synced    Healthy
keycloak-instance-prod           Synced    Healthy
keycloak-instance-staging        Synced    Healthy
postgresql-instance-prod         Synced    Healthy
rabbitmq-instance-prod           Synced    Healthy
redis-instance-prod              Synced    Healthy
```

### 2. Verify No Shared Resource Warnings
```bash
kubectl get applications -n argocd -o yaml | grep "SharedResourceWarning" || echo "✓ No warnings"
```

### 3. Check All Pods Running
```bash
kubectl get pods -n prod
kubectl get pods -n staging
kubectl get pods -n keycloak-system
```

---

## 🔄 RE-DEPLOY AFTER FIX

### For Staging:
```bash
cd ansible
ansible-playbook -i inventories/hosts.ini playbooks/deploy_applications.yml -e target_environment=staging
```
Creates: shared apps + staging-specific apps

### For Production:
```bash
cd ansible
ansible-playbook -i inventories/hosts.ini playbooks/deploy_applications.yml -e target_environment=prod
```
Creates: only prod-specific apps (skips shared)

---

## 🏗️ ARCHITECTURE SUMMARY

### Shared Resources (Managed by `-staging` Apps)
- **keycloak-db** → Used by both prod and staging Keycloak
- **infrastructure-secrets** → Secrets for all environments

### Environment-Specific Resources (Separate Apps)
- **PostgreSQL** → `database` in `prod` / `staging` namespaces
- **Redis** → `redis-replication` in `prod` / `staging` namespaces
- **RabbitMQ** → `queue` in `prod` / `staging` namespaces
- **Keycloak** → `keycloak-instance-prod` / `keycloak-instance-staging` in `keycloak-system`
- **Applications** → `backend`, `ai-service`, `scheduler` in separate namespaces

---

## ❌ ROLLBACK (If Needed)

```bash
cd infrastructure-kubernetes
git revert 8cd2d18
git push

# Then re-run Ansible for both environments
cd ansible
ansible-playbook -i inventories/hosts.ini playbooks/deploy_applications.yml -e target_environment=staging
ansible-playbook -i inventories/hosts.ini playbooks/deploy_applications.yml -e target_environment=prod
```

---

## 📖 FULL DOCUMENTATION

See: `docs/argocd-outsync-fix.md` for complete details including:
- Root cause analysis
- Step-by-step solutions
- Architecture diagrams
- Troubleshooting guide

---

## 💡 KEY TAKEAWAYS

1. **Don't create duplicate ArgoCD apps** for resources that exist only once
2. **Use `ignoreDifferences`** for operator-managed fields that cause drift
3. **Understand your architecture** - know which resources are shared vs environment-specific
4. **SharedResourceWarning** in ArgoCD means multiple apps are fighting over the same resource
