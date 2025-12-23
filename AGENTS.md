# Infrastructure Kubernetes - Agent Documentation

## Quick Start

Complete cluster setup with Kubernetes provisioning + Operator-based deployment:

```bash
# Step 1: Provision Kubernetes cluster with Terraform
cd terraform
terraform apply

# Step 2: Deploy Kubernetes and applications with Ansible
cd ../ansible

# Deploy complete infrastructure and applications
ansible-playbook -i inventories/hosts.ini playbooks/site.yml -e target_environment=staging
ansible-playbook -i inventories/hosts.ini playbooks/site.yml -e target_environment=prod

# Deploy with verbose output
ansible-playbook -vvv -i inventories/hosts.ini playbooks/site.yml -e target_environment=staging

# Deploy specific phase
ansible-playbook -i inventories/hosts.ini playbooks/kubespray.yml
ansible-playbook -i inventories/hosts.ini playbooks/do_csi_driver.yml
ansible-playbook -i inventories/hosts.ini playbooks/install_infrastructures.yml -e target_environment=staging
```

**Note:** The cluster is shared for both staging and production environments:
- Both environments use the same Kubernetes cluster
- Applications deploy to separate namespaces: `staging` and `prod`
- Operators run in dedicated system namespaces (e.g., `cnpg-system`, `redis-operator-system`, `rabbitmq-system`)

## Project Structure

```
infrastructure-kubernetes/
├── terraform/                       # Infrastructure provisioning
│   ├── main.tf                      # Cluster configuration
│   ├── variables.tf                 # Cluster variables
│   ├── outputs.tf                   # Cluster outputs
│   ├── terraform.tfvars             # Cluster configuration values
│   ├── modules/                     # networking, kubernetes-cluster
│   └── templates/inventory.tpl      # Auto-generates ansible inventory
├── ansible/                         # Configuration management
│   ├── playbooks/                   # Orchestration playbooks
│   │   ├── site.yml                 # Main orchestration
│   │   ├── kubespray.yml            # Kubernetes cluster setup
│   │   ├── do_csi_driver.yml        # DigitalOcean storage driver
│   │   ├── do_cloud_controller_manager.yml  # DigitalOcean CCM
│   │   ├── install_infrastructures.yml      # Operators and ArgoCD
│   │   ├── setup_dns.yml            # DNS and SSL/TLS
│   │   ├── generate_sealed_secrets.yml      # Sealed secrets
│   │   ├── deploy_applications.yml  # Application deployment
│   │   └── export_connection.yml    # Connection info export
│   ├── inventories/                 # Cluster inventory (auto-generated)
│   │   ├── hosts.ini                # Cluster hosts
│   │   └── group_vars/all/
│   │       ├── vars.yml             # Service configuration
│   │       ├── versions.yml         # Component versions
│   │       └── vault.yml            # Encrypted secrets
│   ├── templates/                   # Ansible templates
│   ├── ansible.cfg                  # Ansible configuration
│   └── .vault_pass                  # Vault password file
├── helm/                            # Helm charts (operator-based architecture)
│   ├── backend/                     # Application service
│   ├── ai-service/                  # Application service
│   ├── scheduler/                   # Application service (n8n)
│   ├── postgres-operator/           # CloudNativePG operator
│   ├── postgres-instance/           # PostgreSQL cluster CR
│   ├── redis-operator/              # Redis operator
│   ├── redis-instance/              # Redis cluster CR
│   ├── rabbitmq-operator/           # RabbitMQ operator
│   ├── rabbitmq/                    # RabbitMQ cluster CR
│   ├── rabbitmq-topology-operator/  # RabbitMQ topology operator
│   ├── keycloak-operator/           # Keycloak operator
│   ├── keycloak-db/                 # Keycloak database CR
│   ├── keycloak-instance/           # Keycloak instance CR
│   ├── kube-prometheus-stack/       # Monitoring stack
│   ├── loki/                        # Log aggregation
│   ├── cert-manager-issuers/        # Certificate issuers
│   ├── argocd-ingress/              # ArgoCD ingress
│   └── secrets/                     # Sealed secrets
├── gitops/                          # GitOps configuration
│   └── applications/                # ArgoCD Application CRDs
│       ├── cloudnative-pg-operator.yml.j2
│       ├── postgresql-instance.yml.j2
│       ├── redis-operator.yml.j2
│       ├── redis-instance.yml.j2
│       ├── rabbitmq-operator.yml.j2
│       ├── rabbitmq-instance.yml.j2
│       ├── backend.yml.j2
│       ├── ai-service.yml.j2
│       ├── scheduler.yml.j2
│       └── ...
├── kubespray/                       # Kubernetes cluster installer (vendored)
├── scripts/                         # Utility scripts
└── AGENTS.md                        # This file
```

