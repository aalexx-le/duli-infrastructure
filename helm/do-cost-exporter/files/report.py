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
    """Query Prometheus for cost metrics (current resources, daily rate)"""
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


def get_billing():
    """Query Prometheus for actual DO billing data"""
    billing = {"droplets": 0, "volumes": 0, "load balancers": 0, "taxes": 0, "credits": 0, "total": 0}
    
    results = query_prometheus("do_cost_exporter_billing_mtd")
    for result in results:
        category = result["metric"].get("category", "unknown")
        value = float(result["value"][1])
        billing[category] = value
    
    balance_results = query_prometheus("do_cost_exporter_billing_balance")
    for result in balance_results:
        billing_type = result["metric"].get("type", "unknown")
        value = float(result["value"][1])
        billing[billing_type] = value
    
    return billing


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


def build_embed(resources, billing):
    """Build Discord embed from resources and actual billing data"""
    period = get_billing_period()
    days = period["days_elapsed"]
    days_in_month = period["days_in_month"]
    
    # Use actual billing data from DO API
    mtd_usage = billing.get("month_to_date_usage", 0)
    droplets_mtd = billing.get("droplets", 0)
    volumes_mtd = billing.get("volumes", 0)
    lb_mtd = billing.get("load balancers", 0)
    taxes = billing.get("taxes", 0)
    credits = billing.get("credits", 0)
    
    # Calculate daily rate and estimates from actual MTD
    daily_rate = mtd_usage / days if days > 0 else 0
    estimated = daily_rate * days_in_month
    
    # Determine severity
    severity = "warning" if estimated > COST_THRESHOLD else "normal"
    color = 0x57F287 if severity == "normal" else 0xED4245
    
    # Create embed
    title = f"Cost Report ({period['start']} - {period['today']})"
    embed = DiscordEmbed(title=title, color=color)
    
    # Summary fields (3 columns at top) - using actual billing
    embed.add_embed_field(name="💳 Daily Rate", value=f"${daily_rate:.2f}", inline=True)
    embed.add_embed_field(name="📅 Month-to-date", value=f"${mtd_usage:.2f}", inline=True)
    embed.add_embed_field(name="📈 Estimated", value=f"${estimated:.2f}", inline=True)
    
    # Droplets - show actual MTD cost with current resource details
    droplets = [r for r in resources if r["type"] == "droplet"]
    if droplets:
        droplet_lines = [f"• droplet-{i}: {d['specs']}" for i, d in enumerate(droplets, 1)]
        embed.add_embed_field(name=f"Droplets (${droplets_mtd:.2f})", value="\n".join(droplet_lines), inline=False)
    
    # Volumes - show actual MTD cost with service breakdown
    volumes = [r for r in resources if r["type"] == "volume"]
    pvc_map = get_pvc_service_map()
    grouped_volumes = group_volumes_by_service(volumes, pvc_map)
    if grouped_volumes:
        volume_lines = []
        for v in grouped_volumes:
            count_text = "volume" if v["count"] == 1 else "volumes"
            volume_lines.append(f"• {v['name']}: {v['size_gb']}GB ({v['count']} {count_text})")
        embed.add_embed_field(name=f"Volumes (${volumes_mtd:.2f})", value="\n".join(volume_lines), inline=False)
    
    # Load Balancers - show actual MTD cost
    lbs = [r for r in resources if r["type"] == "loadbalancer"]
    if lbs or lb_mtd > 0:
        lb_count = len(lbs) if lbs else "?"
        embed.add_embed_field(name=f"Load Balancers (${lb_mtd:.2f})", value=f"• {lb_count} LB", inline=False)
    
    # Taxes and Credits
    if taxes > 0 or credits != 0:
        extras = []
        if taxes > 0:
            extras.append(f"Taxes: ${taxes:.2f}")
        if credits != 0:
            extras.append(f"Credits: ${credits:.2f}")
        embed.add_embed_field(name="Adjustments", value=" | ".join(extras), inline=False)
    
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
    billing = get_billing()
    
    if not billing.get("month_to_date_usage"):
        print("No billing data found - check exporter")
        return
    
    embed, severity = build_embed(resources, billing)
    
    # Print summary for logs
    mtd = billing.get("month_to_date_usage", 0)
    print(f"Cost Report: MTD ${mtd:.2f} (severity: {severity})")
    
    send_to_discord(embed)


if __name__ == "__main__":
    main()
