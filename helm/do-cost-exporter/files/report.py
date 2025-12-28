#!/usr/bin/env python3
import os
import requests
from datetime import datetime

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "")

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
    """Format message for Discord"""
    total_cost = sum(r["cost"] for r in resources)
    
    # Group by type
    droplets = [r for r in resources if r["type"] == "droplet"]
    volumes = [r for r in resources if r["type"] == "volume"]
    lbs = [r for r in resources if r["type"] == "loadbalancer"]
    
    lines = [
        f"# 💰 Daily Cost Report - {datetime.now().strftime('%Y-%m-%d')}",
        "",
        f"**Total Daily Cost: ${total_cost:.2f}/day** (${total_cost * 30:.2f}/month)",
        "",
    ]
    
    if droplets:
        lines.append("## 🖥️ Droplets")
        for r in droplets:
            lines.append(f"• **{r['name']}**: ${r['cost']:.2f}/day - {r['specs']}")
        lines.append("")
    
    if volumes:
        lines.append("## 💾 Volumes")
        for r in volumes:
            lines.append(f"• **{r['name'][:20]}...**: ${r['cost']:.4f}/day - {r['specs']}")
        lines.append("")
    
    if lbs:
        lines.append("## ⚖️ Load Balancers")
        for r in lbs:
            lines.append(f"• **{r['name'][:20]}...**: ${r['cost']:.2f}/day")
        lines.append("")
    
    lines.append("_[View in Grafana](https://grafana.duli.one/d/cost-monitoring)_")
    
    return "\n".join(lines)

def send_to_discord(message):
    """Send message to Discord webhook"""
    if not DISCORD_WEBHOOK:
        print("No Discord webhook configured")
        return
    
    payload = {"content": message}
    response = requests.post(DISCORD_WEBHOOK, json=payload)
    
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