## Orchestration Playbooks

Main entry: `ansible/playbooks/site.yml` (orchestrates all phases)

**Modular Playbooks:**
- `kubespray.yml` - Kubernetes cluster provisioning (includes ingress-nginx)
- `do_csi_driver.yml` - DigitalOcean Block Storage CSI driver
- `do_cloud_controller_manager.yml` - DigitalOcean Cloud Controller Manager
- `install_infrastructures.yml` - Cert-Manager, ArgoCD, Kubernetes operators
- `setup_dns.yml` - DNS records and SSL/TLS configuration
- `generate_sealed_secrets.yml` - Sealed secrets generation
- `deploy_applications.yml` - Application services deployment via ArgoCD
- `export_connection.yml` - Connection information export

**Execution Order:**
1. `kubespray.yml` - Creates Kubernetes cluster with ingress-nginx
2. `do_csi_driver.yml` - Installs DigitalOcean CSI driver (creates `do-block-storage` StorageClass)
3. `do_cloud_controller_manager.yml` - Installs DigitalOcean CCM for LoadBalancer support
4. `install_infrastructures.yml` - Deploys:
   - Cert-Manager (TLS certificates)
   - ArgoCD (GitOps deployment platform)
   - CloudNativePG operator (PostgreSQL)
   - Redis operator
   - RabbitMQ operator
   - Keycloak operator
   - Kube-prometheus-stack (monitoring)
   - Loki (logging)
5. `setup_dns.yml` - Configures DNS records and SSL/TLS certificates
6. `generate_sealed_secrets.yml` - Generates sealed secrets for applications
7. `deploy_applications.yml` - Deploys application services via ArgoCD
8. `export_connection.yml` - Exports connection information

Each playbook waits for resources to be Ready before importing the next.

**Application Deployment Flow:**
Applications are managed by ArgoCD using GitOps:
- Source: Helm charts in `helm/{app}`
- Configuration: Values in chart directories
- Orchestration: ArgoCD Application CRDs in `gitops/applications/{app}.yml.j2`
- Automatic sync: Changes in Git repository automatically deploy within 3 minutes

## Environment Setup

**Single Shared Cluster Architecture:**
- All environments (staging and production) deploy to the same Kubernetes cluster
- Environment isolation is achieved through separate Kubernetes namespaces
- Operators run in dedicated system namespaces (shared across environments)
- Database/cache/queue instances are deployed per-environment

### Cluster Inventory
- Path: `ansible/inventories/`
- Usage: Target hosts for the shared Kubernetes cluster
- Auto-generated by: Terraform (`terraform apply`)
- Configuration: `group_vars/all/vars.yml`
- Secrets: `group_vars/all/vault.yml` (Ansible Vault)

### Staging Environment
- **Namespace:** `staging`
- **Usage:** Development and testing
- **Image Tags:** Latest development versions (e.g., `latest`)
- **Replicas:** Reduced for cost efficiency (1-2 replicas)
- **Resources:** Lower CPU/memory requests and limits
- **Database/Cache/Queue:** Dedicated instances in `staging` namespace

### Production Environment
- **Namespace:** `prod`
- **Usage:** Production deployments
- **Image Tags:** Specific version tags (e.g., `v1.0.0`)
- **Replicas:** Higher for availability (2-3+ replicas)
- **Resources:** Higher CPU/memory requests and limits
- **Autoscaling:** Enabled for select services
- **PDB:** Pod Disruption Budgets enforced
- **Database/Cache/Queue:** Dedicated instances in `prod` namespace

### Inventory Configuration

The shared cluster inventory structure:
```
ansible/inventories/
├── hosts.ini                    # Cluster hosts (auto-generated by Terraform)
└── group_vars/all/
    ├── vars.yml                 # Shared service configuration
    ├── versions.yml             # Component versions
    └── vault.yml                # Encrypted secrets (Ansible Vault)
```

**Setup Instructions:**
1. Run `terraform apply` in `terraform/` directory
2. This auto-generates `ansible/inventories/hosts.ini`
3. Copy and customize `vault.yml.example` to `vault.yml`
4. Encrypt with: `ansible-vault encrypt ansible/inventories/group_vars/all/vault.yml`
5. Run: `ansible-playbook -i inventories/hosts.ini playbooks/site.yml -e target_environment=staging`

## Service Configuration

### Deployment Architecture

