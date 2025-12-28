#!/usr/bin/env python3
import os
import re
import requests
from datetime import datetime, timedelta
from discord_webhook import DiscordWebhook, DiscordEmbed

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK", "")
COST_THRESHOLD = float(os.getenv("COST_THRESHOLD", "100"))

# Services to hide from report
HIDDEN_SERVICES = ["loki (monitoring)", "grafana (monitoring)"]


def query_prometheus(query):
    """Query Prometheus and return results"""
    response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query})
    data = response.json()
    if data["status"] != "success":
        return []
    return data["data"]["result"]


def get_billing_period():
    """Get billing period info"""
    now = datetime.now()
    start_date = now.replace(day=1)
    if now.month == 12:
        end_of_month = now.replace(year=now.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_of_month = now.replace(month=now.month + 1, day=1) - timedelta(days=1)
    
    return {
        "start": start_date.strftime('%b %d'),
        "today": now.strftime('%b %d'),
        "days_elapsed": now.day,
        "days_in_month": end_of_month.day,
    }


def get_pvc_service_map():
    """Build a map from PV name to service name"""
    results = query_prometheus("kube_persistentvolumeclaim_info")
    pvc_map = {}
    
    for result in results:
        labels = result["metric"]
        pv_name = labels.get("volumename", "")
        pvc_name = labels.get("persistentvolumeclaim", "")
        namespace = labels.get("namespace", "")
        
        if not pv_name:
            continue
        
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
            "cost": value
        })
    
    return sorted(resources, key=lambda x: x["cost"], reverse=True)


def group_volumes_by_service(volumes, pvc_map):
    """Group volumes by service and sum their costs"""
    grouped = {}
    for vol in volumes:
        service = pvc_map.get(vol["name"], "unknown")
        if service in HIDDEN_SERVICES:
            continue
        if service not in grouped:
            grouped[service] = {"name": service, "cost": 0, "count": 0, "size_gb": 0}
        grouped[service]["cost"] += vol["cost"]
        grouped[service]["count"] += 1
        match = re.search(r"(\d+)GB", vol.get("specs", ""))
        if match:
            grouped[service]["size_gb"] += int(match.group(1))
    
    return sorted(grouped.values(), key=lambda x: x["cost"], reverse=True)


def build_embed(resources):
    """Build Discord embed from resources"""
    period = get_billing_period()
    days = period["days_elapsed"]
    days_in_month = period["days_in_month"]
    
    # Calculate costs
    total_cost = sum(r["cost"] for r in resources)
    total_today = total_cost
    total_mtd = total_cost * days
    total_estimated = total_cost * days_in_month
    
    # Determine severity
    severity = "warning" if total_estimated > COST_THRESHOLD else "normal"
    color = 0x57F287 if severity == "normal" else 0xED4245
    
    # Create embed
    title = f"Cost Report ({period['start']} - {period['today']})"
    embed = DiscordEmbed(title=title, color=color)
    
    # Summary fields (3 columns at top)
    embed.add_embed_field(name="💳 Today", value=f"${total_today:.2f}", inline=True)
    embed.add_embed_field(name="📅 Month-to-date", value=f"${total_mtd:.2f}", inline=True)
    embed.add_embed_field(name="📈 Estimated", value=f"${total_estimated:.2f}", inline=True)
    
    # Droplets as field
    droplets = [r for r in resources if r["type"] == "droplet"]
    if droplets:
        droplets_mtd = sum(d["cost"] * days for d in droplets)
        droplet_lines = [f"• droplet-{i}: **${d['cost']*days:.2f}** - {d['specs']}" for i, d in enumerate(droplets, 1)]
        embed.add_embed_field(name=f"Droplets (${droplets_mtd:.2f})", value="\n".join(droplet_lines), inline=False)
    
    # Volumes as field
    volumes = [r for r in resources if r["type"] == "volume"]
    pvc_map = get_pvc_service_map()
    grouped_volumes = group_volumes_by_service(volumes, pvc_map)
    if grouped_volumes:
        volumes_mtd = sum(v["cost"] * days for v in grouped_volumes)
        volume_lines = []
        for v in grouped_volumes:
            mtd = v["cost"] * days
            count_text = "volume" if v["count"] == 1 else "volumes"
            volume_lines.append(f"• {v['name']}: **${mtd:.2f}** - {v['size_gb']}GB ({v['count']} {count_text})")
        embed.add_embed_field(name=f"Volumes (${volumes_mtd:.2f})", value="\n".join(volume_lines), inline=False)
    
    # Load Balancers as field
    lbs = [r for r in resources if r["type"] == "loadbalancer"]
    if lbs:
        lb_mtd = sum(lb["cost"] * days for lb in lbs)
        embed.add_embed_field(name=f"Load Balancers (${lb_mtd:.2f})", value=f"• {len(lbs)} LB: **${lb_mtd:.2f}**", inline=False)
    
    return embed, severity


def send_to_discord(embed):
    """Send embed to Discord webhook"""
    if not DISCORD_WEBHOOK_URL:
        print("No Discord webhook configured")
        return
    
    webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL)
    webhook.add_embed(embed)
    
    response = webhook.execute()
    if response.status_code in [200, 204]:
        print("Message sent successfully")
    else:
        print(f"Failed to send: {response.status_code}")


def main():
    resources = get_costs()
    if not resources:
        print("No cost data found")
        return
    
    embed, severity = build_embed(resources)
    
    # Print summary for logs
    period = get_billing_period()
    days = period["days_elapsed"]
    total = sum(r["cost"] for r in resources) * days
    print(f"Cost Report: MTD ${total:.2f} (severity: {severity})")
    
    send_to_discord(embed)


if __name__ == "__main__":
    main()
