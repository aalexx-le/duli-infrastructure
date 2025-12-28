#!/usr/bin/env python3
import os
import re
import requests
from datetime import datetime, timedelta
from jinja2 import Template

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "")
TEMPLATE_PATH = os.getenv("TEMPLATE_PATH", "/app/report_template.md")

def query_prometheus(query):
    """Query Prometheus and return results"""
    response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query})
    data = response.json()
    if data["status"] != "success":
        return []
    return data["data"]["result"]

def get_billing_period():
    """Get billing period info (start date, end date, days elapsed)"""
    now = datetime.now()
    start_date = now.replace(day=1)
    # End of month
    if now.month == 12:
        end_of_month = now.replace(year=now.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_of_month = now.replace(month=now.month + 1, day=1) - timedelta(days=1)
    
    return {
        "start": start_date.strftime('%b %d'),
        "today": now.strftime('%b %d'),
        "end": end_of_month.strftime('%b %d'),
        "days_elapsed": now.day,
        "days_in_month": end_of_month.day,
    }

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
    # Services to hide from report
    hidden_services = ["loki (monitoring)", "grafana (monitoring)"]
    
    grouped = {}
    for vol in volumes:
        service = pvc_map.get(vol["name"], "unknown")
        if service in hidden_services:
            continue
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
    
    # Get billing period info
    period = get_billing_period()
    days_elapsed = period["days_elapsed"]
    days_in_month = period["days_in_month"]
    
    # Add costs to each droplet
    droplets = [r for r in resources if r["type"] == "droplet"]
    droplets_today = 0
    droplets_mtd = 0
    droplets_estimated = 0
    for droplet in droplets:
        droplet["today"] = droplet["cost"]
        droplet["mtd"] = droplet["cost"] * days_elapsed
        droplet["estimated"] = droplet["cost"] * days_in_month
        droplets_today += droplet["today"]
        droplets_mtd += droplet["mtd"]
        droplets_estimated += droplet["estimated"]
    
    # Add costs to each volume group
    volumes_today = 0
    volumes_mtd = 0
    volumes_estimated = 0
    for vol_group in grouped_volumes:
        vol_group["today"] = vol_group["cost"]
        vol_group["mtd"] = vol_group["cost"] * days_elapsed
        vol_group["estimated"] = vol_group["cost"] * days_in_month
        volumes_today += vol_group["today"]
        volumes_mtd += vol_group["mtd"]
        volumes_estimated += vol_group["estimated"]
    
    # LB costs
    lb_today = lb_total_cost
    lb_mtd = lb_total_cost * days_elapsed
    lb_estimated = lb_total_cost * days_in_month
    
    # Totals
    total_today = total_cost
    total_mtd = total_cost * days_elapsed
    total_estimated = total_cost * days_in_month
    
    context = {
        "period": period,
        "total_today": total_today,
        "total_mtd": total_mtd,
        "total_estimated": total_estimated,
        "droplets": droplets,
        "droplets_today": droplets_today,
        "droplets_mtd": droplets_mtd,
        "droplets_estimated": droplets_estimated,
        "volumes": grouped_volumes,
        "volumes_today": volumes_today,
        "volumes_mtd": volumes_mtd,
        "volumes_estimated": volumes_estimated,
        "lb_count": len(loadbalancers),
        "lb_today": lb_today,
        "lb_mtd": lb_mtd,
        "lb_estimated": lb_estimated,
        "severity": "warning" if total_estimated > 90 else "normal",
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
