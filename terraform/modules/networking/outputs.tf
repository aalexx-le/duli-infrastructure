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
