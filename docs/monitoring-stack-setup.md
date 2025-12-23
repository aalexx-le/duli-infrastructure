# Monitoring Stack Implementation - Complete Setup Guide

## Overview

This document describes the complete monitoring stack implementation using **Grafana + Prometheus + Loki** with best practices for Kubernetes observability.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Monitoring Namespace                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐    ┌──────────────┐│
│  │   Grafana    │─────▶│  Prometheus  │    │     Loki     ││
│  │ (Dashboards) │      │   (Metrics)  │    │    (Logs)    ││
│  └──────────────┘      └──────┬───────┘    └──────┬───────┘│
│         │                     │                    │         │
│         │                     │                    │         │
│         └─────────────────────┴────────────────────┘         │
│                               │                              │
└───────────────────────────────┼──────────────────────────────┘
                                │
                    ┌───────────┴──────────┐
                    │                      │
        ┌───────────▼──────────┐  ┌───────▼──────────┐
        │  Staging Namespace   │  │  Prod Namespace  │
        ├──────────────────────┤  ├──────────────────┤
        │ • Backend            │  │ • Backend        │
        │ • AI Service         │  │ • AI Service     │
        │ • Scheduler          │  │ • Scheduler      │
        │ • PostgreSQL (CNPG)  │  │ • PostgreSQL     │
        │ • Redis              │  │ • Redis          │
        │ • RabbitMQ           │  │ • RabbitMQ       │
        └──────────────────────┘  └──────────────────┘
```

## Components

### 1. **Prometheus** (Metrics Collection)
- **Status**: ✅ ENABLED
- **Purpose**: Collect and store time-series metrics from all services
- **Storage**: 3Gi persistent volume (2-day retention)
- **Scrape Interval**: 120s (optimized for low resource usage)
- **Auto-Discovery**: Enabled for all namespaces (staging, prod, monitoring)

### 2. **Grafana** (Visualization)
- **Status**: ✅ ENABLED
- **Purpose**: Unified dashboard for metrics and logs
- **Persistence**: 1Gi persistent volume
- **Ingress**: `grafana.duli.one` (TLS enabled via cert-manager)
- **Data Sources**: 
  - Prometheus (default)
  - Loki (for logs)

### 3. **Loki** (Log Aggregation)
- **Status**: ✅ ENABLED
- **Purpose**: Centralized log collection from all pods
- **Mode**: SingleBinary (minimal footprint)
- **Storage**: 1Gi persistent volume (24h retention)
- **Gateway**: Internal only (`loki-gateway.monitoring.svc.cluster.local`)

## Exporters Added

### Infrastructure Services

#### 1. **PostgreSQL (CloudNativePG Operator)**
- **Exporter**: Built-in PodMonitor
- **Enabled**: ✅ Yes
- **File Modified**: `helm/cloudnative-pg/values.yaml`
- **Metrics Exposed**: 
  - Database health and replication status
  - Query performance
  - Connection pool statistics
  - Storage utilization

#### 2. **Redis**
- **Exporter**: Built-in Redis metrics
- **ServiceMonitor**: ✅ Created
- **Files Modified**:
  - `helm/redis-instance/values.yaml` (added monitoring config)
  - `helm/redis-instance/templates/servicemonitor.yaml` (created)
  - `helm/redis-instance/templates/_helpers.tpl` (created)
- **Metrics Exposed**:
  - Memory usage
  - Command statistics
  - Replication lag
  - Connected clients

#### 3. **RabbitMQ**
- **Exporter**: Built-in Prometheus plugin
- **ServiceMonitor**: ✅ Created
- **Files Modified**:
  - `helm/rabbitmq/values.yaml` (added monitoring config)
  - `helm/rabbitmq/templates/servicemonitor.yaml` (created)
  - `helm/rabbitmq/templates/_helpers.tpl` (created)
- **Metrics Exposed**:
  - Queue depth
  - Message rates
  - Consumer statistics
  - Node health

### Application Services

#### 4. **Backend**
- **ServiceMonitor**: ✅ Created
- **Files Modified**:
  - `helm/backend/values/defaults.yaml` (added monitoring config)
  - `helm/backend/templates/servicemonitor.yml` (created)
- **Metrics Endpoint**: `/metrics`
- **Application Responsibility**: Expose metrics in Prometheus format

#### 5. **AI Service**
- **ServiceMonitor**: ✅ Created
- **Files Modified**:
  - `helm/ai-service/values/defaults.yaml` (added monitoring config)
  - `helm/ai-service/templates/servicemonitor.yml` (created)
- **Metrics Endpoint**: `/metrics`
- **Application Responsibility**: Expose metrics in Prometheus format

#### 6. **Scheduler (n8n)**
- **ServiceMonitor**: ✅ Created
- **Files Modified**:
  - `helm/scheduler/values/defaults.yaml` (added monitoring config)
  - `helm/scheduler/templates/servicemonitor.yml` (created)
- **Metrics Endpoint**: `/metrics`
- **Note**: n8n has built-in Prometheus metrics support

## Files Modified Summary

### Core Monitoring Stack
```
helm/kube-prometheus-stack/values-monitoring.yaml
  - Prometheus: enabled: true
  - Grafana: enabled with Loki datasource
  - Alert Manager: enabled
