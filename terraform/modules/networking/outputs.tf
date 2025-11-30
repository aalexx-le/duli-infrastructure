# Outputs for Networking Module

output "vpc_id" {
  description = "VPC ID"
  value       = digitalocean_vpc.main.id
}

output "vpc_urn" {
  description = "VPC URN"
  value       = digitalocean_vpc.main.urn
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = digitalocean_vpc.main.ip_range
}

output "k8s_firewall_id" {
  description = "Kubernetes internal firewall ID"
  value       = digitalocean_firewall.k8s_internal.id
}

output "ssh_firewall_id" {
  description = "SSH access firewall ID"
  value       = digitalocean_firewall.ssh_access.id
}

output "ingress_firewall_id" {
  description = "Ingress access firewall ID"
  value       = digitalocean_firewall.ingress_access.id
}
