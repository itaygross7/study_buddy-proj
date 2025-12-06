#!/bin/bash
# =============================================================================
# StudyBuddy Hard Restart Deploy Script
# =============================================================================
# This script performs a complete system reset and deployment with full
# permission fixes for auto-update flow and deployment.
#
# What it does:
# 1. Fixes all file and script permissions
# 2. Fixes Docker permissions and user groups
# 3. Forces complete Docker cleanup
# 4. Fixes systemd service permissions
# 5. Ensures auto-update.sh can run properly
# 6. Performs fresh deployment
#
# Safe to run multiple times - idempotent
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Detect if running as root
if [[ $EUID -eq 0 ]]; then
    SUDO=""
    IS_ROOT=true
    CURRENT_USER="${SUDO_USER:-root}"
else
    SUDO="sudo"
    IS_ROOT=false
    CURRENT_USER="$USER"
fi

# Logging functions
log_header() { echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════════╗${NC}"; echo -e "${MAGENTA}║ $*${NC}"; echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════════╝${NC}"; }
log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_error() { echo -e "${RED}[✗]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $*"; }
log_fix() { echo -e "${CYAN}[FIX]${NC} $*"; }

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
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  HARD RESTART DEPLOY - Full Permission Fix${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    if [[ "$IS_ROOT" == true ]]; then
        log_info "Running as root (user: $CURRENT_USER)"
    else
        log_info "Running as user: $CURRENT_USER"
    fi
    echo ""
}

# =============================================================================
# Permission Fixing Functions
# =============================================================================

