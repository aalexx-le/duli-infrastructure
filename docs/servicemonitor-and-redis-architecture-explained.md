# ServiceMonitor Explained & Redis Operator Architecture

## Why Do We Need ServiceMonitor?

### The Problem ServiceMonitor Solves

Without ServiceMonitor, you would need to:
1. **Manually configure Prometheus** with static scrape targets
2. **Update Prometheus config** every time you add/remove Redis instances
3. **Restart Prometheus** to pick up configuration changes
4. **Maintain separate configs** for each environment (staging, prod)

This is **painful and error-prone** in dynamic Kubernetes environments where services scale up/down.

### ServiceMonitor is the Solution

ServiceMonitor is a **Custom Resource Definition (CRD)** from **Prometheus Operator** that enables **automatic service discovery**:

```
┌─────────────────────────────────────────────────────────────┐
│                    Without ServiceMonitor                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Redis Pod 1 ─┐                                             │
│  Redis Pod 2 ─┼──▶ You manually add each IP/port           │
│  Redis Pod 3 ─┘    to Prometheus config (static)            │
│                                                               │
│  Problem: Pods restart → IPs change → Config breaks         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     With ServiceMonitor                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ServiceMonitor ─▶ Prometheus Operator ─▶ Auto-discovers   │
│  (label selector)  (watches)              all matching pods  │
│                                                               │
│  Benefit: Pods scale/restart → Prometheus auto-updates      │
└─────────────────────────────────────────────────────────────┘
```

**Key Benefits**:
- ✅ **Declarative**: Define monitoring as Kubernetes YAML
- ✅ **Dynamic**: Automatically discovers new pods/services
- ✅ **No manual config**: Prometheus Operator handles everything
- ✅ **GitOps-friendly**: Version controlled alongside your apps

---

## Redis Operator vs Redis Instance Architecture

You have **two separate components** in your infrastructure:

### 1. **Redis Operator** (Cluster-scoped)

**What it is**: A Kubernetes **controller** that watches for Redis Custom Resources

**Location**: `redis-operator-system` namespace (deployed once per cluster)

**Purpose**: 
- Watches for `Redis` and `RedisCluster` Custom Resources
- Creates/manages StatefulSets, Services, ConfigMaps for Redis instances
- Handles Redis failover, cluster operations

**Does it need monitoring?**: 
- ❌ **No exporter needed** - The operator itself is just a controller
- ⚠️ You could monitor the operator pod's health (optional), but it doesn't expose Redis metrics

**Deployed by**:
```yaml
# gitops/applications/redis-operator.yml.j2
source:
  repoURL: https://ot-container-kit.github.io/helm-charts
  chart: redis-operator
destination:
  namespace: redis-operator-system  # Operator runs here
```

---

### 2. **Redis Instance** (Per-namespace)

**What it is**: A **Custom Resource** (CR) that tells the operator to create a Redis deployment

**Location**: Each environment namespace (`staging`, `prod`)

**Purpose**: 
- Defines the desired Redis setup (replication, cluster, standalone)
- Operator reads this and creates the actual Redis pods

**Does it need monitoring?**: 
- ✅ **YES** - Each Redis instance needs `redis-exporter` sidecar
- ✅ **YES** - Each instance needs its own ServiceMonitor

**Deployed by**:
```yaml
# gitops/applications/redis-instance.yml.j2
source:
  path: helm/redis-instance  # Your custom chart
destination:
  namespace: "{{ target_env }}"  # staging or prod
```

---

## Where to Add Redis Exporter?

### ✅ Correct Answer: Add Exporter in **Redis Instance** (not Operator)

From official OT-Container-Kit documentation:

> "The redis-operator uses redis-exporter to expose metrics of redis setup in Prometheus format. This exporter captures metrics for both redis standalone and cluster setup."

### How Redis Exporter is Deployed

The exporter runs as a **sidecar container** in the Redis pod:

```
┌───────────────────────────────────────────────────────┐
│             Redis Pod (StatefulSet)                    │
├───────────────────────────────────────────────────────┤
│                                                        │
│  ┌─────────────────┐    ┌───────────────────────┐   │
│  │  redis:7.0      │    │  redis-exporter:1.0   │   │
│  │  (port 6379)    │◀───│  (port 9121/metrics)  │   │
│  │                 │    │                       │   │
│  │  Main Container │    │  Sidecar Container    │   │
│  └─────────────────┘    └───────────────────────┘   │
│                                                        │
└───────────────────────────────────────────────────────┘
                              │
                              ▼
                    ServiceMonitor discovers
                    and tells Prometheus to
                    scrape port 9121
```

### Configuration in Your Redis Instance Chart

**File**: `helm/redis-instance/values.yaml`

```yaml
redis:
  name: redis-replication
  mode: Replication
  
  # ... other config ...

# ✅ This enables redis-exporter sidecar
redisExporter:
  enabled: true
  image: quay.io/opstree/redis-exporter:1.0
  imagePullPolicy: Always
  resources:
    limits:
      cpu: 100m
      memory: 128Mi
    requests:
      cpu: 50m
      memory: 64Mi
  env:
    - name: REDIS_EXPORTER_INCL_SYSTEM_METRICS
      value: "true"
```

