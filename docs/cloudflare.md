# Cloudflare DNS and SSL Configuration Guide

Complete guide for managing Cloudflare DNS records and SSL/TLS settings for external access to Kubernetes services.

**All configuration is automated via Ansible** - only initial API token setup required.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Domain Structure](#domain-structure)
5. [DNS Records](#dns-records)
6. [SSL/TLS Configuration](#ssltls-configuration)
7. [Service Access](#service-access)
8. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```mermaid
graph TB
    subgraph Internet["🌐 Internet Users"]
        DEV["Developers<br/>Tools<br/>CI/CD"]
        ENDUSER["End Users"]
    end
    
    subgraph Cloudflare["☁️ Cloudflare"]
        DNS["DNS Resolution<br/>duli.one"]
        SSL["SSL/TLS Proxy<br/>Full Strict"]
    end
    
    subgraph Kubernetes["⎈ Kubernetes Cluster"]
        subgraph LoadBalancer["Single LoadBalancer Service"]
            LB["ingress-nginx<br/>Port 80, 443, 5432-5673"]
        end
        
        subgraph HTTP["HTTP/HTTPS Traffic"]
            INGRESS["ingress-nginx Controller"]
        end
        
        subgraph TCP["TCP Traffic Passthrough"]
            TCPROUTE["TCP Router"]
        end
        
        subgraph AppServices["Application Services"]
            BACKEND["Backend API"]
            AI["AI Service"]
            SCHEDULER["Scheduler"]
        end
        
        subgraph InfraServices["Infrastructure Services"]
            POSTGRES[("PostgreSQL<br/>staging & prod")]
            REDIS[("Redis<br/>staging & prod")]
            RABBITMQ[("RabbitMQ<br/>staging & prod")]
        end
    end
    
    ENDUSER -->|HTTPS<br/>api.duli.one| DNS
    DNS --> SSL
    SSL -->|Port 443| LB
    LB --> INGRESS
    INGRESS --> AppServices
    
    DEV -->|TCP<br/>db-staging.duli.one:5432| DNS
    DNS -->|Port 5432-5673| LB
    LB --> TCPROUTE
    TCPROUTE --> InfraServices
    
    classDef cf fill:#f96,stroke:#333,color:#000
    classDef k8s fill:#326ce5,stroke:#333,color:#fff
    classDef app fill:#4caf50,stroke:#333,color:#fff
    classDef infra fill:#ff9800,stroke:#333,color:#000
    
    class Cloudflare,DNS,SSL cf
    class Kubernetes,LoadBalancer,HTTP,TCP,INGRESS,TCPROUTE k8s
    class AppServices,BACKEND,AI,SCHEDULER app
    class InfraServices,POSTGRES,REDIS,RABBITMQ infra
```

### Traffic Flow

**HTTPS Services (Applications):**
```
User → Cloudflare DNS → SSL Proxy → LoadBalancer (port 443) → ingress-nginx → Service
```

**TCP Services (Infrastructure):**
```
Developer → Cloudflare DNS → LoadBalancer (ports 5432-5673) → ingress-nginx TCP Router → Service
```

---

## Prerequisites

### 1. Domain Setup

1. Register domain `duli.one`
2. Add domain to Cloudflare:
   - Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
   - Click "Add a Site"
   - Enter `duli.one`
   - Update nameservers at your registrar
   - Wait for DNS propagation (typically 10-30 minutes)

### 2. Cloudflare API Token

Create an API token with these permissions:

1. Go to [API Tokens](https://dash.cloudflare.com/profile/api-tokens)
2. Click "Create Token" → "Create Custom Token"
3. Configure:
   - **Permissions**:
     - Zone - DNS - Edit
     - Zone - Zone - Read
     - Zone - Zone Settings - Edit
   - **Zone Resources**: Include - Specific zone - `duli.one`
4. Copy the token (shown only once!)

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

### Step 2: Deploy

```bash
# Full deployment (includes DNS setup)
ansible-playbook -i inventories/hosts.ini playbooks/site.yml

# Or run DNS setup separately
ansible-playbook -i inventories/hosts.ini playbooks/setup_dns.yml -e target_environment=staging
ansible-playbook -i inventories/hosts.ini playbooks/setup_dns.yml -e target_environment=prod
```

**What happens automatically:**
1. Creates A record for root domain (duli.one)
2. Creates A records for HTTP services (api-staging, ai-staging, etc.)
3. Creates A records for TCP services (db-staging, redis-staging, mq-staging, etc.)
4. Sets SSL mode to Full (Strict)
5. Enables TLS 1.2+, TLS 1.3
6. Enables Always Use HTTPS
7. Enables Automatic HTTPS Rewrites

---

## Domain Structure

### HTTP/HTTPS Services (Proxied via Cloudflare)

**Staging:**
| Domain | Service | Port |
|--------|---------|------|
| api-staging.duli.one | Backend API | 443 |
| ai-staging.duli.one | AI Service | 443 |
| n8n-staging.duli.one | Scheduler | 443 |
| auth-staging.duli.one | Keycloak | 443 |
| queue-staging.duli.one | RabbitMQ UI | 443 |

**Production:**
| Domain | Service | Port |
|--------|---------|------|
| api.duli.one | Backend API | 443 |
| ai.duli.one | AI Service | 443 |
| n8n.duli.one | Scheduler | 443 |
| auth.duli.one | Keycloak | 443 |
| queue.duli.one | RabbitMQ UI | 443 |

**Cluster Management:**
| Domain | Service | Port |
|--------|---------|------|
| argocd.duli.one | ArgoCD | 443 |
| rancher.duli.one | Rancher | 443 |

### TCP Services (Direct via LoadBalancer)

**Staging:**
| Domain | Service | Port | Protocol |
|--------|---------|------|----------|
| db-staging.duli.one | PostgreSQL | 5432 | TCP |
| redis-staging.duli.one | Redis | 6379 | TCP |
| mq-staging.duli.one | RabbitMQ | 5672 | TCP |

**Production:**
| Domain | Service | Port | Protocol |
|--------|---------|------|----------|
| db.duli.one | PostgreSQL | 5433 | TCP |
| redis.duli.one | Redis | 6380 | TCP |
| mq.duli.one | RabbitMQ | 5673 | TCP |

---

## DNS Records

### Auto-generated A Records

DNS records are automatically created and point to the LoadBalancer IP:

**Root Domain:**
- `duli.one` → LoadBalancer IP (proxied via Cloudflare)

**HTTP Services:**
- `api-staging.duli.one` → LoadBalancer IP (proxied)
- `ai-staging.duli.one` → LoadBalancer IP (proxied)
- `n8n-staging.duli.one` → LoadBalancer IP (proxied)
- `auth-staging.duli.one` → LoadBalancer IP (proxied)
- `queue-staging.duli.one` → LoadBalancer IP (proxied)
- `api.duli.one` → LoadBalancer IP (proxied)
- `ai.duli.one` → LoadBalancer IP (proxied)
- `n8n.duli.one` → LoadBalancer IP (proxied)
- `auth.duli.one` → LoadBalancer IP (proxied)
- `queue.duli.one` → LoadBalancer IP (proxied)

**Management Services:**
- `argocd.duli.one` → LoadBalancer IP (proxied)
- `rancher.duli.one` → LoadBalancer IP (proxied)

**TCP Services (Unproxied):**
- `db-staging.duli.one` → LoadBalancer IP (unproxied)
- `redis-staging.duli.one` → LoadBalancer IP (unproxied)
- `mq-staging.duli.one` → LoadBalancer IP (unproxied)
- `db.duli.one` → LoadBalancer IP (unproxied)
- `redis.duli.one` → LoadBalancer IP (unproxied)
- `mq.duli.one` → LoadBalancer IP (unproxied)

---

## SSL/TLS Configuration

### Automatic Configuration

The following SSL/TLS settings are automatically configured:

- **SSL Mode**: Full (Strict) - Validates certificate on origin server
- **Always Use HTTPS**: Enabled - Redirects all HTTP to HTTPS
- **Minimum TLS Version**: 1.2
- **TLS 1.3**: Enabled
- **Automatic HTTPS Rewrites**: Enabled - Rewrites links to HTTPS
- **HSTS**: Enabled with max-age: 31536000 seconds

### Certificate Management

Certificates are managed by:
1. **Cloudflare**: Manages certificates for domains proxied through Cloudflare
2. **Cert-Manager**: Manages certificates for internal services (via LetsEncrypt)

---

## Service Access

### Internal Access (Applications Inside Cluster)

Applications inside the cluster connect to infrastructure services using internal Kubernetes service names:

```
PostgreSQL: database-rw.{namespace}.svc.cluster.local:5432
Redis: redis-master.{namespace}.svc.cluster.local:6379
RabbitMQ: queue.{namespace}.svc.cluster.local:5672
```

Replace `{namespace}` with `staging` or `prod`.

### External Access (Developers and Tools)

#### HTTP/HTTPS Services

Access via standard HTTPS:

```bash
# Staging
curl https://api-staging.duli.one
curl https://ai-staging.duli.one
curl https://n8n-staging.duli.one

# Production
curl https://api.duli.one
curl https://ai.duli.one
curl https://n8n.duli.one
```

#### TCP Services

Connect using public domains and configured ports:

**PostgreSQL:**
```bash
# Staging
psql -h db-staging.duli.one -p 5432 -U duli_user -d duli_db

# Production
psql -h db.duli.one -p 5433 -U duli_user -d duli_db
```

**Redis:**
```bash
# Staging
redis-cli -h redis-staging.duli.one -p 6379

# Production
redis-cli -h redis.duli.one -p 6380
```

**RabbitMQ:**
```bash
# Staging
amqp://user:password@mq-staging.duli.one:5672

# Production
amqp://user:password@mq.duli.one:5673
```

---

## Troubleshooting

### DNS Not Resolving

Check DNS propagation:

```bash
# Verify DNS records
dig duli.one
nslookup api-staging.duli.one

# Check Cloudflare dashboard
# Go to DNS → Records to verify records exist
```

### SSL Certificate Issues

Check certificate configuration:

```bash
# Verify certificate
openssl s_client -connect api-staging.duli.one:443

# Check cert-manager status
kubectl get certificates -A
kubectl describe certificate <cert-name> -n <namespace>
```

### Connection Refused

Check ingress-nginx and LoadBalancer:

```bash
# Verify LoadBalancer IP
kubectl get svc -n ingress-nginx ingress-nginx

# Check ingress configuration
kubectl get ingress -A

# Check ingress-nginx logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
```

### TCP Port Not Accessible

Check TCP port configuration:

```bash
# Verify TCP ports are exposed
kubectl get svc -n ingress-nginx ingress-nginx -o yaml | grep -A 20 ports

# Test connection
nc -zv db-staging.duli.one 5432
```

### Re-run Configuration

To reapply DNS and SSL configuration:

```bash
ansible-playbook -i inventories/hosts.ini playbooks/setup_dns.yml -e target_environment=staging
ansible-playbook -i inventories/hosts.ini playbooks/setup_dns.yml -e target_environment=prod
```

---

## Additional Resources

- [Cloudflare DNS Management](https://developers.cloudflare.com/dns/manage-dns-records/)
- [Cloudflare SSL/TLS](https://developers.cloudflare.com/ssl/)
- [Kubernetes Ingress Documentation](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
