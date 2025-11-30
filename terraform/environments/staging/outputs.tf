# Outputs for Staging Environment

output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "control_plane_ips" {
  description = "Control plane public IPs"
  value       = module.kubernetes_cluster.control_plane_public_ips
}

output "worker_ips" {
  description = "Worker public IPs"
  value       = module.kubernetes_cluster.worker_public_ips
}

output "first_control_plane_ip" {
  description = "First control plane IP for SSH access"
  value       = module.kubernetes_cluster.first_control_plane_ip
}

output "ssh_command" {
  description = "SSH command to connect to first control plane"
  value       = "ssh root@${module.kubernetes_cluster.first_control_plane_ip}"
}
