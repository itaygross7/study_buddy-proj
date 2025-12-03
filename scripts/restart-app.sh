#!/bin/bash
# =============================================================================
# StudyBuddy Restart Script
# =============================================================================
# Simple script to restart the StudyBuddy application
# Can be run manually or scheduled
# =============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_error() { echo -e "${RED}[✗]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $*"; }

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] [COMPONENT]

Restart StudyBuddy application or specific components.

COMPONENT:
    all         Restart all services (default)
    app         Restart only the Flask application
    worker      Restart only the background worker
    mongo       Restart only MongoDB
    rabbitmq    Restart only RabbitMQ
    caddy       Restart only Caddy reverse proxy

OPTIONS:
    -h, --help      Show this help message
    -r, --rebuild   Rebuild containers before restarting
    
EXAMPLES:
    $0                  # Restart all services
    $0 app              # Restart only the app
    $0 --rebuild        # Rebuild and restart all
    $0 -r app           # Rebuild and restart app only

EOF
}

# Parse arguments
REBUILD=""
COMPONENT="all"

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -r|--rebuild)
            REBUILD="--build"
            shift
            ;;
        app|worker|mongo|rabbitmq|caddy|all)
            COMPONENT=$1
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

log_info "Restarting StudyBuddy: $COMPONENT"

# Check if running as systemd service
if systemctl is-active --quiet studybuddy 2>/dev/null; then
    log_info "Using systemd service..."
    
    if [ "$COMPONENT" = "all" ]; then
        sudo systemctl restart studybuddy
        sleep 5
        
        if systemctl is-active --quiet studybuddy; then
            log_success "StudyBuddy service restarted successfully"
        else
            log_error "Service failed to restart"
            sudo systemctl status studybuddy
            exit 1
        fi
    else
        log_warning "Systemd service is active. Use 'docker compose restart $COMPONENT' for specific components."
        log_info "Or restart the entire service with: sudo systemctl restart studybuddy"
        exit 1
    fi
    
elif command -v docker compose &> /dev/null || command -v docker-compose &> /dev/null; then
    log_info "Using docker compose..."
    
    if [ "$COMPONENT" = "all" ]; then
        docker compose restart $REBUILD
    else
        docker compose restart $REBUILD "$COMPONENT"
    fi
    
    # Wait for services to start
    sleep 5
    
    # Check status
    if docker compose ps | grep -q "Up"; then
        log_success "Services restarted successfully"
        docker compose ps
    else
        log_error "Some services failed to start"
        docker compose ps
        docker compose logs --tail=20
        exit 1
    fi
    
else
    log_error "Neither systemd service nor docker compose found"
    exit 1
fi

# Health check
log_info "Checking application health..."
sleep 3

if curl -sf http://localhost:5000/health > /dev/null 2>&1; then
    log_success "Application is healthy"
elif curl -sf http://localhost/health > /dev/null 2>&1; then
    log_success "Application is healthy (via proxy)"
else
    log_warning "Health check failed. Check logs: docker compose logs -f"
fi

log_success "Restart complete!"
