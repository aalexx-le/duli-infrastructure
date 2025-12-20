# ============================================================================
# MODULE: cloudflare-access-warp
# Variables for Zero Trust Access Applications with WARP Authentication
# ============================================================================

variable "account_id" {
  description = "Cloudflare Account ID"
  type        = string
}

variable "applications" {
  description = "List of Zero Trust Access applications to create/update with WARP"
  type = list(object({
    name                      = string
    domain                    = string
    session_duration          = string
    auto_redirect_to_identity = bool
    enable_binding_cookie     = bool
    skip_interstitial         = bool
    app_launcher_visible      = bool
    service_auth_401_redirect = bool
    custom_deny_message       = string
    cors_allowed_methods      = list(string)
    cors_allowed_origins      = list(string)
    cors_allow_credentials    = bool
    cors_max_age              = number
  }))

  validation {
    condition = alltrue([
      for app in var.applications : can(regex("^[a-z0-9.-]+$", app.domain))
    ])
    error_message = "All application domains must be valid domain names."
  }
}

variable "enable_warp_on_all" {
  description = "Enable allow_authenticate_via_warp on all applications"
  type        = bool
  default     = true
}

variable "http_only_cookie_attribute" {
  description = "Enable HttpOnly cookie attribute for increased XSS protection"
  type        = bool
  default     = true
}

variable "same_site_cookie_attribute" {
  description = "SameSite cookie attribute setting (strict, lax, or none)"
  type        = string
  default     = "strict"

  validation {
    condition     = contains(["strict", "lax", "none"], var.same_site_cookie_attribute)
    error_message = "SameSite cookie attribute must be 'strict', 'lax', or 'none'."
  }
}

variable "tags" {
  description = "Tags for the applications"
  type        = list(string)
  default     = ["terraform-managed", "cloudflare-access-warp"]
}