**File**: `helm/redis-instance/templates/redis-replication.yaml`

When the operator processes your Redis CR, it automatically adds the exporter sidecar to the StatefulSet.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Kubernetes Cluster                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  redis-operator-system (namespace)                     │   │
│  │  ┌──────────────────────────────────────────────┐     │   │
│  │  │  Redis Operator (controller)                 │     │   │
│  │  │  - Watches Redis CRs                          │     │   │
│  │  │  - Creates StatefulSets/Services             │     │   │
│  │  │  - NO exporter needed                        │     │   │
│  │  └──────────────────────────────────────────────┘     │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  staging (namespace)                                   │   │
│  │  ┌──────────────────────────────────────────────┐     │   │
│  │  │  Redis Instance (Custom Resource)            │     │   │
│  │  │  ┌────────────┐  ┌────────────────────┐     │     │   │
│  │  │  │ redis:7.0  │  │ redis-exporter:1.0 │     │     │   │
│  │  │  │ port 6379  │  │ port 9121          │◀────┼─────┼───ServiceMonitor
│  │  │  └────────────┘  └────────────────────┘     │     │   │
│  │  └──────────────────────────────────────────────┘     │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  prod (namespace)                                      │   │
│  │  ┌──────────────────────────────────────────────┐     │   │
│  │  │  Redis Instance (Custom Resource)            │     │   │
│  │  │  ┌────────────┐  ┌────────────────────┐     │     │   │
│  │  │  │ redis:7.0  │  │ redis-exporter:1.0 │     │     │   │
│  │  │  │ port 6379  │  │ port 9121          │◀────┼─────┼───ServiceMonitor
│  │  │  └────────────┘  └────────────────────┘     │     │   │
│  │  └──────────────────────────────────────────────┘     │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  monitoring (namespace)                                │   │
│  │  ┌──────────────────────────────────────────────┐     │   │
│  │  │  Prometheus                                   │     │   │
│  │  │  - Scrapes all ServiceMonitors               │     │   │
│  │  │  - Discovers redis-exporter:9121 endpoints   │     │   │
│  │  └──────────────────────────────────────────────┘     │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Summary: What Goes Where

| Component | Needs Exporter? | Needs ServiceMonitor? | Deployed Where |
|-----------|-----------------|----------------------|----------------|
| **Redis Operator** | ❌ No | ❌ No | `redis-operator-system` namespace (once) |
| **Redis Instance (staging)** | ✅ Yes (sidecar) | ✅ Yes | `staging` namespace |
| **Redis Instance (prod)** | ✅ Yes (sidecar) | ✅ Yes | `prod` namespace |

---

## Your Current Setup is Correct! ✅

Looking at your files:

1. ✅ **Redis Operator deployed** via ArgoCD to `redis-operator-system`
2. ✅ **Redis Instance chart** has monitoring config in `values.yaml`
3. ✅ **ServiceMonitor template** created in `helm/redis-instance/templates/servicemonitor.yaml`

### What You Need to Do

**Enable redis-exporter in your Redis Instance values**:

```yaml
# helm/redis-instance/values-staging.yaml
redis:
  name: redis-replication
  mode: Replication
  # ... other config ...

# ADD THIS:
redisExporter:
  enabled: true
  image: quay.io/opstree/redis-exporter:1.0
  imagePullPolicy: Always
  resources:
    requests:
      cpu: 50m
      memory: 64Mi
    limits:
      cpu: 100m
      memory: 128Mi
  env:
    - name: REDIS_EXPORTER_INCL_SYSTEM_METRICS
      value: "true"

monitoring:
  enabled: true
  interval: 30s
  scrapeTimeout: 10s
```

Repeat for `values-prod.yaml`.

---

## Verification Steps

After deployment:

```bash
# 1. Check Redis pods have 2 containers (redis + exporter)
kubectl get pods -n staging -l app.kubernetes.io/name=redis-replication
# Should show: 2/2 Running

# 2. Check ServiceMonitor exists
kubectl get servicemonitor -n staging

# 3. Test metrics endpoint
kubectl exec -n staging redis-replication-0 -c redis-exporter -- curl localhost:9121/metrics | head -20

# 4. Check Prometheus targets
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090
# Visit: http://localhost:9090/targets
# Look for: redis-instance targets showing UP
```

---

## References

1. **OT-Container-Kit Redis Operator**:
   - Architecture: https://github.com/OT-CONTAINER-KIT/redis-operator
   - Monitoring Guide: https://ot-container-kit.github.io/redis-operator/guide/monitoring.html
   - Redis Exporter: Built-in sidecar deployment

2. **Prometheus Operator**:
   - ServiceMonitor CRD: https://github.com/prometheus-operator/prometheus-operator/blob/main/Documentation/user-guides/running-exporters.md

3. **Best Practice**:
   - Run exporters as sidecars (not separate deployments) for pod-level metrics
   - Use ServiceMonitor for dynamic discovery (not manual Prometheus config)