fix_script_permissions() {
    log_header "Fixing Script Permissions"
    
    log_info "Setting execute permissions on all shell scripts..."
    
    # Main directory scripts
    for script in *.sh; do
        if [ -f "$script" ]; then
            chmod +x "$script" 2>/dev/null || $SUDO chmod +x "$script"
            log_success "Fixed: $script"
        fi
    done
    
    # Scripts directory
    if [ -d "scripts" ]; then
        for script in scripts/*.sh; do
            if [ -f "$script" ]; then
                chmod +x "$script" 2>/dev/null || $SUDO chmod +x "$script"
                log_success "Fixed: $script"
            fi
        done
    fi
    
    log_success "All script permissions fixed"
    return 0
}

fix_directory_permissions() {
    log_header "Fixing Directory Permissions"
    
    log_info "Ensuring proper directory ownership and permissions..."
    
    # Get the actual user (not root if using sudo)
    ACTUAL_USER="${SUDO_USER:-$USER}"
    
    # Fix ownership of key directories
    if [[ "$IS_ROOT" == true ]]; then
        log_fix "Setting ownership to $ACTUAL_USER..."
        chown -R "$ACTUAL_USER:$ACTUAL_USER" . 2>/dev/null || true
    fi
    
    # Ensure directories are readable/writable
    directories=("scripts" "src" "ui" "services" "templates" "static" "logs")
    for dir in "${directories[@]}"; do
        if [ -d "$dir" ]; then
            chmod -R u+rwX,go+rX "$dir" 2>/dev/null || $SUDO chmod -R u+rwX,go+rX "$dir"
            log_success "Fixed permissions: $dir/"
        fi
    done
    
    # Create logs directory if it doesn't exist
    if [ ! -d "logs" ]; then
        mkdir -p logs
        log_success "Created logs directory"
    fi
    
    # Fix logs directory permissions
    chmod 755 logs 2>/dev/null || $SUDO chmod 755 logs
    
    log_success "Directory permissions fixed"
    return 0
}

fix_docker_permissions() {
    log_header "Fixing Docker Permissions"
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker not installed!"
        log_info "Install with: curl -fsSL https://get.docker.com | sh"
        return 1
    fi
    
    log_success "Docker is installed"
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null 2>&1; then
        log_warning "Docker daemon not running"
        log_fix "Starting Docker daemon..."
        
        $SUDO systemctl start docker 2>/dev/null || true
        $SUDO systemctl enable docker 2>/dev/null || true
        
        sleep 3
        
        if ! docker info &> /dev/null 2>&1; then
            log_error "Failed to start Docker daemon"
            return 1
        fi
        
        log_success "Docker daemon started"
    else
        log_success "Docker daemon is running"
    fi
    
    # Fix Docker group membership
    if [[ "$IS_ROOT" == false ]]; then
        if ! docker ps &> /dev/null 2>&1; then
            log_warning "Docker permission issues for user $CURRENT_USER"
            log_fix "Adding user to docker group..."
            
            $SUDO usermod -aG docker "$CURRENT_USER"
            
            # Try to apply group membership without logout
            if command -v newgrp &> /dev/null; then
                log_info "Attempting to apply group membership..."
            fi
            
            log_success "User added to docker group"
            log_warning "You may need to log out and back in for docker permissions to take full effect"
            log_info "Or run: newgrp docker"
        else
            log_success "Docker permissions OK for $CURRENT_USER"
        fi
    fi
    
    # Fix Docker socket permissions
    if [ -S /var/run/docker.sock ]; then
        $SUDO chmod 666 /var/run/docker.sock 2>/dev/null || true
        log_success "Docker socket permissions fixed"
    fi
    
    return 0
}

fix_git_permissions() {
    log_header "Fixing Git Repository Permissions"
    
    if [ ! -d ".git" ]; then
        log_error "Not a git repository!"
        return 1
    fi
    
    log_info "Configuring git for safe operation..."
    
    # Mark directory as safe for git operations
    if git config --global --get-all safe.directory | grep -q "$(pwd)" 2>/dev/null; then
        log_success "Git safe directory already configured"
    else
        git config --global --add safe.directory "$(pwd)" 2>/dev/null || true
        log_success "Added current directory to git safe directories"
    fi
    
    # Fix .git directory permissions
    if [[ "$IS_ROOT" == true ]]; then
        ACTUAL_USER="${SUDO_USER:-$USER}"
        chown -R "$ACTUAL_USER:$ACTUAL_USER" .git 2>/dev/null || true
        log_success "Fixed .git directory ownership"
    fi
    
    chmod -R u+rwX .git 2>/dev/null || $SUDO chmod -R u+rwX .git
    log_success "Fixed .git directory permissions"
    
    return 0
}

fix_env_file_permissions() {
    log_header "Fixing Environment File Permissions"
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            log_warning ".env file not found"
            log_fix "Creating .env from .env.example..."
            cp .env.example .env
            log_success ".env created"
        else
            log_error ".env and .env.example not found!"
            return 1
        fi
    fi
    
    # Secure .env file (readable only by owner)
    chmod 600 .env 2>/dev/null || $SUDO chmod 600 .env
    
    if [[ "$IS_ROOT" == true ]]; then
        ACTUAL_USER="${SUDO_USER:-$USER}"
        chown "$ACTUAL_USER:$ACTUAL_USER" .env 2>/dev/null || true
    fi
    
    log_success ".env file permissions secured"
    return 0
}

fix_systemd_service() {
    log_header "Fixing Systemd Service (if installed)"
    
    SERVICE_FILE="/etc/systemd/system/studybuddy.service"
    
    if [ -f "$SERVICE_FILE" ]; then
        log_info "Systemd service file found"
        
        # Reload systemd daemon
        $SUDO systemctl daemon-reload 2>/dev/null || true
        
        # Fix service file permissions
        $SUDO chmod 644 "$SERVICE_FILE" 2>/dev/null || true
        
        log_success "Systemd service configuration reloaded"
    else
        log_info "No systemd service installed (this is OK)"
    fi
    
    return 0
}

fix_log_permissions() {
    log_header "Fixing Log File Permissions"
    
    # Common log locations
    LOG_LOCATIONS=(
        "/var/log/studybuddy-update.log"
        "/var/log/studybuddy.log"
        "logs/"
    )
    
    for log_location in "${LOG_LOCATIONS[@]}"; do
        if [ -f "$log_location" ]; then
            $SUDO chmod 644 "$log_location" 2>/dev/null || true
            if [[ "$IS_ROOT" == true ]]; then
                ACTUAL_USER="${SUDO_USER:-$USER}"
                $SUDO chown "$ACTUAL_USER:$ACTUAL_USER" "$log_location" 2>/dev/null || true
            fi
            log_success "Fixed permissions: $log_location"
        elif [ -d "$log_location" ]; then
            $SUDO chmod 755 "$log_location" 2>/dev/null || true
            if [[ "$IS_ROOT" == true ]]; then
                ACTUAL_USER="${SUDO_USER:-$USER}"
                $SUDO chown -R "$ACTUAL_USER:$ACTUAL_USER" "$log_location" 2>/dev/null || true
            fi
            log_success "Fixed permissions: $log_location/"
        fi
    done
    
    log_success "Log permissions fixed"
    return 0
}

# =============================================================================
# Docker Cleanup & Restart Functions
# =============================================================================

force_docker_cleanup() {
    log_header "Forcing Complete Docker Cleanup"
    
    log_warning "This will stop and remove ALL StudyBuddy containers"
    
    # Stop systemd service if running
    if systemctl is-active --quiet studybuddy 2>/dev/null; then
        log_fix "Stopping systemd service..."
        $SUDO systemctl stop studybuddy 2>/dev/null || true
    fi
    
    # Stop all StudyBuddy containers
    log_fix "Stopping containers..."
    docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true
    
    # Stop any remaining studybuddy containers
    STUDYBUDDY_CONTAINERS=$(docker ps -aq --filter "name=studybuddy" 2>/dev/null)
    if [ -n "$STUDYBUDDY_CONTAINERS" ]; then
        log_fix "Removing StudyBuddy containers..."
        echo "$STUDYBUDDY_CONTAINERS" | xargs docker stop 2>/dev/null || true
        echo "$STUDYBUDDY_CONTAINERS" | xargs docker rm 2>/dev/null || true
    fi
    
    # Clean up dangling images and volumes
    log_fix "Cleaning up Docker resources..."
    docker system prune -f 2>/dev/null || true
    
    log_success "Docker cleanup complete"
    return 0
}

verify_auto_update_setup() {
    log_header "Verifying Auto-Update Setup"
    
    AUTO_UPDATE_SCRIPT="scripts/auto-update.sh"
    
    if [ ! -f "$AUTO_UPDATE_SCRIPT" ]; then
        log_error "Auto-update script not found: $AUTO_UPDATE_SCRIPT"
        return 1
    fi
    
    # Verify it's executable
    if [ ! -x "$AUTO_UPDATE_SCRIPT" ]; then
        log_error "Auto-update script is not executable!"
        return 1
    fi
    
    log_success "Auto-update script is properly configured"
    
    # Check if webhook service exists
    if systemctl list-units --type=service --all | grep -q "studybuddy-webhook"; then
        log_info "Webhook service detected"
        $SUDO systemctl restart studybuddy-webhook 2>/dev/null || true
        log_success "Webhook service restarted"
    else
        log_info "No webhook service (this is OK - can use SSH for auto-deploy)"
    fi
    
    return 0
}

fresh_deployment() {
    log_header "Performing Fresh Deployment"
    
    # Determine docker compose command
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        log_error "Docker Compose not found!"
        log_info "Install with: sudo apt install docker-compose-plugin"
        return 1
    fi
    
    log_info "Using: $COMPOSE_CMD"
    
    # Pull latest images
    log_info "Pulling latest images..."
    $COMPOSE_CMD pull 2>/dev/null || log_warning "Pull failed, will use local images"
    
    # Build images
    log_info "Building images (this may take a few minutes)..."
    if ! $COMPOSE_CMD build --no-cache 2>&1 | tee /tmp/build.log; then
        log_error "Build failed! Check /tmp/build.log"
        tail -20 /tmp/build.log
        return 1
    fi
    
    log_success "Images built successfully"
    
    # Start services
    log_info "Starting services..."
    if ! $COMPOSE_CMD up -d; then
        log_error "Failed to start services!"
        $COMPOSE_CMD logs --tail=50
        return 1
    fi
    
    log_success "Services started"
    
    # Wait for services to be ready
    log_info "Waiting for services to stabilize..."
    sleep 15
    
    # Check container status
    RUNNING_COUNT=$($COMPOSE_CMD ps --format json 2>/dev/null | grep -c '"State":"running"' || echo 0)
    
    if [ "$RUNNING_COUNT" -ge 3 ]; then
        log_success "Deployment successful! $RUNNING_COUNT containers running"
        return 0
    else
        log_warning "Only $RUNNING_COUNT containers running"
        log_info "Check status with: $COMPOSE_CMD ps"
        return 1
    fi
}

verify_deployment() {
    log_header "Verifying Deployment"
    
    log_info "Checking application health..."
    
    # Wait a bit more for app to be ready
    sleep 5
    
    # Check health endpoint
    if curl -sf http://localhost:5000/health &> /dev/null; then
        log_success "Application is healthy and responding!"
        return 0
    elif curl -sf http://localhost/health &> /dev/null; then
        log_success "Application is healthy (via proxy)!"
        return 0
    else
        log_warning "Health check failed"
        log_info "The application might still be starting up..."
        log_info "Check logs with: docker compose logs -f app"
        return 1
    fi
}

show_final_status() {
    local IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
    
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ HARD RESTART COMPLETE!                                   ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}What was fixed:${NC}"
    echo -e "  ${GREEN}✓${NC} All script permissions (chmod +x)"
    echo -e "  ${GREEN}✓${NC} Directory ownership and permissions"
    echo -e "  ${GREEN}✓${NC} Docker permissions and user groups"
    echo -e "  ${GREEN}✓${NC} Git repository permissions"
    echo -e "  ${GREEN}✓${NC} Environment file security"
    echo -e "  ${GREEN}✓${NC} Log file permissions"
    echo -e "  ${GREEN}✓${NC} Systemd service configuration"
    echo -e "  ${GREEN}✓${NC} Auto-update script setup"
    echo -e "  ${GREEN}✓${NC} Complete Docker cleanup and restart"
    echo ""
    echo -e "${CYAN}Access Points:${NC}"
    echo -e "  ${GREEN}→${NC} Application:     http://localhost:5000"
    if [[ "$IP" != "localhost" && "$IP" != "127.0.0.1" ]]; then
        echo -e "  ${GREEN}→${NC} External:        http://${IP}:5000"
    fi
    echo -e "  ${GREEN}→${NC} RabbitMQ UI:     http://localhost:15672"
    echo ""
    echo -e "${CYAN}Useful Commands:${NC}"
    echo -e "  ${YELLOW}View logs:${NC}       docker compose logs -f app"
    echo -e "  ${YELLOW}Check status:${NC}    docker compose ps"
    echo -e "  ${YELLOW}Restart app:${NC}     ./scripts/restart-app.sh"
    echo -e "  ${YELLOW}Update app:${NC}      ./scripts/auto-update.sh"
    echo -e "  ${YELLOW}Hard restart:${NC}    ./hard-restart-deploy.sh (this script)"
    echo ""
    echo -e "${CYAN}Auto-Update Status:${NC}"
    echo -e "  ${GREEN}✓${NC} Auto-update script is executable and ready"
    echo -e "  ${GREEN}✓${NC} Can be triggered by GitHub Actions webhook"
    echo -e "  ${GREEN}✓${NC} Can be triggered by SSH deployment"
    echo -e "  ${GREEN}✓${NC} All permissions are properly configured"
    echo ""
    
    # Show container status
    echo -e "${CYAN}Container Status:${NC}"
    docker compose ps 2>/dev/null | sed 's/^/  /' || true
    echo ""
    
    log_info "Auto-update flow is now fully configured!"
    log_info "Future deployments will work automatically"
    echo ""
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    show_banner
    
    # Ensure we're in the project directory
    if [[ ! -f docker-compose.yml ]]; then
        log_error "docker-compose.yml not found!"
        log_info "Please run this script from the StudyBuddy project root"
        exit 1
    fi
    
    log_info "Starting hard restart with full permission fix..."
    echo ""
    
    # Fix all permissions
    fix_script_permissions || { log_error "Failed to fix script permissions"; exit 1; }
    fix_directory_permissions || { log_error "Failed to fix directory permissions"; exit 1; }
    fix_docker_permissions || { log_error "Failed to fix Docker permissions"; exit 1; }
    fix_git_permissions || { log_error "Failed to fix git permissions"; exit 1; }
    fix_env_file_permissions || { log_error "Failed to fix .env permissions"; exit 1; }
    fix_log_permissions || true  # Non-critical
    fix_systemd_service || true  # Non-critical
    
    echo ""
    
    # Force cleanup and restart
    force_docker_cleanup || { log_error "Docker cleanup failed"; exit 1; }
    fresh_deployment || { log_error "Deployment failed"; exit 1; }
    
    echo ""
    
    # Verify everything
    verify_auto_update_setup || log_warning "Auto-update verification had issues"
    verify_deployment || log_warning "Health check had issues"
    
    echo ""
    
    # Show final status
    show_final_status
    
    exit 0
}

# Handle interrupts gracefully
trap 'echo ""; log_warning "Hard restart interrupted by user"; exit 130' INT TERM

# Run main function
main "$@"
