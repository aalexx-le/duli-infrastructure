# RBAC Configuration for Team Members

This directory contains RBAC (Role-Based Access Control) configurations for team member access to the Kubernetes cluster.

## Structure

```
rbac/
├── roles/                    # Kubernetes Role definitions (namespace-scoped)
│   ├── developer-role.yaml  # Developer read/write access
│   ├── viewer-role.yaml     # View-only access
│   └── admin-role.yaml      # Full namespace access
├── rolebindings/            # RoleBinding definitions (namespace-scoped)
│   ├── developer-binding-staging.yaml
│   ├── developer-binding-prod.yaml
│   ├── viewer-binding.yaml
│   └── admin-binding.yaml
├── clusterroles/            # ClusterRole definitions (cluster-scoped)
│   └── cluster-viewer.yaml  # Cluster-wide read-only access
├── clusterrolebindings/     # ClusterRoleBinding definitions
│   └── cluster-viewer-binding.yaml
└── serviceaccounts/         # ServiceAccount for CI/CD and automation
    ├── ci-cd-sa.yaml        # CI/CD pipeline access
    └── monitoring-sa.yaml   # Monitoring and observability
```

## Quick Start

### 1. Create a Developer User with Staging Access

```bash
# Create role and rolebinding
kubectl apply -f rbac/roles/developer-role.yaml
kubectl apply -f rbac/rolebindings/developer-binding-staging.yaml
```

### 2. Create a View-Only User

```bash
# Create role and rolebinding
kubectl apply -f rbac/roles/viewer-role.yaml
kubectl apply -f rbac/rolebindings/viewer-binding.yaml
```

### 3. Create a ServiceAccount for CI/CD

```bash
# Create service account and bindings
kubectl apply -f rbac/serviceaccounts/ci-cd-sa.yaml
```

## Access Levels

### View-Only (Read)
- List pods, services, deployments, etc.
- View logs
- Describe resources
- No create/update/delete permissions

### Developer (Read/Write)
- All view-only permissions
- Create/update/delete deployments
- Create/update ConfigMaps and Secrets
- Scale deployments
- View pod logs and events

### Admin (Full)
- All permissions within namespace
- Can create/update/delete any resource

## Team Member Setup

### For User Authentication (Certificates)

1. **Generate client certificate**
```bash
# Create private key
openssl genrsa -out ${USER}.key 2048

# Create certificate signing request
openssl req -new -key ${USER}.key -out ${USER}.csr \
  -subj "/CN=${USER}/O=development"

# Sign with cluster CA (requires admin access)
kubectl certificate approve ${USER} -n default
```

2. **Create kubeconfig**
```bash
# Get cluster info
CLUSTER_NAME=$(kubectl config current-context)
CLUSTER_API=$(kubectl cluster-info | grep 'Kubernetes master' | awk '/https/ {print $NF}')

# Create kubeconfig file
cat > ${USER}-kubeconfig.yaml <<EOF
apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: $(cat ~/.kube/config | grep certificate-authority-data | awk '{print $2}')
    server: ${CLUSTER_API}
  name: ${CLUSTER_NAME}
contexts:
- context:
    cluster: ${CLUSTER_NAME}
    user: ${USER}
  name: ${CLUSTER_NAME}
current-context: ${CLUSTER_NAME}
kind: Config
preferences: {}
users:
- name: ${USER}
  user:
    client-certificate-data: $(base64 -i ${USER}.crt)
    client-key-data: $(base64 -i ${USER}.key)
EOF
```

### For ServiceAccount (CI/CD)

```bash
# Get service account token
TOKEN=$(kubectl get secret -n ${NAMESPACE} \
  $(kubectl get secret -n ${NAMESPACE} | grep ${SA_NAME} | awk '{print $1}') \
  -o jsonpath='{.data.token}' | base64 -d)

# Create kubeconfig with token
cat > ci-cd-kubeconfig.yaml <<EOF
apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: $(cat ~/.kube/config | grep certificate-authority-data | awk '{print $2}')
    server: ${CLUSTER_API}
  name: ${CLUSTER_NAME}
contexts:
- context:
    cluster: ${CLUSTER_NAME}
    user: ci-cd
  name: ${CLUSTER_NAME}
current-context: ${CLUSTER_NAME}
kind: Config
preferences: {}
users:
- name: ci-cd
  user:
    token: ${TOKEN}
EOF
```

## Security Best Practices

1. **Principle of Least Privilege**
   - Grant only the minimum permissions needed
   - Use namespace-scoped roles when possible
   - Avoid cluster-admin role for developers

2. **Separation of Concerns**
   - Staging developers ≠ Production developers
   - Read-only users for monitoring/observability
   - ServiceAccounts for automation

3. **Audit & Monitoring**
   - Enable RBAC audit logging
   - Monitor who accessed what
   - Review permissions regularly

4. **Credential Management**
   - Store kubeconfig files securely
   - Rotate tokens regularly
   - Use short-lived credentials when possible

## Common Scenarios

### Scenario 1: Developer with Staging Access
- Role: `developer-role` (create/update/delete)
- Namespace: `staging`
- Access to: All resources in staging namespace

### Scenario 2: DevOps with Production Access
- Role: `admin-role` (full control)
- Namespace: `prod`
- Additional: cluster read-only for debugging

### Scenario 3: CI/CD Pipeline
- ServiceAccount: `ci-cd`
- Namespace: `staging` and `prod`
- Permissions: Deploy, update, scale (no delete)

### Scenario 4: Monitoring Team
- Role: `cluster-viewer`
- Access: Read pods, logs, metrics cluster-wide
- No: Create/update/delete

## Troubleshooting

### Check user permissions
```bash
kubectl auth can-i get pods --as=${USERNAME} -n staging
kubectl auth can-i create deployments --as=${USERNAME} -n staging
kubectl auth can-i delete secrets --as=${USERNAME} -n prod
```

### View effective RBAC
```bash
# List all roles in namespace
kubectl get roles -n staging

# List all role bindings
kubectl get rolebindings -n staging

# Describe a specific role
kubectl describe role developer-role -n staging
```

### Test access
```bash
# Set kubeconfig
export KUBECONFIG=/path/to/user-kubeconfig.yaml

# Test access
kubectl get pods -n staging
kubectl logs ${POD_NAME} -n staging
kubectl create deployment test --image=nginx -n staging
```

## Next Steps

1. Decide on access levels for each team member
2. Create necessary roles and rolebindings
3. Generate kubeconfig files for each user
4. Distribute securely (encrypted)
5. Test and verify access
6. Document team member access matrix

