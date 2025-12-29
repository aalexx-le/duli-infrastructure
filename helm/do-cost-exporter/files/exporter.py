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

resource_cost = Gauge(
    "do_cost_exporter_resource_cost",
    "DigitalOcean resource cost per day",
    ["resource_id", "resource_name", "resource_type", "specs", "region"]
)

billing_mtd = Gauge(
    "do_cost_exporter_billing_mtd",
    "DigitalOcean actual month-to-date billing from invoice",
    ["category"]
)

billing_balance = Gauge(
    "do_cost_exporter_billing_balance",
    "DigitalOcean account balance info",
    ["type"]
)

def get_droplet_specs(droplet):
    """Extract droplet specs in human-readable format"""
    size = droplet.get("size", {})
    cpu = size.get("vcpus", 0)
    memory = size.get("memory", 0)
    disk = size.get("disk", 0)
    return f"{cpu}CPU {memory}MB RAM {disk}GB Disk"


def collect_billing_metrics(headers):
    """Collect actual billing data from DigitalOcean API"""
    try:
        balance = requests.get(
            "https://api.digitalocean.com/v2/customers/my/balance",
            headers=headers
        ).json()
        
        mtd_usage = float(balance.get("month_to_date_usage", 0))
        account_balance = float(balance.get("account_balance", 0))
        
        billing_balance.labels(type="month_to_date_usage").set(mtd_usage)
        billing_balance.labels(type="account_balance").set(account_balance)
        
        logger.info(f"Billing: MTD usage ${mtd_usage:.2f}, account balance ${account_balance:.2f}")
        
    except Exception as e:
        logger.error(f"Failed to fetch balance: {e}")
    
    try:
        invoices = requests.get(
            "https://api.digitalocean.com/v2/customers/my/invoices",
            headers=headers
        ).json()
        
        preview = invoices.get("invoice_preview", {})
        invoice_uuid = preview.get("invoice_uuid")
        
        if invoice_uuid:
            summary = requests.get(
                f"https://api.digitalocean.com/v2/customers/my/invoices/{invoice_uuid}/summary",
                headers=headers
            ).json()
            
            product_charges = summary.get("product_charges", {})
            for item in product_charges.get("items", []):
                category = item.get("name", "unknown").lower()
                amount = float(item.get("amount", 0))
                billing_mtd.labels(category=category).set(amount)
                logger.debug(f"Billing {category}: ${amount:.2f}")
            
            taxes = summary.get("taxes", {})
            tax_amount = float(taxes.get("amount", 0))
            billing_mtd.labels(category="taxes").set(tax_amount)
            
            credits = summary.get("credits_and_adjustments", {})
            credit_amount = float(credits.get("amount", 0))
            billing_mtd.labels(category="credits").set(credit_amount)
            
            total = float(summary.get("amount", 0))
            billing_mtd.labels(category="total").set(total)
            
            logger.info(f"Invoice breakdown: Droplets, Volumes, LBs, Taxes=${tax_amount:.2f}, Credits=${credit_amount:.2f}, Total=${total:.2f}")
            
    except Exception as e:
        logger.error(f"Failed to fetch invoice summary: {e}")


def collect_metrics():
    headers = {"Authorization": f"Bearer {DO_API_TOKEN}"}
    
    if not DO_API_TOKEN:
        logger.warning("DO_API_TOKEN not set - metrics will be 0")
        return
    
    collect_billing_metrics(headers)
    
    total_cost = 0
    
    try:
        droplets = requests.get(
            "https://api.digitalocean.com/v2/droplets?per_page=200",
            headers=headers
        ).json()
        
        for droplet in droplets.get("droplets", []):
            droplet_id = droplet.get("id")
            droplet_name = droplet.get("name", f"droplet-{droplet_id}")
            region = droplet.get("region", {}).get("slug", "unknown")
            specs = get_droplet_specs(droplet)
            
            cost = droplet.get("size", {}).get("price_monthly", 0) / 30
            
            resource_cost.labels(
                resource_id=str(droplet_id),
                resource_name=droplet_name,
                resource_type="droplet",
                specs=specs,
                region=region
            ).set(cost)
            
            total_cost += cost
            logger.debug(f"Droplet {droplet_name}: ${cost:.2f}/day")
        
        logger.info(f"Processed {len(droplets.get('droplets', []))} droplets")
        
    except Exception as e:
        logger.error(f"Failed to fetch droplets: {e}")
    
    try:
        volumes = requests.get(
            "https://api.digitalocean.com/v2/volumes?per_page=200",
            headers=headers
        ).json()
        
        for volume in volumes.get("volumes", []):
            volume_id = volume.get("id")
            volume_name = volume.get("name", f"volume-{volume_id}")
            region = volume.get("region", {}).get("slug", "unknown")
            size_gb = volume.get("size_gigabytes", 0)
            
            cost = size_gb * 0.10 / 30
            
            resource_cost.labels(
                resource_id=volume_id,
                resource_name=volume_name,
                resource_type="volume",
                specs=f"{size_gb}GB Storage",
                region=region
            ).set(cost)
            
            total_cost += cost
            logger.debug(f"Volume {volume_name}: ${cost:.2f}/day")
        
        logger.info(f"Processed {len(volumes.get('volumes', []))} volumes")
        
    except Exception as e:
        logger.error(f"Failed to fetch volumes: {e}")
    
    try:
        lbs = requests.get(
            "https://api.digitalocean.com/v2/load_balancers?per_page=200",
            headers=headers
        ).json()
        
        for lb in lbs.get("load_balancers", []):
            lb_id = lb.get("id")
            lb_name = lb.get("name", f"lb-{lb_id}")
            region = lb.get("region", {}).get("slug", "unknown")
            
            cost = 12 / 30
            
            resource_cost.labels(
                resource_id=lb_id,
                resource_name=lb_name,
                resource_type="loadbalancer",
                specs="Load Balancer",
                region=region
            ).set(cost)
            
            total_cost += cost
            logger.debug(f"Load Balancer {lb_name}: ${cost:.2f}/day")
        
        logger.info(f"Processed {len(lbs.get('load_balancers', []))} load balancers")
        
    except Exception as e:
        logger.error(f"Failed to fetch load balancers: {e}")
    
    logger.info(f"Total daily cost: ${total_cost:.2f}")

if __name__ == "__main__":
    logger.info(f"Starting DigitalOcean cost exporter on port {METRICS_PORT} with poll interval {POLL_INTERVAL}s")
    start_http_server(METRICS_PORT)
    while True:
        try:
            collect_metrics()
        except Exception as e:
            logger.exception(f"Unexpected error during metrics collection: {e}")
        time.sleep(POLL_INTERVAL)
