# Kubernetes Cluster Module
# Creates control plane and worker nodes (infrastructure only)
# Kubernetes installation is handled by Ansible (Kubespray)

terraform {
  required_version = ">= 1.0"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.32"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

# SSH Key for K8s Nodes
resource "digitalocean_ssh_key" "k8s" {
  name       = "${var.environment}-k8s-key"
  public_key = file(var.ssh_public_key_path)
}

# Control Plane Nodes
resource "digitalocean_droplet" "control_plane" {
  count = var.control_plane_count

  name   = "${var.environment}-control-${format("%02d", count.index + 1)}"
  region = var.region
  image  = var.droplet_image
  size   = var.control_plane_size

  vpc_uuid = var.vpc_id
  ssh_keys = [digitalocean_ssh_key.k8s.fingerprint]

  monitoring = var.enable_monitoring
  ipv6       = true

  tags = [
    "environment:${var.environment}",
    "role:control-plane"
  ]

  lifecycle {
    create_before_destroy = false
  }
}

# Worker Nodes
resource "digitalocean_droplet" "worker" {
  count = var.worker_count

  name   = "${var.environment}-worker-${format("%02d", count.index + 1)}"
  region = var.region
  image  = var.droplet_image
  size   = var.worker_size

  vpc_uuid = var.vpc_id
  ssh_keys = [digitalocean_ssh_key.k8s.fingerprint]

  monitoring = var.enable_monitoring
  ipv6       = true

  tags = [
    "environment:${var.environment}",
    "role:worker"
  ]

  lifecycle {
    create_before_destroy = false
  }
}

# Assign K8s Droplets to Project
resource "digitalocean_project_resources" "k8s_droplets" {
  project = var.project_id

  resources = concat(
    [for cp in digitalocean_droplet.control_plane[*].urn : cp],
    [for w in digitalocean_droplet.worker[*].urn : w]
  )
}


