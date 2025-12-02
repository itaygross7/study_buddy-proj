#!/bin/bash
# =============================================================================
# StudyBuddyAI One-Click Deployment Script
# =============================================================================
# Tested on: Ubuntu 22.04 LTS (also works on Ubuntu 20.04+, Debian, and other Linux distributions)
#
# This is the main deployment script that:
# 1. Runs comprehensive pre-deployment checks
# 2. Handles environment setup
# 3. Builds and starts all Docker services
# 4. Validates the deployment
# 5. Provides helpful status information
#
# Usage:
#   ./deploy.sh [OPTIONS]
#
# Options:
#   --skip-checks    Skip pre-deployment checks (not recommended)
#   --rebuild        Force rebuild of all images
#   --clean          Remove all existing containers and volumes (fresh start)
#   --check-only     Only run checks, don't deploy
#   --help           Show this help message
#
# =============================================================================

set -e  # Exit on error (will be temporarily disabled for checks)

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
PRE_CHECK_SCRIPT="$PROJECT_ROOT/scripts/pre-deploy-check.sh"

# Options (defaults)
SKIP_CHECKS=false
FORCE_REBUILD=false
CLEAN_START=false
CHECK_ONLY=false

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
}

log_error() {
    echo -e "${RED}[✗]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $*"
}

section_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $*${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
}