**Kubernetes Operators** (Deployed via ArgoCD to system namespaces):
- CloudNativePG operator (`cnpg-system` namespace) - PostgreSQL clusters
- Redis operator (`redis-operator-system` namespace) - Redis instances
- RabbitMQ operator (`rabbitmq-system` namespace) - RabbitMQ clusters
- RabbitMQ topology operator (`rabbitmq-system` namespace) - RabbitMQ topology management
- Keycloak operator (`keycloak-system` namespace) - Keycloak instances

**Infrastructure Instances** (Deployed via ArgoCD per environment):
- PostgreSQL cluster (CloudNativePG CR in `staging` or `prod` namespace)
- Redis cluster (Redis CR in `staging` or `prod` namespace)
- RabbitMQ cluster (RabbitmqCluster CR in `staging` or `prod` namespace)

**Platform Services** (Deployed via Ansible):
- Cert-Manager (`cert-manager` namespace) - TLS certificate management
- ArgoCD (`argocd` namespace) - GitOps continuous deployment
- Kube-prometheus-stack (`monitoring` namespace) - Metrics and alerting
- Loki (`monitoring` namespace) - Log aggregation

**Applications** (Deployed via ArgoCD per environment):
- Backend API (`staging` or `prod` namespace)
- AI-Service (`staging` or `prod` namespace)
- Scheduler (n8n) (`staging` or `prod` namespace)

### PostgreSQL (CloudNativePG Operator)

**Operator:**
- Chart: CloudNativePG operator
- Namespace: `cnpg-system`
- Purpose: Manages PostgreSQL cluster lifecycle
- Version: 1.27.1

**Instances (Per Environment):**
- Custom Resource: `Cluster` (CloudNativePG CRD)
- Namespace: `staging` or `prod`
- Architecture: Primary-replica with automatic failover
- Default: 3 PostgreSQL nodes
- Storage: Persistent volumes via `do-block-storage`
- Backup: Point-in-time recovery (PITR) support
- Endpoints:
  - Read/Write: `database-rw.{namespace}.svc.cluster.local:5432`
  - Read-only: `database-ro.{namespace}.svc.cluster.local:5432`
  - Read: `database-r.{namespace}.svc.cluster.local:5432`

### Redis (Redis Operator)

**Operator:**
- Chart: OT-CONTAINER-KIT/redis-operator
- Namespace: `redis-operator-system`
- Purpose: Manages Redis cluster lifecycle

**Instances (Per Environment):**
- Custom Resource: `Redis` or `RedisCluster` CRD
- Namespace: `staging` or `prod`
- Architecture: Master-replica with Sentinel for failover
- Default: 1 master, 2 replicas, 3 Sentinel nodes
- Storage: Persistent volumes via `do-block-storage`
- Endpoints:
  - Master: `redis-master.{namespace}.svc.cluster.local:6379`
  - Replica: `redis-replica.{namespace}.svc.cluster.local:6379`

### RabbitMQ (RabbitMQ Cluster Operator)

**Operators:**
- Cluster Operator: Manages RabbitMQ clusters (`rabbitmq-system` namespace)
- Topology Operator: Manages RabbitMQ topology (exchanges, queues, bindings) (`rabbitmq-system` namespace)

**Instances (Per Environment):**
- Custom Resource: `RabbitmqCluster` CRD
- Namespace: `staging` or `prod`
- Architecture: Multi-node cluster with peer discovery
- Default: 3 cluster nodes
- Storage: Persistent volumes via `do-block-storage`
- Endpoints:
  - AMQP: `queue.{namespace}.svc.cluster.local:5672`
  - Management: `queue.{namespace}.svc.cluster.local:15672`

### TCP Services Access

**Internal (Applications inside cluster):**
- Staging Database: `database-rw.staging.svc.cluster.local:5432`
- Production Database: `database-rw.prod.svc.cluster.local:5432`
- Staging Redis: `redis-master.staging.svc.cluster.local:6379`
- Production Redis: `redis-master.prod.svc.cluster.local:6379`
- Staging RabbitMQ: `queue.staging.svc.cluster.local:5672`
- Production RabbitMQ: `queue.prod.svc.cluster.local:5672`

**External (Developers, tools, CI/CD - via ingress-nginx LoadBalancer):**
- Staging PostgreSQL: `db-staging.duli.one:5432`
- Production PostgreSQL: `db.duli.one:5433`
- Staging Redis: `redis-staging.duli.one:6379`
- Production Redis: `redis.duli.one:6380`
- Staging RabbitMQ: `mq-staging.duli.one:5672`
- Production RabbitMQ: `mq.duli.one:5673`

**Note:** Applications always use internal service names (ClusterIP) for better performance and security. External domains are only for developer access from outside the cluster.

### Application Services (ArgoCD-managed)

