# Variables for Kubernetes Cluster Module

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}

variable "region" {
  description = "DigitalOcean region"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for private networking"
  type        = string
}

variable "project_id" {
  description = "DigitalOcean project ID"
  type        = string
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key"
  type        = string
}

variable "control_plane_count" {
  description = "Number of control plane nodes (1, 3, or 5 for HA)"
  type        = number
  default     = 1

  validation {
    condition     = contains([1, 3, 5], var.control_plane_count)
    error_message = "Control plane count must be 1, 3, or 5 for proper etcd quorum."
  }
}

variable "control_plane_size" {
  description = "Droplet size for control plane nodes"
  type        = string
  default     = "s-2vcpu-4gb"
}

variable "worker_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 2
}

variable "worker_size" {
  description = "Droplet size for worker nodes"
  type        = string
  default     = "s-2vcpu-4gb"
}

variable "droplet_image" {
  description = "Droplet image (OS)"
  type        = string
  default     = "ubuntu-22-04-x64"
}

variable "enable_monitoring" {
  description = "Enable DigitalOcean monitoring"
  type        = bool
  default     = true
}
