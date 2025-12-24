#!/bin/bash
# Setup RBAC access for a new team member

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 <username> <role> [namespace]"
    echo ""
    echo "Roles:"
    echo "  - viewer: Read-only access to staging and prod"
    echo "  - developer: Deploy access to staging only"
    echo "  - admin: Full admin access to specified namespace"
    echo "  - cluster-viewer: Read-only cluster-wide access"
    echo ""
    echo "Examples:"
    echo "  $0 john.doe@example.com viewer"
    echo "  $0 jane.smith@example.com developer staging"
    echo "  $0 devops@example.com admin prod"
    exit 1
fi

USERNAME=$1
ROLE=$2
NAMESPACE=${3:-""}

print_info "Setting up RBAC for user: $USERNAME with role: $ROLE"

# Create temporary RBAC file
TEMP_FILE=$(mktemp)
trap "rm -f $TEMP_FILE" EXIT

case $ROLE in
    viewer)
        print_info "Creating viewer role in staging..."
        kubectl apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: viewer-binding-$USERNAME
  namespace: staging
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: viewer
subjects:
  - kind: User
    name: "$USERNAME"
    apiGroup: rbac.authorization.k8s.io
EOF
        
        print_info "Creating viewer role in prod..."
        kubectl apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: viewer-binding-$USERNAME
  namespace: prod
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: viewer
subjects:
  - kind: User
    name: "$USERNAME"
    apiGroup: rbac.authorization.k8s.io
EOF
        ;;
    
    developer)
        if [ -z "$NAMESPACE" ]; then
            NAMESPACE="staging"
        fi
        
        print_info "Creating developer role in $NAMESPACE..."
        kubectl apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer-binding-$USERNAME
  namespace: $NAMESPACE
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: developer
subjects:
  - kind: User
    name: "$USERNAME"
    apiGroup: rbac.authorization.k8s.io
EOF
        ;;
    
    admin)
        if [ -z "$NAMESPACE" ]; then
            print_error "Admin role requires namespace argument"
            exit 1
        fi
        
        print_info "Creating admin role in $NAMESPACE..."
        kubectl apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: admin-binding-$USERNAME
  namespace: $NAMESPACE
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: admin
subjects:
  - kind: User
    name: "$USERNAME"
    apiGroup: rbac.authorization.k8s.io
EOF
        ;;
    
    cluster-viewer)
        print_info "Creating cluster-viewer role..."
        kubectl apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: cluster-viewer-binding-$USERNAME
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-viewer
subjects:
  - kind: User
    name: "$USERNAME"
    apiGroup: rbac.authorization.k8s.io
EOF
        ;;
    
    *)
        print_error "Unknown role: $ROLE"
        exit 1
        ;;
esac

print_info "✅ RBAC setup complete for $USERNAME"
print_info ""
print_info "Verify access with:"
echo "  kubectl auth can-i get pods --as=$USERNAME -n staging"
echo "  kubectl auth can-i create deployments --as=$USERNAME -n staging"
echo ""

