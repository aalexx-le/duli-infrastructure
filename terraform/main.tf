# Duli AI - Kubernetes Infrastructure

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

# Project for Kubernetes Cluster
resource "digitalocean_project" "kubernetes" {
  name        = "duli-kubernetes"
  description = "Duli AI - Kubernetes cluster"
  purpose     = "Other"
}

# Networking Module - Creates VPC first
module "networking" {
  source = "./modules/networking"

  region   = var.region
  vpc_cidr = var.vpc_cidr

  depends_on = [digitalocean_project.kubernetes]
}

# Kubernetes Cluster Module - Creates droplets in VPC, then updates firewall droplet_ids
module "kubernetes_cluster" {
  source = "./modules/kubernetes-cluster"

  region      = var.region
  vpc_id      = module.networking.vpc_id

  ssh_public_key_path = var.ssh_public_key_path
  project_id          = digitalocean_project.kubernetes.id

  control_plane_count = var.control_plane_count
  control_plane_size  = var.control_plane_size
  worker_count        = var.worker_count
  worker_size         = var.worker_size

  enable_monitoring = var.enable_monitoring

  depends_on = [module.networking, digitalocean_project.kubernetes]
}

# Firewall for Kubernetes internal communication
resource "digitalocean_firewall" "k8s_internal" {
  name        = "duli-k8s-internal"
  droplet_ids = module.kubernetes_cluster.droplet_ids

  # Kubernetes API server (TCP 6443)
  inbound_rule {
    protocol         = "tcp"
    port_range       = "6443"
    source_addresses = [var.vpc_cidr]
  }

  # etcd server client API (TCP 2379-2380)
  inbound_rule {
    protocol         = "tcp"
    port_range       = "2379-2380"
    source_addresses = [var.vpc_cidr]
  }

  # Kubelet API (TCP 10250)
  inbound_rule {
    protocol         = "tcp"
    port_range       = "10250"
    source_addresses = [var.vpc_cidr]
  }

  # kube-scheduler (TCP 10259)
  inbound_rule {
    protocol         = "tcp"
    port_range       = "10259"
    source_addresses = [var.vpc_cidr]
  }

  # kube-controller-manager (TCP 10257)
  inbound_rule {
    protocol         = "tcp"
    port_range       = "10257"
    source_addresses = [var.vpc_cidr]
  }

  # NodePort Services (TCP 30000-32767)
  inbound_rule {
    protocol         = "tcp"
    port_range       = "30000-32767"
    source_addresses = [var.vpc_cidr]
  }

  # Calico BGP (TCP 179)
  inbound_rule {
    protocol         = "tcp"
    port_range       = "179"
    source_addresses = [var.vpc_cidr]
  }

  # Calico VXLAN (UDP 4789)
  inbound_rule {
    protocol         = "udp"
    port_range       = "4789"
    source_addresses = [var.vpc_cidr]
  }

  # Allow all outbound traffic
  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  depends_on = [module.kubernetes_cluster]
}

# Firewall for SSH access
resource "digitalocean_firewall" "ssh_access" {
  name        = "duli-ssh-access"
  droplet_ids = module.kubernetes_cluster.droplet_ids

  # SSH from anywhere
  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  depends_on = [module.kubernetes_cluster]
}

# Firewall for load balancer access and all external traffic
resource "digitalocean_firewall" "ingress_access" {
  name        = "duli-ingress-access"
  droplet_ids = module.kubernetes_cluster.droplet_ids

  # Allow all TCP traffic from anywhere
  inbound_rule {
    protocol         = "tcp"
    port_range       = "1-65535"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Allow all UDP traffic from anywhere
  inbound_rule {
    protocol         = "udp"
    port_range       = "1-65535"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Allow ICMP (ping) from anywhere
  inbound_rule {
    protocol         = "icmp"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  depends_on = [module.kubernetes_cluster]
}

# Automatically write Ansible inventory to file
# This inventory will be used for both staging and prod deployments
resource "local_file" "ansible_inventory" {
  content = templatefile("${path.module}/templates/inventory.tpl", {
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
  })
  filename = "${path.module}/../ansible/inventories/hosts.ini"

  depends_on = [module.kubernetes_cluster]
}