Applications are deployed and managed by ArgoCD using GitOps. All configuration is version-controlled in Git. Applications are deployed to environment-specific namespaces (`staging` and `prod`).

**Backend:**
- Chart: `helm/backend`
- Resource Name: `backend` (deployed to `staging` or `prod` namespace)
- Staging: 1 replica, latest image tag, debug logging, 512Mi memory
- Production: 2 replicas, versioned image tag, info logging, 1Gi memory, PDB enabled
- ArgoCD Template: `gitops/applications/backend.yml.j2`

**AI-Service (ML workload):**
- Chart: `helm/ai-service`
- Resource Name: `ai-service` (deployed to `staging` or `prod` namespace)
- Staging: 2 replicas, higher CPU/memory for ML, latest image tag
- Production: 3 replicas, higher resource limits (4Gi memory), autoscaling enabled
- ArgoCD Template: `gitops/applications/ai-service.yml.j2`

**Scheduler (n8n):**
- Chart: `helm/scheduler`
- Resource Name: `scheduler` (deployed to `staging` or `prod` namespace)
- Staging: 1 replica, 10Gi persistent storage, debug logging
- Production: 2 replicas, 20Gi persistent storage, info logging
- Database: Connects to PostgreSQL cluster in same namespace
- ArgoCD Template: `gitops/applications/scheduler.yml.j2`

**GitOps Workflow:**
1. Update Helm chart or values in `helm/{app}/`
2. Commit to Git repository
3. ArgoCD automatically detects changes and syncs within 3 minutes
4. All changes tracked in Git history for audit trail

## Configuration Management

### ConfigMap and Secret Best Practices

**Critical Security Rules:**

1. **Never put passwords in ConfigMaps** - Always use Secrets
2. **Split connection strings** - Use individual environment variables
3. **Use envFrom for multiple variables** - Cleaner than individual env entries
4. **Use SealedSecrets** - For secrets stored in Git

**ConfigMap Usage:**
- ✅ Non-sensitive configuration (log levels, feature flags, URLs, ports)
- ✅ Environment variables (NODE_ENV, PYTHONUNBUFFERED)
- ❌ Never passwords, API keys, or connection strings with credentials

**Secret Usage:**
- ✅ Passwords and API keys
- ✅ Database credentials
- ✅ TLS certificates
- ✅ Any sensitive data

**SealedSecret Usage:**
- ✅ Encrypted secrets stored in Git
- ✅ Decrypted by sealed-secrets controller in cluster
- ✅ Namespace-scoped encryption

**Example Pattern:**

```yaml
# ConfigMap (non-sensitive)
apiVersion: v1
kind: ConfigMap
data:
  DATABASE_HOST: "database-rw.staging.svc.cluster.local"
  DATABASE_PORT: "5432"

---
# SealedSecret (sensitive, encrypted in Git)
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: app-secret
spec:
  encryptedData:
    DATABASE_USER: AgB...encrypted...
    DATABASE_PASSWORD: AgB...encrypted...
    DATABASE_NAME: AgB...encrypted...
```

### Ansible Vault

Sensitive credentials are stored in encrypted vault files:
- Location: `ansible/inventories/group_vars/all/vault.yml`
- Encryption: Ansible Vault
- Password file: `ansible/.vault_pass`

**Required Vault Variables:**
- `vault_postgres_password` - PostgreSQL superuser password
- `vault_redis_password` - Redis password
- `vault_rabbitmq_password` - RabbitMQ password
- `vault_do_api_token` - DigitalOcean API token (for CSI driver)
- `vault_cloudflare_api_token` - Cloudflare API token (for DNS)

**Create/Edit Vault:**
```bash
cd ansible
ansible-vault edit inventories/group_vars/all/vault.yml
```

## Storage Configuration

### Helm Repositories

The following Helm repositories are used:

- **Argo**: `https://argoproj.github.io/argo-helm`
  - Used for: ArgoCD
  - Added in: `install_infrastructures.yml`

- **Jetstack**: `https://charts.jetstack.io`
  - Used for: Cert-Manager
  - Added in: `install_infrastructures.yml`

- **DigitalOcean OCI Registry**: `oci://registry.digitalocean.com/digitalocean/csi-digitalocean`
  - Used for: DigitalOcean CSI driver
  - Installed directly from OCI registry (no repository add needed)
  - Playbook: `do_csi_driver.yml`

### DigitalOcean Block Storage

Kubespray does not natively support DigitalOcean block storage. We install the DigitalOcean CSI driver via Helm:

**Playbook:** `ansible/playbooks/do_csi_driver.yml`

