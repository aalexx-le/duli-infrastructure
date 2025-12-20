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
     - Account - Cloudflare Tunnel - Edit
     - Account - Access: Apps and Policies - Edit
     - Zone - Zone - Read
     - Zone - DNS - Edit
     - Zone - Zone Settings - Edit
   - **Account Resources**:
     - Include - [Your Account] - All accounts
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
3. ✅ Stores credentials as Kubernetes Secret
4. ✅ Deploys cloudflared pods (2 replicas)
5. ✅ Configures DNS records (CNAME for HTTPS, Tunnel for TCP)
6. ✅ Sets SSL to Full (Strict)
7. ✅ Enables TLS 1.2+, TLS 1.3, Always HTTPS, Automatic HTTPS Rewrites

---

## Domain Structure

### Application Services (HTTPS via ingress-nginx)

**Production:**
| Domain | Service | Description |
|--------|---------|-------------|
| api.duli.one | backend | Backend API service |
| ai.duli.one | ai-service | AI/ML service |
| n8n.duli.one | scheduler | n8n workflow automation |
| auth.duli.one | keycloak | Authentication (Keycloak) |

**Staging:**
| Domain | Service | Description |
|--------|---------|-------------|
| api.staging.duli.one | backend | Backend API service |
| ai.staging.duli.one | ai-service | AI/ML service |
| n8n.staging.duli.one | scheduler | n8n workflow automation |
| auth.staging.duli.one | keycloak | Authentication (Keycloak) |

### Cluster-Wide Management (HTTPS via ingress-nginx)

| Domain | Service | Description |
|--------|---------|-------------|
| argocd.duli.one | argocd-server | ArgoCD GitOps UI |
| rancher.duli.one | rancher | Rancher cluster management |

### Infrastructure Services (TCP via Cloudflare Tunnel)

**Production:**
| Domain | Service | Port | Protocol |
|--------|---------|------|----------|
| db.duli.one | PostgreSQL | 5432 | TCP |
| redis.duli.one | Redis | 6379 | TCP |
| mq.duli.one | RabbitMQ AMQP | 5672 | TCP |
| queue.duli.one | RabbitMQ Mgmt | 15672 | HTTPS |

**Staging:**
| Domain | Service | Port | Protocol |
|--------|---------|------|----------|
| db.staging.duli.one | PostgreSQL | 5432 | TCP |
| redis.staging.duli.one | Redis | 6379 | TCP |
| mq.staging.duli.one | RabbitMQ AMQP | 5672 | TCP |
| queue.staging.duli.one | RabbitMQ Mgmt | 15672 | HTTPS |

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

# Tunnel credentials are auto-generated and stored in ~/.cloudflared/
# No manual vault configuration needed for tunnel secrets
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

### Automated Setup (Included in Deployment)

Cloudflare Access is **automatically provisioned** by the Ansible playbook. Zero Trust security is configured out-of-the-box with:

- ✅ Access applications for all TCP services (PostgreSQL, Redis, RabbitMQ)
- ✅ Email-based authentication policies
- ✅ 24-hour session duration
- ✅ SSO integration ready (Google, GitHub, Azure AD, Okta)

### For Developers: Accessing Infrastructure Services

Developers can connect directly to infrastructure services using domain names after **enrolling with WARP**.

#### Prerequisites: WARP Client Enrollment (Required)

To access TCP services, you must enroll your device with Cloudflare Zero Trust.

📖 **See detailed guide:** [WARP Enrollment Guide](warp-enrollment-guide.md)

**Quick Enrollment Steps:**

1. **Install WARP client** (if not installed)  
   Download: https://1.1.1.1/

2. **Enroll with your organization:**
   ```bash
   warp-cli registration new <YOUR_TEAM_NAME>
   ```

3. **Authenticate in browser** (engineer.duli@gmail.com or @gmail.com domain)

4. **Verify enrollment:**
   ```bash
   warp-cli registration show
   # Should show your team name and email
   ```

#### Direct Connection (After WARP Enrollment)

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

### Cloudflare WARP Client (Required for TCP Access)

**Important:** WARP client enrollment is **required** to access TCP services (PostgreSQL, Redis, RabbitMQ) directly.

📖 **Complete enrollment guide:** [WARP Enrollment Guide](warp-enrollment-guide.md)

**Why use WARP?**
- ✅ **Required** for direct TCP access to infrastructure services
- ✅ Automatic authentication via Cloudflare Zero Trust
- ✅ Faster connection speeds via Cloudflare's global network
- ✅ Works on mobile devices (iOS, Android)
- ✅ Seamless switching between networks (WiFi, mobile data)
- ✅ Zero Trust security enforced on all connections

#### Installation

**macOS:**
```bash
# Download from Cloudflare
open https://install.appcenter.ms/orgs/cloudflare/apps/1.1.1.1-macos-1/distribution_groups/release

# Or via Homebrew
brew install --cask cloudflare-warp
```

