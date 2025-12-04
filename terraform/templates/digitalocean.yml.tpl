---
# ============================================================================
# DIGITALOCEAN CLOUD INTEGRATION
# ============================================================================
# Configuration for DigitalOcean-specific Kubernetes integration including
# Cloud Controller Manager (CCM) and Container Storage Interface (CSI) driver.

# DigitalOcean Cloud Controller Manager
# Reference: https://github.com/digitalocean/digitalocean-cloud-controller-manager/releases
# Used by: do_cloud_controller_manager.yml
do_ccm_version: "v0.1.64"  # Compatible with K8s 1.33.x

# DigitalOcean CSI Driver
# Reference: https://github.com/digitalocean/csi-digitalocean/releases
# Used by: do_csi_driver.yml
do_csi_driver_version: "v4.8.0"  # Compatible with K8s 1.33.x

# VPC Configuration
# Used by: do_cloud_controller_manager.yml
do_cluster_vpc_id: "${vpc_id}"

# Storage Configuration
# Default storage class created by CSI driver
storage_class: "do-block-storage"
