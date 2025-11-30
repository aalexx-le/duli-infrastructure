# Variables for Networking Module

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}

variable "region" {
  description = "DigitalOcean region"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
}