**Windows:**
```powershell
# Download installer
Start-Process "https://install.appcenter.ms/orgs/cloudflare/apps/1.1.1.1-windows-1/distribution_groups/release"
```

**Linux (Ubuntu/Debian):**
```bash
# Add Cloudflare repository
curl https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list

# Install
sudo apt update && sudo apt install cloudflare-warp
```

**iOS/Android:**
- Search for "1.1.1.1: Faster Internet" in App Store/Play Store
- Install and enable WARP

#### Enrollment (Connect to Zero Trust Organization)

**CORRECT COMMAND:**

```bash
# macOS/Linux - Enroll with your organization
warp-cli registration new <YOUR_TEAM_NAME>

# Example (replace with your actual team name):
warp-cli registration new duli-ai

# Browser will open for authentication
# Login with: engineer.duli@gmail.com or any @gmail.com email

# Verify enrollment
warp-cli registration show
# Should display your organization name and email

# Check status
warp-cli status
# Should show: Status: Connected
```

**Or via GUI:**
1. Click WARP icon in menu bar
2. Go to Settings → Preferences → Account
3. Click "Login with Cloudflare Zero Trust"
4. Enter your team name
5. Authenticate in browser

3. **Authenticate**:
   - Enter your company email
   - Complete email verification
   - WARP automatically handles all TCP connections

4. **Verify connection**:
   ```bash
   # Test direct database access (no browser popup!)
   psql -h db.staging.duli.one -p 5432 -U duli_user
   ```

**What happens automatically:**
- ✅ DNS resolves to Cloudflare Tunnel
- ✅ WARP client authenticates via Zero Trust
- ✅ Traffic encrypted end-to-end
- ✅ Connection routed through nearest Cloudflare datacenter
- ✅ Zero Trust security policies applied
- ✅ Works from anywhere (home, office, mobile, airports)

---

#### Legacy Method: kubectl port-forward (Not Recommended)

⚠️ **Deprecated**: Port-forwarding is no longer needed with Cloudflare Access.

This method is only for emergency offline access:

```bash
kubectl port-forward -n staging svc/database-rw 5432:5432
psql -h localhost -p 5432 -U duli_user
```

**Limitations:**
- Requires kubectl access and VPN
- Requires manual setup for each service
- Doesn't work from mobile devices
- No audit logging or SSO authentication

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
# Re-run Cloudflare setup (Tunnel + DNS + SSL)
ansible-playbook -i inventories/hosts.ini playbooks/setup_cloudflare.yml
```

---

## Security Best Practices

### 1. Rotate Credentials

**Tunnel Credentials:**
```bash
# Rotate tunnel credentials
cloudflared tunnel delete duli-tunnel
cloudflared tunnel create duli-tunnel

# Update vault.yml with new credentials
ansible-vault edit inventories/group_vars/all/vault.yml

# Re-deploy cloudflared
ansible-playbook -i inventories/hosts.ini playbooks/setup_cloudflare.yml
```

**API Token:**
```bash
# 1. Create new token at: https://dash.cloudflare.com/profile/api-tokens
# 2. Update vault.yml
ansible-vault edit inventories/group_vars/all/vault.yml
# 3. Re-run setup
ansible-playbook -i inventories/hosts.ini playbooks/setup_cloudflare.yml
```

### 2. Network Isolation

**Kubernetes Network Policies:**

Infrastructure services are protected at multiple layers:

```yaml
# Example: Restrict PostgreSQL access to authorized pods only
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: postgres-access
  namespace: staging
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: cloudflare-system  # Only cloudflared pods
        - podSelector:
            matchLabels:
              app: backend  # Only backend pods
      ports:
        - protocol: TCP
          port: 5432
```

**Zero Trust Principles:**
- ✅ Cloudflared runs in isolated namespace
- ✅ Services not exposed via NodePort/LoadBalancer
- ✅ Direct pod access blocked by network policies
- ✅ All traffic authenticated and encrypted via Cloudflare tunnel

---

## Accessing TCP Services

There are two methods to access TCP services (Database, Redis, RabbitMQ):

### Method 1: Hostname Access (Requires cloudflared)
Requires `cloudflared access tcp` command to bridge the connection. Use this for programmatic access or if you cannot use WARP.

```bash
# Example: Connect to Staging DB
cloudflared access tcp --hostname db.staging.duli.one --url localhost:5432 &
psql -h localhost -p 5432 -U duli_user -d duli_db
```

### Method 2: Direct ClusterIP (Requires WARP)
The simplest method if you have WARP client installed and connected.

1. Connect WARP client
2. Use the **Service ClusterIP** directly (found in `connection-info-staging.ini` or via kubectl)

```bash
# Get ClusterIP
kubectl get svc -n staging database-rw

# Connect directly
psql -h 10.233.x.x -p 5432 -U duli_user -d duli_db
```

> **Note:** Hostname-based access via WARP DNS (e.g. `psql -h db.staging.duli.one`) requires configuring "Local Domain Fallback" or Gateway DNS policies in Cloudflare Zero Trust dashboard, which is not enabled by default.

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
