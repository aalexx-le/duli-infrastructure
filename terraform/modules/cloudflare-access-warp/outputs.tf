# ============================================================================
# MODULE: cloudflare-access-warp
# Outputs for Zero Trust Access Applications with WARP Authentication
# ============================================================================

output "application_ids" {
  description = "Map of application names to their Cloudflare IDs"
  value       = { for app in cloudflare_zero_trust_access_application.app : app.name => app.id }
}

output "application_account_ids" {
  description = "Map of application names to their Cloudflare Account IDs"
  value       = { for app in cloudflare_zero_trust_access_application.app : app.name => app.account_id }
}

output "warp_enabled_applications" {
  description = "List of application names with WARP authentication enabled"
  value       = [for app in cloudflare_zero_trust_access_application.app : app.name if app.allow_authenticate_via_warp]
}

output "application_domains" {
  description = "Map of application names to their domains"
  value       = { for app in cloudflare_zero_trust_access_application.app : app.name => app.domain }
}

output "application_details" {
  description = "Detailed information about all created applications"
  value = {
    for app in cloudflare_zero_trust_access_application.app : app.name => {
      id                       = app.id
      domain                   = app.domain
      allow_authenticate_via_warp = app.allow_authenticate_via_warp
      session_duration         = app.session_duration
      app_launcher_visible     = app.app_launcher_visible
      enable_binding_cookie    = app.enable_binding_cookie
    }
  }
}

output "connection_info" {
  description = "Connection information for accessing applications via WARP"
  value = {
    postgres_staging = "psql -h db.staging.duli.one -p 5432 -U duli_user -d app"
    redis_staging    = "redis-cli -h redis.staging.duli.one -p 6379"
    rabbitmq_staging = "amqp://user:password@mq.staging.duli.one:5672"
    postgres_prod    = "psql -h db.duli.one -p 5432 -U duli_user -d app"
    redis_prod       = "redis-cli -h redis.duli.one -p 6379"
    rabbitmq_prod    = "amqp://user:password@mq.duli.one:5672"
  }
}
