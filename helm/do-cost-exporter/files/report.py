#!/usr/bin/env python3
import os
import re
import requests
from datetime import datetime
from jinja2 import Template

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "")
TEMPLATE_PATH = os.getenv("TEMPLATE_PATH", "/app/report_template.md")
DO_API_TOKEN = os.getenv("DO_API_TOKEN", "")

def query_prometheus(query):
    """Query Prometheus and return results"""
    response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query})
    data = response.json()
    if data["status"] != "success":
        return []
    return data["data"]["result"]

def get_mtd_billing():
    """Get month-to-date billing from DigitalOcean invoice preview API"""
    if not DO_API_TOKEN:
        return None
    
    headers = {
        "Authorization": f"Bearer {DO_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            "https://api.digitalocean.com/v2/customers/my/invoices/preview",
            headers=headers
        )
        if response.status_code != 200:
            return None
        
        data = response.json()
        invoice = data.get("invoice_preview", {})
        
        # Parse billing period
        billing_period = invoice.get("billing_period", "")
        
        # Sum up by product category
        mtd = {
            "billing_period": billing_period,
            "droplets": 0,
            "volumes": 0,
            "load_balancers": 0,
            "total": 0,
        }
        
        for item in invoice.get("product_charges", {}).get("items", []):
            amount = float(item.get("amount", 0))
            product = item.get("product", "").lower()
            
            if "droplet" in product:
                mtd["droplets"] += amount
            elif "volume" in product or "storage" in product:
                mtd["volumes"] += amount
            elif "load balancer" in product:
                mtd["load_balancers"] += amount
            
            mtd["total"] += amount
        
        return mtd
    except Exception as e:
        print(f"Error fetching MTD billing: {e}")
        return None

def get_pvc_service_map():
    """Build a map from PV name to service name using kube-state-metrics"""
    results = query_prometheus("kube_persistentvolumeclaim_info")
    pvc_map = {}
    
    for result in results:
        labels = result["metric"]
        pv_name = labels.get("volumename", "")
        pvc_name = labels.get("persistentvolumeclaim", "")
        namespace = labels.get("namespace", "")
        
        if not pv_name:
            continue
        
        # Determine service name from PVC name patterns
        service = None
        if pvc_name.startswith("database-") or "keycloak-db" in pvc_name:
            service = f"postgresql ({namespace})"
        elif "redis" in pvc_name:
            service = f"redis ({namespace})"
        elif "queue" in pvc_name:
            service = f"rabbitmq ({namespace})"
        elif "grafana" in pvc_name:
            service = "grafana (monitoring)"
        elif "prometheus" in pvc_name:
            service = "prometheus (monitoring)"
        elif "alertmanager" in pvc_name:
            service = "alertmanager (monitoring)"
        elif "loki" in pvc_name:
            service = "loki (monitoring)"
        else:
            service = f"{pvc_name} ({namespace})"
        
        pvc_map[pv_name] = service
    
    return pvc_map

def get_costs():
    """Query Prometheus for cost metrics"""
    results = query_prometheus("do_cost_exporter_resource_cost")
    
    resources = []
    for result in results:
        labels = result["metric"]
        value = float(result["value"][1])
        resources.append({
            "name": labels.get("resource_name", "unknown"),
            "type": labels.get("resource_type", "unknown"),
            "specs": labels.get("specs", ""),
            "region": labels.get("region", ""),
            "cost": value
        })
    
    return sorted(resources, key=lambda x: x["cost"], reverse=True)

def group_volumes_by_service(volumes, pvc_map):
    """Group volumes by service and sum their costs"""
    grouped = {}
    for vol in volumes:
        service = pvc_map.get(vol["name"], "unknown")
        if service not in grouped:
            grouped[service] = {"name": service, "cost": 0, "count": 0, "size_gb": 0}
        grouped[service]["cost"] += vol["cost"]
        grouped[service]["count"] += 1
        # Extract size from specs like "40GB Storage"
        specs = vol.get("specs", "")
        match = re.search(r"(\d+)GB", specs)
        if match:
            grouped[service]["size_gb"] += int(match.group(1))
    
    return sorted(grouped.values(), key=lambda x: x["cost"], reverse=True)

def format_discord_message(resources):
    """Format message using Jinja2 template"""
    total_cost = sum(r["cost"] for r in resources)
    
    volumes = [r for r in resources if r["type"] == "volume"]
    pvc_map = get_pvc_service_map()
    grouped_volumes = group_volumes_by_service(volumes, pvc_map)
    
    loadbalancers = [r for r in resources if r["type"] == "loadbalancer"]
    lb_total_cost = sum(lb["cost"] for lb in loadbalancers)
    
    # Get MTD billing from DO API
    mtd = get_mtd_billing()
    
    context = {
        "date": datetime.now().strftime('%Y-%m-%d'),
        "total_daily": total_cost,
        "total_monthly": total_cost * 30,
        "droplets": [r for r in resources if r["type"] == "droplet"],
        "volumes": grouped_volumes,
        "lb_count": len(loadbalancers),
        "lb_cost": lb_total_cost,
        "mtd": mtd,
    }
    
    with open(TEMPLATE_PATH) as f:
        template = Template(f.read())
    
    return template.render(**context).strip()

def send_to_discord(message):
    """Send message to Discord webhook"""
    if not DISCORD_WEBHOOK:
        print("No Discord webhook configured")
        return
    
    response = requests.post(DISCORD_WEBHOOK, json={"content": message})
    
    if response.status_code == 204:
        print("Message sent successfully")
    else:
        print(f"Failed to send: {response.status_code} - {response.text}")

def main():
    resources = get_costs()
    if not resources:
        print("No cost data found")
        return
    
    message = format_discord_message(resources)
    print(message)
    send_to_discord(message)

if __name__ == "__main__":
    main()
