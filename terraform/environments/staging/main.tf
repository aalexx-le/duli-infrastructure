# Staging Environment Configuration
# Provisions Kubernetes cluster for staging environment

terraform {
  required_version = ">= 1.0"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.32"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.0"
    }
  }
}

# Provider configuration
provider "digitalocean" {
  token = var.do_token
}

# Project for Staging Environment
resource "digitalocean_project" "staging" {
  name        = "duli-k8s-${var.environment}"
  description = "Kubernetes cluster for ${var.environment} environment"
  purpose     = "Other"
  environment = "Staging"
}

# Networking Module
module "networking" {
  source = "../../modules/networking"

  environment = var.environment
  region      = var.region
  vpc_cidr    = var.vpc_cidr
}

# Kubernetes Cluster Module
module "kubernetes_cluster" {
  source = "../../modules/kubernetes-cluster"

  environment = var.environment
  region      = var.region
  vpc_id      = module.networking.vpc_id

  ssh_public_key_path = var.ssh_public_key_path
  project_id          = digitalocean_project.staging.id

  control_plane_count = var.control_plane_count
  control_plane_size  = var.control_plane_size
  worker_count        = var.worker_count
  worker_size         = var.worker_size

  enable_monitoring = var.enable_monitoring

  depends_on = [module.networking, digitalocean_project.staging]
}

# Automatically write Ansible inventory to file
resource "local_file" "ansible_inventory" {
  content = templatefile("${path.module}/../../templates/inventory.tpl", {
    control_plane_nodes = [
      for idx, cp in module.kubernetes_cluster.control_plane_details : {
        name       = cp.name
        public_ip  = cp.public_ip
        private_ip = cp.private_ip
      }
    ]
    worker_nodes = [
      for idx, worker in module.kubernetes_cluster.worker_details : {
        name       = worker.name
        public_ip  = worker.public_ip
        private_ip = worker.private_ip
      }
    ]
    environment          = var.environment
    ssh_private_key_path = replace(abspath(var.ssh_public_key_path), ".pub", "")
  })
  filename = "${path.module}/../../../ansible/inventories/staging/hosts.ini"

  depends_on = [module.kubernetes_cluster]
}