**What it does:**
1. Creates Kubernetes Secret with DO API token
2. Installs CSI driver via Helm from OCI registry
3. Waits for controller and node pods to be ready
4. Verifies `do-block-storage` StorageClass is created

**StorageClass:** `do-block-storage`
- Provisioner: `dobs.csi.digitalocean.com`
- Volume binding: WaitForFirstConsumer
- Reclaim policy: Delete

**Required:**
- `vault_do_api_token` in vault.yml
- Get token from: https://cloud.digitalocean.com/account/api/tokens

### Persistent Volumes

All stateful services use persistent volumes:
- PostgreSQL: Defined in Cluster CR (managed by CloudNativePG)
- Redis: Defined in Redis CR (managed by Redis operator)
- RabbitMQ: Defined in RabbitmqCluster CR (managed by RabbitMQ operator)
- Scheduler: 10Gi (staging) / 20Gi (prod)

Volumes are dynamically provisioned using `do-block-storage` StorageClass.

## Security

### Secret Encryption at Rest

Kubespray supports encrypting Secrets in etcd. To enable:

**Add to `ansible/inventories/group_vars/all/vars.yml`:**

```yaml
# Enable Secret encryption at rest
kube_encrypt_secret_data: true
kube_encryption_algorithm: "secretbox"  # Options: secretbox, aescbc, aesgcm
kube_encryption_resources: [secrets]
```

**Note:** This must be configured before initial cluster deployment. Enabling on an existing cluster requires re-encrypting all Secrets.

**Algorithm Options:**
- `secretbox` (recommended) - Default, secure, no rotation needed
- `aescbc` - Not recommended (CBC vulnerability)
- `aesgcm` - Requires rotation every 200k writes
- `kms` - Requires external KMS service

### SealedSecrets

Secrets stored in Git are encrypted using SealedSecrets:
- **Controller:** Deployed to `kube-system` namespace
- **Certificate:** Generated during deployment
- **Workflow:**
  1. Create Secret YAML
  2. Encrypt using `kubeseal` CLI
  3. Store SealedSecret in Git
  4. Controller decrypts in cluster

## Configuration Standards

### Environment Naming and Namespaces
- **Staging Environment:**
  - Kubernetes Namespace: `staging`
  - Application Names: Clean (no suffix) - e.g., `backend`, `ai-service`, `scheduler`
  - Service Endpoints: Use `staging` namespace - e.g., `database-rw.staging.svc.cluster.local`
- **Production Environment:**
  - Kubernetes Namespace: `prod`
  - Application Names: Clean (no suffix) - e.g., `backend`, `ai-service`, `scheduler`
  - Service Endpoints: Use `prod` namespace - e.g., `database-rw.prod.svc.cluster.local`
- **Operator Namespaces:**
  - CloudNativePG: `cnpg-system`
  - Redis Operator: `redis-operator-system`
  - RabbitMQ Operator: `rabbitmq-system`
  - Keycloak Operator: `keycloak-system`

