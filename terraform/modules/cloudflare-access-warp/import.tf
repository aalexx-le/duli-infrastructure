# ============================================================================
# IMPORT EXISTING CLOUDFLARE ACCESS APPLICATIONS
# ============================================================================
# This file helps import existing Cloudflare Access applications into Terraform state
# This is needed when applications were created outside of Terraform

# Note: The applications appear to already exist in Cloudflare
# Use the import commands below to add them to Terraform state

# Import command format:
# terraform import 'module.cloudflare_access_warp.cloudflare_zero_trust_access_application.app["ApplicationName"]' 'account_id/application_id'

# Examples:
# terraform import 'module.cloudflare_access_warp.cloudflare_zero_trust_access_application.app["PostgreSQL Staging"]' '9c0d91907036918bc0ae212ed139dd1f/app-id-here'
# terraform import 'module.cloudflare_access_warp.cloudflare_zero_trust_access_application.app["PostgreSQL Production"]' '9c0d91907036918bc0ae212ed139dd1f/app-id-here'
# ... and so on for each application

# To get the application IDs, visit:
# https://one.dash.cloudflare.com/9c0d91907036918bc0ae212ed139dd1f/access-controls/apps
