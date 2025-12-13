# Cloudflare Configuration Guide

Complete guide for setting up Cloudflare DNS, SSL/TLS, and Zero Trust Tunnels for secure access to Kubernetes services.

**All configuration is automated via Ansible** - only initial API token and account setup required.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Domain Structure](#domain-structure)
5. [Cloudflare Tunnel Setup](#cloudflare-tunnel-setup)
6. [DNS and SSL Configuration](#dns-and-ssl-configuration)
7. [Access Configuration](#access-configuration)
8. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```mermaid
graph TB
    subgraph Internet["🌐 Internet Users"]
        USER1[Developer]
        USER2[End User]
    end
    
    subgraph Cloudflare["☁️ Cloudflare Edge Network"]
        DNS[DNS Resolution<br/>duli.one]
        SSL[SSL/TLS Proxy<br/>Full Strict]
        TUNNEL[Zero Trust Tunnel<br/>TCP/UDP Support]
    end
    
    subgraph Kubernetes["⎈ Kubernetes Cluster"]
        subgraph Ingress["HTTPS Traffic Handler"]
            LB[ingress-nginx<br/>LoadBalancer]
        end
        
        subgraph CloudflaredPods["TCP Traffic Handler"]
            CF1[cloudflared<br/>replica 1]
            CF2[cloudflared<br/>replica 2]
        end
        
        subgraph AppServices["Application Services"]
            BACKEND[Backend API]
            AI[AI Service]
            SCHEDULER[Scheduler]
            KEYCLOAK[Keycloak]
        end
        
        subgraph MgmtUIs["Management UIs"]
            RABBITMQ_UI[RabbitMQ UI]
            ARGOCD[ArgoCD]
            RANCHER[Rancher]
        end
        
        subgraph InfraServices["Infrastructure Services"]
            POSTGRES[(PostgreSQL)]
            REDIS[(Redis)]
            RABBITMQ[(RabbitMQ AMQP)]
        end
    end
    
    USER2 -->|HTTPS| DNS
    DNS --> SSL
    SSL -->|Proxied| LB
    LB --> AppServices
    LB --> MgmtUIs
    
    USER1 -->|WARP Client| TUNNEL
    TUNNEL -->|Encrypted| CF1
    TUNNEL -->|Encrypted| CF2
    CF1 --> InfraServices
    CF2 --> InfraServices
    
    classDef cloudflare fill:#f96,stroke:#333,color:#000
    classDef kubernetes fill:#326ce5,stroke:#333,color:#fff
    classDef app fill:#4caf50,stroke:#333,color:#fff
    classDef infra fill:#ff9800,stroke:#333,color:#000
    
    class DNS,SSL,TUNNEL cloudflare
    class LB,CF1,CF2 kubernetes
    class BACKEND,AI,SCHEDULER,KEYCLOAK,RABBITMQ_UI,ARGOCD,RANCHER app
    class POSTGRES,REDIS,RABBITMQ infra
```

### Traffic Flow

**HTTPS Services (via ingress-nginx):**
```
User → Cloudflare (Orange Cloud) → LoadBalancer → ingress-nginx → Service
```

**TCP Services (via Cloudflare Tunnel):**
```
User → WARP Client → Cloudflare Tunnel → cloudflared Pod → Service
```

---

## Prerequisites

### 1. Domain Setup

1. **Register domain** `duli.one` (already done)
2. **Add domain to Cloudflare**:
   - Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
   - Click **Add a Site**
   - Enter `duli.one`
   - Choose Free plan
3. **Update nameservers**:
   - Cloudflare will provide 2 nameservers (e.g., `ns1.cloudflare.com`, `ns2.cloudflare.com`)
   - Update nameservers at your domain registrar
   - Wait for DNS propagation (up to 24 hours, usually ~10 minutes)

### 2. Cloudflare API Token

Create an API token with the following permissions:

1. Go to [API Tokens](https://dash.cloudflare.com/profile/api-tokens)
2. Click **Create Token**
3. Select **Create Custom Token**
4. Configure:
   - **Token name**: `duli-k8s-automation`
   - **Permissions**:
     - Zone - Zone - Read
     - Zone - DNS - Edit
     - Zone - Zone Settings - Edit
   - **Zone Resources**:
     - Include - Specific zone - `duli.one`
5. Click **Continue to summary** → **Create Token**
6. **Copy the token** (shown only once!)

### 3. Cloudflare Account ID

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Select your account (top-right)
3. Copy the **Account ID** from the right sidebar

---

## Quick Start

### Step 1: Configure Ansible Vault

```bash
cd infrastructure-kubernetes/ansible

# Edit vault file
ansible-vault edit inventories/group_vars/all/vault.yml

# Add your credentials:
vault_cloudflare_api_token: "your-api-token-here"
vault_cloudflare_account_id: "your-account-id-here"
```

### Step 2: Deploy Everything

```bash
# Full deployment (creates tunnel automatically)
ansible-playbook -i inventories/hosts.ini playbooks/site.yml

# Or run Cloudflare setup separately
ansible-playbook -i inventories/hosts.ini playbooks/setup_cloudflare.yml
```

**What happens automatically:**
1. ✅ Creates Cloudflare Tunnel (`duli-tunnel`)
2. ✅ Generates tunnel credentials
3. ✅ Stores credentials in Ansible Vault
4. ✅ Deploys cloudflared pods (2 replicas)
5. ✅ Configures DNS records
6. ✅ Sets SSL to Full (Strict)
7. ✅ Enables security features

---

## Domain Structure

### Application Services (HTTPS)

| Domain | Service | Type | Description |
|--------|---------|------|-------------|
| api.duli.one | backend | HTTPS | Backend API service |
| ai.duli.one | ai-service | HTTPS | AI/ML service |
| n8n.duli.one | scheduler | HTTPS | n8n workflow automation |
| auth.duli.one | keycloak | HTTPS | Authentication (Keycloak) |
| argocd.duli.one | argocd-server | HTTPS | ArgoCD GitOps UI |
| rancher.duli.one | rancher | HTTPS | Rancher cluster management |

### Infrastructure Services (TCP via Tunnel)

**Production:**
| Domain | Service | Port | Protocol |
|--------|---------|------|----------|
| db.duli.one | PostgreSQL | 5432 | TCP |
| redis.duli.one | Redis | 6379 | TCP |
| mq.duli.one | RabbitMQ AMQP | 5672 | TCP |

**Staging:**
| Domain | Service | Port | Protocol |
|--------|---------|------|----------|
| db.staging.duli.one | PostgreSQL | 5432 | TCP |
| redis.staging.duli.one | Redis | 6379 | TCP |
| mq.staging.duli.one | RabbitMQ AMQP | 5672 | TCP |

### Management UIs (HTTPS)

| Domain | Service | Description |
|--------|---------|-------------|
| queue.duli.one | RabbitMQ Mgmt | Production management UI |
| queue.staging.duli.one | RabbitMQ Mgmt | Staging management UI |

---

## Cloudflare Tunnel Setup

### Automatic Provisioning (Recommended)

Ansible automatically creates and configures the tunnel. **No manual steps required!**

The playbook:
1. Checks if tunnel exists
2. Creates tunnel if not found
3. Stores credentials in vault
4. Deploys cloudflared to cluster

### Manual Tunnel Creation (Advanced)

Only needed if automatic provisioning fails:

```bash
# Install cloudflared CLI
brew install cloudflare/cloudflare/cloudflared  # macOS
# OR
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb  # Linux

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create duli-tunnel

# List tunnels to get ID
cloudflared tunnel list

# Add credentials to vault
ansible-vault edit inventories/group_vars/all/vault.yml
# Add:
# vault_cloudflare_tunnel_id: "your-tunnel-uuid"
# vault_cloudflare_tunnel_secret: "your-tunnel-secret"
```

---

## DNS and SSL Configuration

### DNS Records (Auto-configured)

Ansible creates these DNS records automatically:

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| A | @ | `<LoadBalancer IP>` | 🟠 Proxied |
| CNAME | api | duli.one | 🟠 Proxied |
| CNAME | ai | duli.one | 🟠 Proxied |
| CNAME | n8n | duli.one | 🟠 Proxied |
| CNAME | auth | duli.one | 🟠 Proxied |
| CNAME | argocd | duli.one | 🟠 Proxied |
| CNAME | rancher | duli.one | 🟠 Proxied |
| CNAME | queue | duli.one | 🟠 Proxied |
| CNAME | queue.staging | duli.one | 🟠 Proxied |

**Note:** Infrastructure service DNS (db, redis, mq) is managed by Cloudflare Tunnel, not DNS records.

### SSL/TLS Settings (Auto-configured)

Ansible configures:

- ✅ **SSL Mode**: Full (Strict)
- ✅ **Always Use HTTPS**: Enabled
- ✅ **Minimum TLS**: 1.2
- ✅ **TLS 1.3**: Enabled
- ✅ **Automatic HTTPS Rewrites**: Enabled
- ✅ **HSTS**: Enabled (max-age: 31536000)

---

## Access Configuration

### For Developers: Accessing Infrastructure Services

Developers can connect directly to infrastructure services using domain names - **no commands, no port-forwarding, just connect!**

#### Direct Connection (Zero Manual Steps)

**PostgreSQL (Staging):**
```bash
psql -h db.staging.duli.one -p 5432 -U duli_user
```

**PostgreSQL (Production):**
```bash
psql -h db.duli.one -p 5432 -U duli_user
```

**Redis (Staging):**
```bash
redis-cli -h redis.staging.duli.one -p 6379 -a <password>
```

**RabbitMQ (Staging):**
```bash
# AMQP connection
amqp://user:pass@mq.staging.duli.one:5672

# Management UI
https://queue.staging.duli.one
```

#### How It Works

1. **First-time setup** (automatic, browser-based):
   - Visit any infrastructure domain (e.g., `db.staging.duli.one`)
   - Cloudflare Access shows login page
   - Authenticate with Google/GitHub (SSO)
   - Access granted automatically

2. **After authentication**:
   - All infrastructure services accessible via domains
   - No VPN, no port-forwarding, no commands
   - Works from anywhere (home, office, mobile)

3. **Cloudflare WARP** (optional, for better performance):
   - Install once: [WARP Client](https://developers.cloudflare.com/cloudflare-one/connections/connect-devices/warp/)
   - Automatic background connection
   - Faster than browser-based auth

**What happens automatically:**
- ✅ DNS resolves to Cloudflare Tunnel
- ✅ Cloudflare authenticates via SSO
- ✅ Traffic encrypted end-to-end
- ✅ Connection routed to Kubernetes service
- ✅ Zero Trust security applied

---

#### Alternative: kubectl port-forward (No Internet Required)

If you need offline access or prefer traditional approach:

```bash
kubectl port-forward -n staging svc/database-rw 5432:5432
psql -h localhost -p 5432 -U duli_user
```

---

## Troubleshooting

### Tunnel Not Connecting

```bash
# Check cloudflared pods
kubectl get pods -l app.kubernetes.io/name=cloudflare-tunnel

# Check logs
kubectl logs -l app.kubernetes.io/name=cloudflare-tunnel

# Check tunnel status
kubectl exec -it <cloudflared-pod> -- cloudflared tunnel info
```

### DNS Not Resolving

```bash
# Verify DNS records
dig api.duli.one
nslookup db.staging.duli.one

# Check Cloudflare dashboard
# Go to DNS → Records
```

### SSL Certificate Issues

```bash
# Check cert-manager
kubectl get certificates -A
kubectl describe certificate <cert-name>

# Check certificate issuer
kubectl get clusterissuer
```

### Connection Refused

1. **For HTTPS services**: Check ingress-nginx
   ```bash
   kubectl get ingress -A
   kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
   ```

2. **For TCP services**: Check cloudflared
   ```bash
   kubectl logs -l app.kubernetes.io/name=cloudflare-tunnel
   ```

### Re-run Configuration

```bash
# Re-run Cloudflare DNS/SSL setup
ansible-playbook -i inventories/hosts.ini playbooks/configure_cloudflare.yml

# Re-deploy cloudflared
ansible-playbook -i inventories/hosts.ini playbooks/install_cloudflared.yml
```

---

## Security Best Practices

### 1. Access Policies

Configure Cloudflare Access policies to restrict who can access infrastructure services:

1. Go to [Cloudflare Zero Trust](https://one.dash.cloudflare.com)
2. **Access** → **Applications** → **Add an application**
3. Configure:
   - **Application name**: PostgreSQL Staging
   - **Application domain**: `db.staging.duli.one`
   - **Policy**: Allow emails from `@yourcompany.com`

### 2. Audit Logs

Monitor access in Cloudflare:
- **Zero Trust** → **Logs** → **Access**

### 3. Rotate Credentials

```bash
# Rotate tunnel credentials
cloudflared tunnel delete duli-tunnel
cloudflared tunnel create duli-tunnel
# Update vault.yml with new credentials
ansible-vault edit inventories/group_vars/all/vault.yml
```

---

## Deployment Order (Automated)

The `site.yml` playbook runs in this order:

```yaml
1. kubespray.yml                    # Kubernetes cluster
2. do_csi_driver.yml                # DigitalOcean CSI
3. do_cloud_controller_manager.yml  # DigitalOcean CCM
4. install_infrastructures.yml      # Cert-Manager, operators
5. setup_cloudflare.yml             # Tunnel + DNS + SSL (ALL IN ONE)
6. generate_sealed_secrets.yml      # Sealed secrets
7. deploy_applications.yml          # Applications
8. export_connection.yml            # Connection info
```

---

## Additional Resources

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Cloudflare Zero Trust](https://developers.cloudflare.com/cloudflare-one/)
- [Kubernetes Deployment Guide](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/deployment-guides/kubernetes/)
- [WARP Client Setup](https://developers.cloudflare.com/cloudflare-one/connections/connect-devices/warp/)
