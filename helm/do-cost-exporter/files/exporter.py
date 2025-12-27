import os
import requests
from prometheus_client import start_http_server, Gauge
import time

DO_API_TOKEN = os.getenv("DO_API_TOKEN", "")
METRICS_PORT = int(os.getenv("METRICS_PORT", "8080"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "3600"))

# Metrics
do_droplets_cost = Gauge("do_droplets_cost_monthly", "Droplets cost", ["region"])
do_volumes_cost = Gauge("do_volumes_cost_monthly", "Volumes cost", ["region"])
do_lb_cost = Gauge("do_loadbalancers_cost_monthly", "Load balancers cost")
do_total_cost = Gauge("do_total_cost_monthly", "Total cost")

def collect_metrics():
    headers = {"Authorization": f"Bearer {DO_API_TOKEN}"}
    
    # Droplets: $24/month each
    droplets = requests.get("https://api.digitalocean.com/v2/droplets?per_page=200", headers=headers).json()
    droplet_cost = len(droplets.get("droplets", [])) * 24
    
    # Volumes: $0.10/GiB/month
    volumes = requests.get("https://api.digitalocean.com/v2/volumes?per_page=200", headers=headers).json()
    volume_cost = sum(v["size_gigabytes"] * 0.10 for v in volumes.get("volumes", []))
    
    # Load Balancers: $12/month each
    lbs = requests.get("https://api.digitalocean.com/v2/load_balancers?per_page=200", headers=headers).json()
    lb_cost = len(lbs.get("load_balancers", [])) * 12
    
    total = droplet_cost + volume_cost + lb_cost
    
    do_total_cost.set(total)
    do_lb_cost.set(lb_cost)
    print(f"Costs - Droplets: ${droplet_cost:.2f}, Volumes: ${volume_cost:.2f}, LB: ${lb_cost:.2f}, Total: ${total:.2f}")

if __name__ == "__main__":
    start_http_server(METRICS_PORT)
    while True:
        try:
            collect_metrics()
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(POLL_INTERVAL)
