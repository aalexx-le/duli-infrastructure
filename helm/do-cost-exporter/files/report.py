#!/usr/bin/env python3
import os
import requests
from datetime import datetime
from jinja2 import Template

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "")
TEMPLATE_PATH = os.getenv("TEMPLATE_PATH", "/app/report_template.md")

def get_costs():
    """Query Prometheus for cost metrics"""
    query = 'do_cost_exporter_resource_cost'
    response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query})
    data = response.json()
    
    if data["status"] != "success":
        return []
    
    resources = []
    for result in data["data"]["result"]:
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

def format_discord_message(resources):
    """Format message using Jinja2 template"""
    total_cost = sum(r["cost"] for r in resources)
    
    context = {
        "date": datetime.now().strftime('%Y-%m-%d'),
        "total_daily": total_cost,
        "total_monthly": total_cost * 30,
        "droplets": [r for r in resources if r["type"] == "droplet"],
        "volumes": [r for r in resources if r["type"] == "volume"],
        "loadbalancers": [r for r in resources if r["type"] == "loadbalancer"],
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
