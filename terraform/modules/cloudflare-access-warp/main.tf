# ============================================================================
# MODULE: cloudflare-access-warp
# Main configuration for Cloudflare Access Applications with WARP
# ============================================================================
# This module creates/updates Cloudflare Access applications with
# WARP authentication enabled.
# ============================================================================

terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.52"
    }
  }
}

# Create or update each Zero Trust Access application with WARP enabled
# Uses the modern cloudflare_zero_trust_access_application resource
resource "cloudflare_zero_trust_access_application" "app" {
  for_each = { for app in var.applications : app.name => app }

  account_id                      = var.account_id
  name                            = each.value.name
  domain                          = each.value.domain
  session_duration                = each.value.session_duration
  auto_redirect_to_identity       = each.value.auto_redirect_to_identity
  enable_binding_cookie           = each.value.enable_binding_cookie
  skip_interstitial               = each.value.skip_interstitial
  app_launcher_visible            = each.value.app_launcher_visible
  service_auth_401_redirect       = each.value.service_auth_401_redirect
  custom_deny_message             = each.value.custom_deny_message
  allow_authenticate_via_warp     = var.enable_warp_on_all
  http_only_cookie_attribute      = var.http_only_cookie_attribute
  same_site_cookie_attribute      = var.same_site_cookie_attribute

  cors_headers {
    allowed_methods   = each.value.cors_allowed_methods
    allowed_origins   = each.value.cors_allowed_origins
    # NOTE: Cloudflare security policy: cannot allow credentials with wildcard origins (*)
    # If origins contains "*", credentials are automatically set to false
    allow_credentials = contains(each.value.cors_allowed_origins, "*") ? false : each.value.cors_allow_credentials
    max_age           = each.value.cors_max_age
  }

  lifecycle {
    ignore_changes = [
      # Ignore changes to policies managed by separate policy resources
      # This allows independent policy management via cloudflare_zero_trust_access_policy
      policies,
      # Ignore tags since they may not exist in Cloudflare
      tags
    ]
  }
}

# Create allow-all policies for each application
# Users with WARP client connected and authenticated can access
resource "cloudflare_zero_trust_access_policy" "allow_all" {
  for_each = { for app in var.applications : app.name => app }

  account_id     = var.account_id
  application_id = cloudflare_zero_trust_access_application.app[each.key].id
  name           = "${each.value.name} - Allow All WARP Users"
  precedence     = 1
  decision       = "allow"

  # Allow everyone with WARP enabled on the application
  include {
    everyone = true
  }
}