**Best Practice:** Use separate namespaces for environment isolation combined with Kubernetes standard labels (app.kubernetes.io/*, environment, team, tier) for resource identification and querying.

### File Naming Standards
- YAML files: `.yml` extension
- Ansible playbooks: `.yml`
- Helm charts: `.yml`
- Jinja2 templates: `.yml.j2`

### Helm Charts
Charts are centralized in `helm/` directory and deployed via ArgoCD.

**Operator Charts:**
- `postgres-operator/` - CloudNativePG operator
- `redis-operator/` - Redis operator
- `rabbitmq-operator/` - RabbitMQ cluster operator
- `rabbitmq-topology-operator/` - RabbitMQ topology operator
- `keycloak-operator/` - Keycloak operator

**Instance Charts:**
- `postgres-instance/` - PostgreSQL cluster CR
- `redis-instance/` - Redis cluster CR
- `rabbitmq/` - RabbitMQ cluster CR
- `keycloak-db/` - Keycloak database CR
- `keycloak-instance/` - Keycloak instance CR

**Application Charts:**
- `backend/` - Backend API service
- `ai-service/` - AI service application
- `scheduler/` - n8n scheduler

**Platform Charts:**
- `kube-prometheus-stack/` - Monitoring stack
- `loki/` - Log aggregation
- `cert-manager-issuers/` - Certificate issuers
- `argocd-ingress/` - ArgoCD ingress
- `secrets/` - SealedSecrets

## Command Reference

All commands run from `ansible` directory and use `-i inventories/hosts.ini` for the shared cluster.

### Provision Infrastructure
```bash
cd terraform
terraform plan
terraform apply
```

### Run Full Orchestration
```bash
cd ansible

# Deploy staging environment
ansible-playbook -i inventories/hosts.ini playbooks/site.yml -e target_environment=staging

# Deploy production environment
ansible-playbook -i inventories/hosts.ini playbooks/site.yml -e target_environment=prod
```

### Run Individual Phases
```bash
# Kubernetes cluster setup
ansible-playbook -i inventories/hosts.ini playbooks/kubespray.yml

# Storage driver
ansible-playbook -i inventories/hosts.ini playbooks/do_csi_driver.yml

# Operators and infrastructure (requires target_environment)
ansible-playbook -i inventories/hosts.ini playbooks/install_infrastructures.yml -e target_environment=staging

# Applications (requires target_environment)
ansible-playbook -i inventories/hosts.ini playbooks/deploy_applications.yml -e target_environment=staging
```

### Verify Deployment
```bash
kubectl cluster-info
kubectl get nodes

# Check staging environment
kubectl get all -n staging
kubectl get clusters.postgresql.cnpg.io -n staging
kubectl get redis -n staging
kubectl get rabbitmqclusters -n staging

# Check production environment
kubectl get all -n prod
kubectl get clusters.postgresql.cnpg.io -n prod
kubectl get redis -n prod
kubectl get rabbitmqclusters -n prod

# Check operators
kubectl get pods -n cnpg-system
kubectl get pods -n redis-operator-system
kubectl get pods -n rabbitmq-system

# Storage
kubectl get storageclass
kubectl get pv
```

### Check Service Status
```bash
# Operators
kubectl get pods -n cnpg-system
kubectl get pods -n redis-operator-system
kubectl get pods -n rabbitmq-system

# Infrastructure instances - staging
kubectl get pods -n staging -l cnpg.io/cluster=database
kubectl get pods -n staging -l redis.opstreelabs.in/instance-name=redis
kubectl get pods -n staging -l app.kubernetes.io/name=queue

# Application services - staging
kubectl get pods -n staging -l app.kubernetes.io/name=backend
kubectl get pods -n staging -l app.kubernetes.io/name=ai-service
kubectl get pods -n staging -l app.kubernetes.io/name=scheduler

# Infrastructure instances - production
kubectl get pods -n prod -l cnpg.io/cluster=database
kubectl get pods -n prod -l redis.opstreelabs.in/instance-name=redis
kubectl get pods -n prod -l app.kubernetes.io/name=queue

# Application services - production
kubectl get pods -n prod -l app.kubernetes.io/name=backend
kubectl get pods -n prod -l app.kubernetes.io/name=ai-service
kubectl get pods -n prod -l app.kubernetes.io/name=scheduler
```

### ArgoCD Commands
```bash
# Get ArgoCD admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Port-forward to ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Check ArgoCD applications
kubectl get applications -n argocd

# Sync application manually
kubectl patch application backend -n argocd -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"normal"}}}' --type merge
```

## Logging and Output

**Real-time Streaming Output:**
All task output streams directly to console. Output is also automatically saved to `logs/ansible.log`.

**Verbosity Control:**
```bash
# Standard output (default)
ansible-playbook -i inventories/hosts.ini playbooks/site.yml -e target_environment=staging

# Verbose output
ansible-playbook -v -i inventories/hosts.ini playbooks/site.yml -e target_environment=staging

# Very verbose (includes all debug tasks)
ansible-playbook -vv -i inventories/hosts.ini playbooks/site.yml -e target_environment=staging

# Maximum verbosity (connection debugging)
ansible-playbook -vvv -i inventories/hosts.ini playbooks/site.yml -e target_environment=staging
```

## Troubleshooting

### Playbook Won't Start
```bash
ansible --version
ls ../kubespray/cluster.yml
```

### Kubespray Fails
Check inventory and host configuration:
```bash
ansible all -i inventories/hosts.ini -m ping
```

### CSI Driver Issues
Verify DigitalOcean API token and StorageClass:
```bash
kubectl get secret digitalocean-csi-secret -n kube-system
kubectl get storageclass do-block-storage
kubectl get pods -n kube-system -l app=csi-digitalocean-controller
kubectl get pods -n kube-system -l app=csi-digitalocean-node
```

### Operator Issues
```bash
# Check CloudNativePG operator
kubectl get pods -n cnpg-system
kubectl logs -n cnpg-system deployment/cnpg-controller-manager

# Check Redis operator
kubectl get pods -n redis-operator-system
kubectl logs -n redis-operator-system deployment/redis-operator

# Check RabbitMQ operator
kubectl get pods -n rabbitmq-system
kubectl logs -n rabbitmq-system deployment/rabbitmq-cluster-operator
```

### Database/Cache/Queue Issues
```bash
# Check PostgreSQL cluster status
kubectl get cluster -n staging database -o yaml
kubectl cnpg status -n staging database

# Check Redis status
kubectl get redis -n staging redis -o yaml
kubectl describe redis -n staging redis

# Check RabbitMQ status
kubectl get rabbitmqcluster -n staging queue -o yaml
kubectl describe rabbitmqcluster -n staging queue
```

### Application Pods Stuck
```bash
# Check staging environment
watch kubectl get pods -n staging
kubectl describe pod -n staging <pod-name>
kubectl logs -n staging <pod-name>

# Check production environment
watch kubectl get pods -n prod
kubectl describe pod -n prod <pod-name>
kubectl logs -n prod <pod-name>
```

### Persistent Volume Issues
```bash
kubectl get pv

# Check staging environment
kubectl get pvc -n staging
kubectl describe pvc <pvc-name> -n staging

# Check production environment
kubectl get pvc -n prod
kubectl describe pvc <pvc-name> -n prod
```

### ArgoCD Issues
```bash
# Check ArgoCD status
kubectl get pods -n argocd

# Check application sync status
kubectl get application -n argocd backend -o yaml

# View sync errors
kubectl describe application -n argocd backend
```

### Vault Password Issues
Ensure `.vault_pass` exists in `ansible/` directory and is referenced in `ansible.cfg`:
```bash
ls .vault_pass
```

### Cleanup
Reset cluster:
```bash
ansible-playbook -i inventories/hosts.ini ../kubespray/reset.yml
```

Delete staging environment:
```bash
kubectl delete namespace staging
```

Delete production environment:
```bash
kubectl delete namespace prod
```

Delete operators (WARNING: This will delete all managed resources):
```bash
kubectl delete namespace cnpg-system
kubectl delete namespace redis-operator-system
kubectl delete namespace rabbitmq-system
```

## System Requirements

- Ansible 2.17+
- Python 3.8+
- kubectl (latest stable)
- helm v3.0+
- kubeseal (for SealedSecrets)
- SSH access to target hosts (if remote)
- DigitalOcean API token (for CSI driver)
- Cloudflare API token (for DNS management)

## Design Principles

- **Operator-Based**: Kubernetes operators manage database, cache, and queue lifecycle
- **Pure Ansible**: No shell scripts - all native Ansible tasks
- **Modular**: Independent playbooks for each deployment phase
- **Idempotent**: Safe to run repeatedly without side effects
- **Environment-Aware**: Support for multiple environments via `target_environment` variable
- **Resilient**: Built-in retries and health checks
- **Observable**: Real-time output streaming + permanent logs
- **GitOps**: All configuration version-controlled and deployed via ArgoCD
- **Security First**: SealedSecrets for Git-stored secrets, Vault for Ansible secrets

## High Availability Architecture

### PostgreSQL (CloudNativePG)
- **Primary + Replicas**: 1 primary, 2+ replicas for read scaling
- **Automatic Failover**: Operator handles primary promotion
- **Streaming Replication**: Synchronous replication for data safety
- **Backup**: Point-in-time recovery (PITR) support
- **Endpoint**: Read/write at `database-rw`, read-only at `database-ro`

### Redis (Redis Operator)
- **Master-Slave**: 1 master, 2+ replicas for read scaling
- **Sentinel**: Automatic failover with quorum-based decisions
- **Persistence**: RDB and AOF persistence options
- **Endpoint**: Master at `redis-master`, replicas at `redis-replica`

### RabbitMQ (RabbitMQ Cluster Operator)
- **Cluster**: 3+ nodes in a cluster
- **Quorum Queues**: Replicated queues for high availability
- **Peer Discovery**: Kubernetes-based automatic peer discovery
- **Endpoint**: Load-balanced across cluster nodes

## Architecture: IaC vs GitOps

This project follows a **hybrid architecture** separating Infrastructure as Code from GitOps continuous deployment:

### IaC Layer (Bootstrap via Ansible)
**What:** Platform services and operator installation  
**When:** Runs once during initial cluster setup  
**Tools:** Ansible playbooks  
**Scope:** Kubernetes cluster + operators + ArgoCD

**Services in IaC:**
- Kubernetes cluster (Kubespray)
- DigitalOcean CSI driver
- DigitalOcean Cloud Controller Manager
- Cert-Manager (TLS certificate management)
- ArgoCD (GitOps continuous deployment platform)
- Kubernetes operators (CloudNativePG, Redis, RabbitMQ, Keycloak)

**Why IaC?**
- Foundational platform services that bootstrap the cluster
- Operators that rarely change after deployment
- Services required for GitOps to function (ArgoCD)
- DevOps team responsibility

### GitOps Layer (Continuous via ArgoCD)
**What:** Infrastructure instances and application deployment  
**When:** Runs 24/7 watching Git repository for changes  
**Tools:** ArgoCD (continuous deployment)  
**Scope:** Database/cache/queue instances + application services

**Services in GitOps:**
- PostgreSQL clusters (CloudNativePG CR)
- Redis clusters (Redis CR)
- RabbitMQ clusters (RabbitmqCluster CR)
- Backend API service
- AI Service (ML workload)
- Scheduler (n8n)
- Monitoring stack (Prometheus, Grafana, Loki)

**Why GitOps?**
- Infrastructure instances that may change (scaling, configuration)
- Stateless applications that change frequently
- Developer workflow (commit → auto-deploy)
- Declarative source of truth in Git
- Application team responsibility

### Deployment Flow
```
STEP 1: IaC Bootstrap (Ansible - runs once)
  ├─ ansible-playbook site.yml -e target_environment=staging
  ├─ Deploys: K8s, CSI driver, CCM
  ├─ Installs: Cert-Manager, ArgoCD
  ├─ Deploys: Operators (CloudNativePG, Redis, RabbitMQ, Keycloak)
  └─ Creates: ArgoCD Application CRDs (bootstrap)

     ↓

STEP 2: GitOps Management (ArgoCD - continuous 24/7)
  ├─ ArgoCD watches: Git repository (this repo)
  ├─ When changes detected: automatic sync to cluster
  ├─ Manages: Database/cache/queue instances, applications
  └─ Result: infrastructure and apps deployed from Git (source of truth)
```

### Key Design Principle
**Separation of Concerns:**
- IaC handles platform bootstrap (once)
- GitOps handles infrastructure instances and applications (continuous)
- ArgoCD itself is installed by Ansible, then manages everything else
- This is **industry best practice** (Netflix, Stripe, etc. follow this pattern)

## Namespace Architecture

```
Cluster (Shared)
├── System Namespaces (Operators - deployed once)
│   ├── cnpg-system              # CloudNativePG operator
│   ├── redis-operator-system    # Redis operator
│   ├── rabbitmq-system          # RabbitMQ operators
│   ├── keycloak-system          # Keycloak operator
│   ├── cert-manager             # Cert-Manager
│   ├── argocd                   # ArgoCD
│   └── monitoring               # Prometheus, Grafana, Loki
│
├── Staging Environment (staging namespace)
│   ├── database                 # PostgreSQL cluster CR
│   ├── redis                    # Redis cluster CR
│   ├── queue                    # RabbitMQ cluster CR
│   ├── backend                  # Backend API
│   ├── ai-service               # AI service
│   └── scheduler                # n8n scheduler
│
└── Production Environment (prod namespace)
    ├── database                 # PostgreSQL cluster CR
    ├── redis                    # Redis cluster CR
    ├── queue                    # RabbitMQ cluster CR
    ├── backend                  # Backend API
    ├── ai-service               # AI service
    └── scheduler                # n8n scheduler
```

## Monitoring and Observability

### Metrics (Prometheus + Grafana)
- **Stack:** Kube-prometheus-stack
- **Namespace:** `monitoring`
- **Components:**
  - Prometheus: Metrics collection
  - Grafana: Visualization and dashboards
  - Alertmanager: Alert routing and notifications
- **Operator Metrics:**
  - CloudNativePG: Built-in Prometheus exporter
  - Redis: Redis-exporter automatically deployed
  - RabbitMQ: Built-in Prometheus plugin

### Logs (Loki)
- **Namespace:** `monitoring`
- **Integration:** Grafana data source
- **Collection:** Promtail agents on all nodes
- **Query Language:** LogQL

### Access
```bash
# Port-forward to Grafana
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80

# Get Grafana admin password
kubectl get secret -n monitoring kube-prometheus-stack-grafana -o jsonpath="{.data.admin-password}" | base64 -d
```

## Notes

- Terraform auto-generates `ansible/inventories/hosts.ini` with `terraform apply`
- Vault password file: `ansible/.vault_pass`
- All Helm charts are local: `helm/`
- Kubespray is vendored (no nested .git)
- Python interpreter is auto-detected
- DigitalOcean CSI driver must be installed before deploying services with persistent volumes
- Operators manage database/cache/queue lifecycle (CloudNativePG, Redis Operator, RabbitMQ Operator)
- Infrastructure instances and applications are deployed via ArgoCD (GitOps)
- Playbooks are fully idempotent - safe to run multiple times
- Architecture follows IaC + GitOps separation (industry best practice)
- All secrets in Git are encrypted using SealedSecrets
- The `target_environment` variable must be provided for environment-specific deployments