```

### Infrastructure Services
```
helm/cloudnative-pg/values.yaml
  - monitoring.podMonitorEnabled: true

helm/redis-instance/
  - values.yaml (added monitoring section)
  - templates/servicemonitor.yaml (created)
  - templates/_helpers.tpl (created)

helm/rabbitmq/
  - values.yaml (added monitoring section)
  - templates/servicemonitor.yaml (created)
  - templates/_helpers.tpl (created)
```

### Application Services
```
helm/backend/
  - values/defaults.yaml (added monitoring section)
  - templates/servicemonitor.yml (created)

helm/ai-service/
  - values/defaults.yaml (added monitoring section)
  - templates/servicemonitor.yml (created)

helm/scheduler/
  - values/defaults.yaml (added monitoring section)
  - templates/servicemonitor.yml (created)
```

## Configuration Details

### Prometheus Discovery
Prometheus is configured to automatically discover all ServiceMonitors and PodMonitors across all namespaces:

```yaml
prometheus:
  prometheusSpec:
    serviceMonitorSelectorNilUsesHelmValues: false
    podMonitorSelectorNilUsesHelmValues: false
    serviceMonitorNamespaceSelector: {}
    podMonitorNamespaceSelector: {}
```

### Monitoring Configuration Pattern
All services follow this standardized pattern in `values.yaml`:

```yaml
monitoring:
  enabled: true
  interval: 30s              # How often to scrape metrics
  scrapeTimeout: 10s         # Timeout for scrape requests
  metricsPath: /metrics      # Endpoint path (for apps)
  additionalLabels: {}       # Extra labels for ServiceMonitor
  metricRelabelings: []      # Metric transformation rules
  relabelings: []            # Label transformation rules
```

## Deployment via ArgoCD

The monitoring stack is deployed via ArgoCD GitOps:

```
ansible/playbooks/install_infrastructures.yml
  ├─ Creates monitoring namespace
  ├─ Creates Grafana admin secret
  ├─ Creates Cloudflare API token secret
  └─ Deploys ArgoCD Applications:
      ├─ kube-prometheus-stack (sync-wave: 1)
      └─ loki (sync-wave: 2)
```

ArgoCD Application templates:
- `gitops/applications/kube-prometheus-stack.yml.j2`
- `gitops/applications/loki.yml.j2`

## Access and Usage

### Grafana Dashboard
- **URL**: https://grafana.duli.one
- **Username**: admin
- **Password**: Stored in `vault_grafana_admin_password` (Ansible Vault)
- **TLS**: Automatic via cert-manager with Let's Encrypt

### Default Dashboards Included
1. **Kubernetes Cluster Overview** - Node/pod resources
2. **PostgreSQL Dashboard** - Database metrics (from CNPG)
3. **Redis Dashboard** - Cache performance
4. **RabbitMQ Dashboard** - Message queue metrics
5. **Application Metrics** - Custom app metrics
6. **Logs Explorer** - Loki log viewer

## Best Practices Implemented

### 1. **Namespace Isolation**
- Monitoring stack in dedicated `monitoring` namespace
- Metrics collected from all namespaces (staging, prod)
- Clear separation of concerns

### 2. **Resource Optimization**
- Prometheus: 2-day retention (3Gi storage)
- Loki: 24h retention (1Gi storage)
- Reduced scrape intervals (120s for Prometheus)
- Minimal resource requests/limits

### 3. **Auto-Discovery**
- ServiceMonitors automatically discovered by Prometheus
- No manual configuration needed for new services
- Label-based service selection

### 4. **GitOps Workflow**
- All configuration in Git
- ArgoCD auto-sync enabled
- Changes tracked in version control

### 5. **High Availability Ready**
- All components support HA configuration
- Persistent storage for data retention
- Ingress configured for external access

## Application Requirements

For application services (backend, ai-service, scheduler) to be monitored, they must:

1. **Expose Prometheus Metrics** at `/metrics` endpoint
2. **Return metrics in Prometheus format**:
   ```
   # HELP http_requests_total Total HTTP requests
   # TYPE http_requests_total counter
   http_requests_total{method="GET",status="200"} 1234
   ```

### Example Implementation (Node.js/Express)
```javascript
const promClient = require('prom-client');
const register = new promClient.Registry();

