# Variables for Networking Module

variable "region" {
  description = "DigitalOcean region"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
}
