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
  name     = "duli-ai-vpc"
  region   = var.region
  ip_range = var.vpc_cidr
}
