# Cost Monitoring Stack

Complete guide for DigitalOcean + Kubernetes cost monitoring with Discord alerts.

## Architecture

**Flow:** OpenCost + DO Cost Exporter → Prometheus → AlertManager → Discord

**Components:**
- **OpenCost**: K8s resource costs (CPU, memory allocation)
- **DO Cost Exporter**: DigitalOcean infrastructure (droplets, volumes, load balancers)
- **Prometheus**: Metrics collection & alert evaluation
- **AlertManager**: Alert routing & management
- **alertmanager-discord**: Discord webhook bridge
- **Grafana**: Dashboards & visualization

## Quick Start

### Prerequisites
- Update `vault.yml` with `vault_discord_webhook_url` (Discord webhook for daily cost updates)
- Verify `vault_do_api_token` exists in `vault.yml`

### Deploy
```bash
cd ansible
ansible-playbook -i inventories/hosts.ini playbooks/install_infrastructures.yml -e target_environment=staging
```

ArgoCD auto-deploys 3 applications within 3 minutes:
- opencost
- do-cost-exporter
- alertmanager-discord

## Configuration Details

### AlertManager-Discord Helm Chart

**Service Details:**
- Name: `alertmanager-discord.monitoring.svc.cluster.local`
- Port: `9094` (not 8080)
- Parameter key: `discord.webhook_url`
- Environment variable: `DISCORD_WEBHOOK`

**Files:**
- `helm/alertmanager-discord/Chart.yaml` - Metadata
- `helm/alertmanager-discord/values.yaml` - Configuration
- `helm/alertmanager-discord/templates/` - Deployment, Service, Secret, ServiceAccount

### AlertManager Webhook Route

Daily notification configuration (24h repeat interval):
```yaml
routes:
  - receiver: 'discord-cost-alerts'
    group_by: ['alertname', 'severity']
    group_wait: 1m
    group_interval: 24h
    repeat_interval: 24h
    match:
      category: 'cost'

receivers:
  - name: 'discord-cost-alerts'
    webhook_configs:
      - url: 'http://alertmanager-discord.monitoring.svc.cluster.local:9094'
        send_resolved: true
```

**Key settings for daily notifications:**
- `group_wait: 1m` - Wait 1 minute to batch alerts
- `group_interval: 24h` - Group alerts together for 24 hours
- `repeat_interval: 24h` - Resend alert once per 24 hours (daily)

### Alert Rules

**3 PrometheusRules in `helm/do-cost-exporter/templates/prometheusrule.yaml`:**

1. **DailyCostReport** - Sends daily cost summary (K8s + DigitalOcean) every 24h
2. **DailyDigitalOceanCostAlert** - Sends daily DigitalOcean infrastructure cost breakdown
3. **CostAnomalyDetected** - Fires when daily cost deviates >25% from 7-day average (info level)

### Grafana Dashboard

7-panel dashboard automatically deployed via ConfigMap:
- Daily cost breakdown (pie chart)
- Total daily cost (stat card with thresholds)
- K8s cost estimate (stat card)
- 30-day cost trend (time series)
- Cost by resource type (table)
- Staging vs prod comparison (bar chart)
- Cost alerts panel

## Verification

### Check Helm Chart
```bash
helm lint infrastructure-kubernetes/helm/alertmanager-discord/
```

### Check Components Deployed
```bash
kubectl get pods -n monitoring
kubectl get applications -n argocd | grep -E "opencost|do-cost-exporter|alertmanager-discord"
```

### Verify Prometheus Rules
```bash
kubectl get prometheusrule -n monitoring
kubectl get prometheusrule cost-monitoring -n monitoring -o yaml
```

### Test Prometheus Queries
Port-forward: `kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090`

Queries:
```
do_cost_exporter_daily_cost
opencost_container_memory_allocation_bytes / 1024 / 1024 / 1024 / 30
opencost_pod_cpu_request * 0.031
```

### Access Grafana
```bash
# Get password
kubectl get secret -n monitoring kube-prometheus-stack-grafana -o jsonpath="{.data.admin-password}" | base64 -d

# Port-forward
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:3000
```

Navigate to `http://localhost:3000` → Home → Dashboards → "Cost Monitoring - Kubernetes & DigitalOcean"

## Troubleshooting

### No metrics in Prometheus
```bash
# Check exporter logs
kubectl logs -n monitoring -l app=do-cost-exporter
kubectl logs -n monitoring -l app=opencost

# Check Prometheus scrape targets
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090
# Navigate to http://localhost:9090/service-discovery
```

### Alerts not firing
```bash
# Verify rules loaded
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090
# Check http://localhost:9090/alerts

# Verify AlertManager config
kubectl get secret -n monitoring alertmanager-kube-prometheus-stack -o jsonpath='{.data.alertmanager\.yaml}' | base64 -d | grep -A5 "discord"
```

### Discord notifications not arriving
```bash
# Check pod logs
kubectl logs -n monitoring -l app.kubernetes.io/name=alertmanager-discord

# Verify webhook URL
kubectl get secret alertmanager-discord-secret -n monitoring -o jsonpath='{.data.webhook-url}' | base64 -d

# Verify AlertManager route points to port 9094
kubectl get secret -n monitoring alertmanager-kube-prometheus-stack -o jsonpath='{.data.alertmanager\.yaml}' | base64 -d | grep "9094"
```

## Cost Estimates

**K8s Resource Costs (OpenCost):**
- CPU: $0.031/CPU-hour
- Memory: $0.004/GB-hour

**DigitalOcean Infrastructure:**
- Droplet (2GB): ~$0.40/day
- Droplet (4GB): ~$0.80/day
- Load Balancer: ~$0.33/day
- Volume (100GB): ~$0.33/day

**Budget Breakdown ($150/day):**
- K8s (staging): ~$5/day
- K8s (prod): ~$30/day
- DigitalOcean: ~$58/day
- **Total: ~$93/day** (62% of budget)
- **Remaining: ~$57/day** for scaling/additional services

## Files Modified/Created

**Helm Charts:**
- `helm/alertmanager-discord/Chart.yaml`
- `helm/alertmanager-discord/values.yaml`
- `helm/alertmanager-discord/templates/{deployment,service,serviceaccount,secret,_helpers.tpl}.yaml`
- `helm/do-cost-exporter/templates/prometheusrule.yaml`
- `helm/kube-prometheus-stack/values-monitoring.yaml` (AlertManager config)
- `helm/kube-prometheus-stack/templates/grafana-cost-dashboard.yaml`

**ArgoCD Applications:**
- `gitops/applications/opencost.yml.j2`
- `gitops/applications/do-cost-exporter.yml.j2`
- `gitops/applications/alertmanager-discord.yml.j2`

**Secrets:**
- `ansible/inventories/group_vars/all/vault.yml` (added vault_discord_webhook_url)

## References

- [OpenCost Documentation](https://www.opencost.io/)
- [benjojo/alertmanager-discord](https://github.com/benjojo/alertmanager-discord)
- [Prometheus Alerting](https://prometheus.io/docs/alerting/latest/overview/)
- [AlertManager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