// Create metrics
const httpRequestDuration = new promClient.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status'],
});
register.registerMetric(httpRequestDuration);

// Expose /metrics endpoint
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});
```

### Example Implementation (Python/FastAPI)
```python
from prometheus_client import Counter, generate_latest, REGISTRY

# Create metrics
http_requests = Counter('http_requests_total', 'Total HTTP requests',
                        ['method', 'endpoint', 'status'])

# Expose /metrics endpoint
@app.get("/metrics")
async def metrics():
    return Response(generate_latest(REGISTRY), media_type="text/plain")
```

## Verification Steps

After deployment, verify the monitoring stack:

```bash
# 1. Check monitoring namespace
kubectl get all -n monitoring

# 2. Check Prometheus targets
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090
# Open: http://localhost:9090/targets

# 3. Check ServiceMonitors
kubectl get servicemonitors -A

# 4. Check PodMonitors
kubectl get podmonitors -A

# 5. Access Grafana
# Open: https://grafana.duli.one

# 6. Check Loki is receiving logs
kubectl port-forward -n monitoring svc/loki-gateway 3100:80
curl http://localhost:3100/ready
```

## Troubleshooting

### Prometheus Not Scraping Metrics
```bash
# Check if ServiceMonitor exists
kubectl get servicemonitor -n <namespace>

# Check if target is visible in Prometheus
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090
# Visit: http://localhost:9090/targets

# Check Prometheus logs
kubectl logs -n monitoring -l app.kubernetes.io/name=prometheus
```

### Grafana Not Showing Data
```bash
# Check Grafana datasources
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
# Visit: http://localhost:3000/datasources

# Check if Prometheus datasource is healthy
# Visit: Configuration > Data Sources > Prometheus > Test
```

### Loki Not Receiving Logs
```bash
# Check Loki status
kubectl get pods -n monitoring -l app.kubernetes.io/name=loki

# Check Loki logs
kubectl logs -n monitoring -l app.kubernetes.io/component=single-binary

# Test Loki query
kubectl port-forward -n monitoring svc/loki-gateway 3100:80
curl http://localhost:3100/loki/api/v1/labels
```

## Cost Optimization

Current configuration is optimized for minimal resource usage:

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit | Storage |
|-----------|-------------|-----------|----------------|--------------|---------|
| Prometheus | 30m | 150m | 192Mi | 384Mi | 3Gi |
| Grafana | 15m | 75m | 48Mi | 96Mi | 1Gi |
| Loki | 30m | 150m | 96Mi | 192Mi | 1Gi |
| Alertmanager | 5m | 30m | 24Mi | 48Mi | 500Mi |

**Total Additional Resources Required**:
- CPU: ~80m request, ~400m limit
- Memory: ~360Mi request, ~720Mi limit
- Storage: ~5.5Gi

## Next Steps

1. **Deploy the changes**:
   ```bash
   git add .
   git commit -m "Enable monitoring stack with exporters for all services"
   git push origin main
   ```

2. **Wait for ArgoCD sync** (automatic within 3 minutes)

3. **Access Grafana** at https://grafana.duli.one

4. **Import custom dashboards** (optional)

5. **Configure alerts** in Alertmanager (optional)

6. **Update application code** to expose `/metrics` endpoints

## References

- [Prometheus Operator](https://prometheus-operator.dev/)
- [Grafana Loki](https://grafana.com/oss/loki/)
- [kube-prometheus-stack Chart](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
- [CloudNativePG Monitoring](https://cloudnative-pg.io/documentation/current/monitoring/)
- [Prometheus Client Libraries](https://prometheus.io/docs/instrumenting/clientlibs/)
