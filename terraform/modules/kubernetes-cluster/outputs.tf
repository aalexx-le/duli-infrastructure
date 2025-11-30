# Outputs for Kubernetes Cluster Module

output "control_plane_details" {
  description = "Control plane node details"
  value = [
    for cp in digitalocean_droplet.control_plane : {
      id         = cp.id
      name       = cp.name
      public_ip  = cp.ipv4_address
      private_ip = cp.ipv4_address_private
      urn        = cp.urn
    }
  ]
}

output "worker_details" {
  description = "Worker node details"
  value = [
    for w in digitalocean_droplet.worker : {
      id         = w.id
      name       = w.name
      public_ip  = w.ipv4_address
      private_ip = w.ipv4_address_private
      urn        = w.urn
    }
  ]
}

output "control_plane_public_ips" {
  description = "Control plane public IPs"
  value       = [for cp in digitalocean_droplet.control_plane : cp.ipv4_address]
}

output "control_plane_private_ips" {
  description = "Control plane private IPs"
  value       = [for cp in digitalocean_droplet.control_plane : cp.ipv4_address_private]
}

output "worker_public_ips" {
  description = "Worker public IPs"
  value       = [for w in digitalocean_droplet.worker : w.ipv4_address]
}

output "worker_private_ips" {
  description = "Worker private IPs"
  value       = [for w in digitalocean_droplet.worker : w.ipv4_address_private]
}

output "first_control_plane_ip" {
  description = "First control plane public IP (for SSH access)"
  value       = digitalocean_droplet.control_plane[0].ipv4_address
}

output "ssh_key_fingerprint" {
  description = "SSH key fingerprint"
  value       = digitalocean_ssh_key.k8s.fingerprint
}
