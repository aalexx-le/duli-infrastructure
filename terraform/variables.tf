# Shared Kubernetes Cluster Variables

variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "DigitalOcean region"
  type        = string
  default     = "sgp1"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.20.0.0/16"
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key (relative to project root)"
  type        = string
  default     = ".ssh/duli-ai-k8s.pub"
}

variable "control_plane_count" {
  description = "Number of control plane nodes"
  type        = number
  default     = 1
}

variable "control_plane_size" {
  description = "Droplet size for control plane"
  type        = string
  default     = "s-2vcpu-4gb"
}

variable "worker_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 3
}

variable "worker_size" {
  description = "Droplet size for workers"
  type        = string
  default     = "s-2vcpu-4gb"
}

variable "enable_monitoring" {
  description = "Enable DigitalOcean monitoring"
  type        = bool
  default     = true
}

# ============================================================================
# CLOUDFLARE CONFIGURATION
# ============================================================================

variable "cloudflare_api_token" {
  description = "Cloudflare API Token for managing Access applications"
  type        = string
  sensitive   = true
}

variable "cloudflare_account_id" {
  description = "Cloudflare Account ID"
  type        = string
  default     = "9c0d91907036918bc0ae212ed139dd1f"
}
