import os
import logging
import requests
from prometheus_client import start_http_server, Gauge
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
     
     if not DO_API_TOKEN:
          logger.warning("DO_API_TOKEN not set - metrics will be 0")
     
     droplet_cost = 0
     volume_cost = 0
     lb_cost = 0
     
     try:
          droplets = requests.get("https://api.digitalocean.com/v2/droplets?per_page=200", headers=headers).json()
          droplet_cost = len(droplets.get("droplets", [])) * 24
          logger.debug(f"Fetched {len(droplets.get('droplets', []))} droplets")
     except Exception as e:
          logger.error(f"Failed to fetch droplets: {e}")
     
     try:
          volumes = requests.get("https://api.digitalocean.com/v2/volumes?per_page=200", headers=headers).json()
          volume_cost = sum(v["size_gigabytes"] * 0.10 for v in volumes.get("volumes", []))
          logger.debug(f"Fetched {len(volumes.get('volumes', []))} volumes")
     except Exception as e:
          logger.error(f"Failed to fetch volumes: {e}")
     
     try:
          lbs = requests.get("https://api.digitalocean.com/v2/load_balancers?per_page=200", headers=headers).json()
          lb_cost = len(lbs.get("load_balancers", [])) * 12
          logger.debug(f"Fetched {len(lbs.get('load_balancers', []))} load balancers")
     except Exception as e:
          logger.error(f"Failed to fetch load balancers: {e}")
     
     total = droplet_cost + volume_cost + lb_cost
     
     do_total_cost.set(total)
     do_lb_cost.set(lb_cost)
     logger.info(f"Cost metrics - Droplets: ${droplet_cost:.2f}, Volumes: ${volume_cost:.2f}, LB: ${lb_cost:.2f}, Total: ${total:.2f}")

if __name__ == "__main__":
     logger.info(f"Starting DigitalOcean cost exporter on port {METRICS_PORT} with poll interval {POLL_INTERVAL}s")
     start_http_server(METRICS_PORT)
     while True:
         try:
             collect_metrics()
         except Exception as e:
             logger.exception(f"Unexpected error during metrics collection: {e}")
         time.sleep(POLL_INTERVAL)