show_banner() {
    clear
    echo -e "${GREEN}"
    cat << "EOF"
   _____ _             _       ____            _     _       
  / ____| |           | |     |  _ \          | |   | |      
 | (___ | |_ _   _  __| |_   _| |_) |_   _  __| | __| |_   _ 
  \___ \| __| | | |/ _` | | | |  _ <| | | |/ _` |/ _` | | | |
  ____) | |_| |_| | (_| | |_| | |_) | |_| | (_| | (_| | |_| |
 |_____/ \__|\__,_|\__,_|\__, |____/ \__,_|\__,_|\__,_|\__, |
                          __/ |                         __/ |
                         |___/                         |___/ 
EOF
    echo -e "${NC}"
    echo -e "${CYAN}One-Click Deployment Script${NC}"
    echo ""
}

show_help() {
    cat << EOF
StudyBuddyAI Deployment Script

Usage: ./deploy.sh [OPTIONS]

Options:
  --skip-checks    Skip pre-deployment checks (not recommended)
  --rebuild        Force rebuild of all Docker images
  --clean          Remove all existing containers and volumes (fresh start)
  --check-only     Only run checks, don't deploy
  --help           Show this help message

Examples:
  ./deploy.sh                    # Normal deployment with checks
  ./deploy.sh --rebuild          # Force rebuild all images
  ./deploy.sh --clean            # Fresh start (removes all data!)
  ./deploy.sh --check-only       # Only run system checks

For more information, visit: https://github.com/itaygross7/study_buddy-proj
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-checks)
                SKIP_CHECKS=true
                shift
                ;;
            --rebuild)
                FORCE_REBUILD=true
                shift
                ;;
            --clean)
                CLEAN_START=true
                shift
                ;;
            --check-only)
                CHECK_ONLY=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
}

# Run pre-deployment checks
run_checks() {
    section_header "Pre-Deployment Checks"
    
    if [[ ! -f "$PRE_CHECK_SCRIPT" ]]; then
        log_error "Pre-check script not found: $PRE_CHECK_SCRIPT"
        exit 1
    fi
    
    # Make sure the script is executable
    chmod +x "$PRE_CHECK_SCRIPT"
    
    # Run the checks (temporarily allow errors)
    set +e
    bash "$PRE_CHECK_SCRIPT"
    CHECK_RESULT=$?
    set -e
    
    if [[ $CHECK_RESULT -ne 0 ]]; then
        echo ""
        log_error "Pre-deployment checks failed"
        log_warning "Fix the issues above or use --skip-checks to proceed anyway (not recommended)"
        exit 1
    fi
    
    log_success "All pre-deployment checks passed"
}

# Setup environment
setup_environment() {
    section_header "Environment Setup"
    
    cd "$PROJECT_ROOT"
    
    # Check if .env exists, if not create from example
    if [[ ! -f .env ]]; then
        if [[ -f .env.example ]]; then
            log_warning ".env file not found, creating from .env.example"
            cp .env.example .env
            log_warning "Please edit .env file with your configuration before continuing"
            log_info "Required: Set SECRET_KEY, ADMIN_EMAIL, and at least one API key"
            echo ""
            read -p "Press Enter after you've configured .env, or Ctrl+C to cancel..."
        else
            log_error ".env.example not found"
            exit 1
        fi
    else
        log_success ".env file exists"
    fi
    
    # Determine docker-compose command
    if docker compose version &> /dev/null; then
        export COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        export COMPOSE_CMD="docker-compose"
    else
        log_error "Docker Compose not found"
        exit 1
    fi
    
    log_info "Using: $COMPOSE_CMD"
}

# Clean existing deployment
clean_deployment() {
    section_header "Cleaning Existing Deployment"
    
    log_warning "This will remove all containers and volumes (DATA LOSS!)"
    read -p "Are you sure? Type 'yes' to confirm: " -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "Clean cancelled"
        return
    fi
    
    log_info "Stopping and removing containers..."
    $COMPOSE_CMD down -v --remove-orphans 2>/dev/null || true
    
    log_info "Removing StudyBuddy images..."
    docker images | grep studybuddy | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null || true
    
    log_info "Pruning unused Docker resources..."
    docker system prune -f 2>/dev/null || true
    
    log_success "Cleanup completed"
}

# Build and start services
deploy_services() {
    section_header "Building and Starting Services"
    
    cd "$PROJECT_ROOT"
    
    BUILD_FLAGS="--build"
    if [[ "$FORCE_REBUILD" == true ]]; then
        BUILD_FLAGS="--build --no-cache"
        log_info "Force rebuild enabled (no cache)"
    fi
    
    log_info "Building Docker images..."
    $COMPOSE_CMD build --pull 2>&1 | sed 's/^/  /'
    
    log_info "Starting services..."
    $COMPOSE_CMD up -d $BUILD_FLAGS 2>&1 | sed 's/^/  /'
    
    log_success "Services started"
}

# Wait for services to be healthy
wait_for_services() {
    section_header "Waiting for Services"
    
    log_info "Waiting for services to be healthy (this may take 30-60 seconds)..."
    
    MAX_WAIT=120
    ELAPSED=0
    INTERVAL=5
    
    while [[ $ELAPSED -lt $MAX_WAIT ]]; do
        # Check container health
        UNHEALTHY=$($COMPOSE_CMD ps --format json 2>/dev/null | grep -c '"Health":"unhealthy"' || echo 0)
        STARTING=$($COMPOSE_CMD ps --format json 2>/dev/null | grep -c '"Health":"starting"' || echo 0)
        
        if [[ $UNHEALTHY -eq 0 && $STARTING -eq 0 ]]; then
            log_success "All services are healthy"
            return 0
        fi
        
        echo -n "."
        sleep $INTERVAL
        ELAPSED=$((ELAPSED + INTERVAL))
    done
    
    echo ""
    log_warning "Some services may not be fully healthy yet"
    log_info "Check status with: $COMPOSE_CMD ps"
}

# Validate deployment
validate_deployment() {
    section_header "Deployment Validation"
    
    # Check if containers are running
    RUNNING_CONTAINERS=$($COMPOSE_CMD ps --format json 2>/dev/null | grep -c '"State":"running"' || echo 0)
    
    if [[ $RUNNING_CONTAINERS -ge 4 ]]; then
        log_success "All containers are running ($RUNNING_CONTAINERS)"
    else
        log_warning "Only $RUNNING_CONTAINERS containers running (expected 4+)"
    fi
    
    # Try to access the health endpoint
    log_info "Testing application health endpoint..."
    sleep 5  # Give the app a moment to start
    
    if curl -sf http://localhost:5000/health > /dev/null 2>&1; then
        log_success "Application is responding"
    else
        log_warning "Application health check failed (may still be starting)"
        log_info "Wait a moment and try: curl http://localhost:5000/health"
    fi
}

# Show deployment info
show_deployment_info() {
    section_header "Deployment Complete!"
    
    echo ""
    echo -e "${GREEN}✓ StudyBuddyAI is now running!${NC}"
    echo ""
    echo -e "${CYAN}Access Points:${NC}"
    
    # Get the actual IP address
    IP_ADDRESS=$(hostname -I | awk '{print $1}')
    
    echo -e "  ${GREEN}→${NC} Application:       http://localhost:5000"
    if [[ -n "$IP_ADDRESS" && "$IP_ADDRESS" != "127.0.0.1" ]]; then
        echo -e "  ${GREEN}→${NC} External Access:   http://${IP_ADDRESS}:5000"
    fi
    echo -e "  ${GREEN}→${NC} RabbitMQ Manager:  http://localhost:15672 (user/password from .env)"
    echo ""
    
    echo -e "${CYAN}Useful Commands:${NC}"
    echo -e "  ${YELLOW}View logs:${NC}         $COMPOSE_CMD logs -f app"
    echo -e "  ${YELLOW}View all logs:${NC}     $COMPOSE_CMD logs -f"
    echo -e "  ${YELLOW}Check status:${NC}      $COMPOSE_CMD ps"
    echo -e "  ${YELLOW}Stop services:${NC}     $COMPOSE_CMD down"
    echo -e "  ${YELLOW}Restart:${NC}           $COMPOSE_CMD restart"
    echo ""
    
    echo -e "${CYAN}Container Status:${NC}"
    $COMPOSE_CMD ps 2>/dev/null || true
    echo ""
    
    # Show logs tail
    echo -e "${CYAN}Recent Application Logs:${NC}"
    $COMPOSE_CMD logs --tail=10 app 2>/dev/null | sed 's/^/  /' || true
    echo ""
    
    log_info "For more information, see: README.md"
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    show_banner
    parse_args "$@"
    
    # Show configuration
    log_info "Deployment Configuration:"
    log_info "  Skip Checks:    $SKIP_CHECKS"
    log_info "  Force Rebuild:  $FORCE_REBUILD"
    log_info "  Clean Start:    $CLEAN_START"
    log_info "  Check Only:     $CHECK_ONLY"
    echo ""
    
    # Run pre-deployment checks unless skipped
    if [[ "$SKIP_CHECKS" != true ]]; then
        run_checks
    else
        log_warning "Skipping pre-deployment checks"
    fi
    
    # Exit if check-only mode
    if [[ "$CHECK_ONLY" == true ]]; then
        log_info "Check-only mode - exiting without deployment"
        exit 0
    fi
    
    # Setup environment
    setup_environment
    
    # Clean if requested
    if [[ "$CLEAN_START" == true ]]; then
        clean_deployment
    fi
    
    # Deploy services
    deploy_services
    
    # Wait for services
    wait_for_services
    
    # Validate
    validate_deployment
    
    # Show info
    show_deployment_info
    
    log_success "Deployment completed successfully!"
    exit 0
}

# Handle errors
trap 'log_error "Deployment failed at line $LINENO. Check the logs above."' ERR

# Run main
main "$@"
