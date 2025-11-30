# Networking Module for Kubernetes
# Creates VPC and firewall rules for Kubernetes cluster

terraform {
  required_version = ">= 1.0"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.32"
    }
  }
}

# VPC for private networking
resource "digitalocean_vpc" "main" {
  name     = "${var.environment}-vpc"
  region   = var.region
  ip_range = var.vpc_cidr
}

# Firewall for Kubernetes internal communication
resource "digitalocean_firewall" "k8s_internal" {
  name = "${var.environment}-internal"

  tags = ["environment:${var.environment}"]

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
}

# Firewall for SSH access
resource "digitalocean_firewall" "ssh_access" {
  name = "${var.environment}-ssh-access"

  tags = ["environment:${var.environment}"]

  # SSH from anywhere
  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
}

# Firewall for load balancer access and all external traffic
resource "digitalocean_firewall" "ingress_access" {
  name = "${var.environment}-ingress-access"

  tags = ["environment:${var.environment}"]

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
}
