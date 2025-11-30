# Variables for Production Environment

variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "region" {
  description = "DigitalOcean region"
  type        = string
  default     = "sgp1"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.30.0.0/16"
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key"
  type        = string
  default     = "../../../.ssh/duli_prod.pub"
}

variable "control_plane_count" {
  description = "Number of control plane nodes (must be 3 for HA)"
  type        = number
  default     = 3
}

variable "control_plane_size" {
  description = "Droplet size for control plane"
  type        = string
  default     = "s-4vcpu-8gb"
}

variable "worker_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 5
}

variable "worker_size" {
  description = "Droplet size for workers"
  type        = string
  default     = "s-4vcpu-8gb"
}

variable "enable_monitoring" {
  description = "Enable DigitalOcean monitoring"
  type        = bool
  default     = true
}
