#!/bin/bash
# Test script for DigitalOcean Cost Alert to Discord

# Get AlertManager service
AM_POD=$(kubectl get pod -n monitoring -l app.kubernetes.io/name=alertmanager -o name | head -1)

if [ -z "$AM_POD" ]; then
    echo "Error: AlertManager pod not found"
    exit 1
fi

echo "=== Sending test alert via AlertManager API ==="

kubectl exec -n monitoring $AM_POD -c alertmanager -- wget -q -O - --post-data='[
  {
    "labels": {
      "alertname": "DailyCostReport",
      "severity": "warning",
      "category": "cost",
      "resource_name": "test-droplet-01",
      "resource_type": "droplet",
      "specs": "2CPU 4096MB RAM 80GB Disk",
      "region": "sgp1"
    },
    "annotations": {
      "summary": "💰 Daily Cost Report - test-droplet-01",
      "description": "**DigitalOcean Infrastructure Cost Breakdown**\n\n• **test-droplet-01** (droplet): **$1.50/day**\n• Specs: 2CPU 4096MB RAM 80GB Disk\n• Region: sgp1\n\n_Cost monitoring dashboard: https://grafana.duli.one/d/cost-monitoring_"
    },
    "startsAt": "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'",
    "generatorURL": "http://prometheus:9090/graph"
  }
]' --header='Content-Type: application/json' 'http://localhost:9093/api/v2/alerts' 2>&1

echo ""
echo "=== Alert sent! Check Discord in a few seconds ==="
