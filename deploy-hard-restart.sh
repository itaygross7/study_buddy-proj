#!/bin/bash
# =============================================================================
# StudyBuddy Hard Restart Deploy Script
# =============================================================================
# This script performs a complete hard restart of the deployment:
# - Fixes ALL permissions (Git, Docker, files, services)
# - Cleans Docker state completely
# - Rebuilds and restarts all services from scratch
# - Verifies the auto-update flow is properly configured
# 
# Use this when:
# - Auto-update is failing due to permission issues
# - Docker permissions are broken
# - The system is in an inconsistent state
# - You need a complete reset without losing data
#
# Usage:
#   ./deploy-hard-restart.sh
#
# Requirements:
#   - Must be run from repository root
#   - User needs sudo access
# =============================================================================

set -e  # Exit on any error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/tmp/studybuddy-hard-restart-$(date +%Y%m%d-%H%M%S).log"

# Logging functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log_info() { 
    echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$LOG_FILE"
}

log_success() { 
    echo -e "${GREEN}[✓]${NC} $*" | tee -a "$LOG_FILE"
}

log_error() { 
    echo -e "${RED}[✗]${NC} $*" | tee -a "$LOG_FILE"
}

log_warning() { 
    echo -e "${YELLOW}[!]${NC} $*" | tee -a "$LOG_FILE"
}

log_fix() { 
    echo -e "${CYAN}[FIX]${NC} $*" | tee -a "$LOG_FILE"
}

log_section() {
    echo "" | tee -a "$LOG_FILE"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════${NC}" | tee -a "$LOG_FILE"
    echo -e "${MAGENTA}  $*${NC}" | tee -a "$LOG_FILE"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════════${NC}" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
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
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  HARD RESTART DEPLOY - Fix All Permissions & Reset${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    log_info "Log file: $LOG_FILE"
    echo ""
}

# =============================================================================
# Pre-flight Checks
# =============================================================================

check_prerequisites() {
    log_section "Pre-flight Checks"
    
    # Check if running from repo root
    if [ ! -d "$SCRIPT_DIR/.git" ]; then
        log_error "Not a git repository! This script must be run from repository root."
        exit 1
    fi
    log_success "Running from repository root: $SCRIPT_DIR"
    
    # Check sudo access
    if ! sudo -n true 2>/dev/null; then
        log_warning "This script requires sudo access"
        log_info "You may be prompted for your password"
        sudo -v
    fi
    log_success "Sudo access confirmed"
    
    # Check if .env exists
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        log_warning ".env file not found"
        if [ -f "$SCRIPT_DIR/.env.example" ]; then
            log_fix "Creating .env from .env.example"
            cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
            log_warning "Please edit .env with your configuration before proceeding"
            read -p "Press Enter when ready to continue..."
        else
            log_error ".env.example not found. Cannot continue."
            exit 1
        fi
    fi
    log_success ".env file exists"
    
    # Load environment variables from .env
    if [ -f "$SCRIPT_DIR/.env" ]; then
        export $(grep -v '^#' "$SCRIPT_DIR/.env" | grep -v '^[[:space:]]*$' | xargs -0)
    fi
    
    # Show current user
    log_info "Current user: $USER"
    log_info "Home directory: $HOME"
}

# =============================================================================
# Fix Git Permissions
# =============================================================================

fix_git_permissions() {
    log_section "Fixing Git Repository Permissions"
    
    cd "$SCRIPT_DIR"
    
    # Ensure current user owns the repository
    log_fix "Setting repository ownership to $USER:$USER"
    sudo chown -R "$USER:$USER" "$SCRIPT_DIR"
    log_success "Repository ownership fixed"
    
    # Fix .git directory permissions
    log_fix "Fixing .git directory permissions"
    chmod -R u+rwX,go+rX,go-w "$SCRIPT_DIR/.git"
    log_success ".git permissions fixed"
    
    # Make all .sh files executable
    log_fix "Making all shell scripts executable"
    find "$SCRIPT_DIR" -type f -name "*.sh" -exec chmod +x {} \;
    log_success "Shell scripts are now executable"
    
    # Verify git configuration
    log_info "Checking Git configuration..."
    
    # Set safe directory to avoid dubious ownership errors
    git config --global --add safe.directory "$SCRIPT_DIR" 2>/dev/null || true
    
    # Check if we can run git commands
    if git status &> /dev/null; then
        log_success "Git is working correctly"
        CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
        CURRENT_COMMIT=$(git rev-parse --short HEAD)
        log_info "Branch: $CURRENT_BRANCH"
        log_info "Commit: $CURRENT_COMMIT"
        
        # Pull latest changes
        log_fix "Pulling latest changes from repository"
        if sudo git pull origin "$CURRENT_BRANCH" 2>&1 | tee -a "$LOG_FILE"; then
            NEW_COMMIT=$(git rev-parse --short HEAD)
            if [ "$CURRENT_COMMIT" != "$NEW_COMMIT" ]; then
                log_success "Updated from $CURRENT_COMMIT to $NEW_COMMIT"
            else
                log_success "Already up to date"
            fi
        else
            log_warning "Git pull failed, but continuing with current version..."
        fi
    else
        log_warning "Git status check failed, but continuing..."
    fi
    
    # Ensure scripts directory is executable
    if [ -d "$SCRIPT_DIR/scripts" ]; then
        log_fix "Fixing scripts directory permissions"
        chmod +x "$SCRIPT_DIR/scripts"/*.sh 2>/dev/null || true
        log_success "Scripts directory fixed"
    fi
}

# =============================================================================
# Fix Docker Permissions
# =============================================================================

fix_docker_permissions() {
    log_section "Fixing Docker Permissions"
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed!"
        log_info "Install Docker first: curl -fsSL https://get.docker.com | sudo sh"
        exit 1
    fi
    log_success "Docker is installed"
    
    # Check Docker daemon
    if ! sudo systemctl is-active --quiet docker; then
        log_fix "Starting Docker daemon"
        sudo systemctl start docker
        sudo systemctl enable docker
        sleep 3
    fi
    
    if sudo systemctl is-active --quiet docker; then
        log_success "Docker daemon is running"
    else
        log_error "Docker daemon failed to start"
        exit 1
    fi
    
    # Fix Docker group permissions
    log_fix "Adding $USER to docker group"
    sudo usermod -aG docker "$USER"
    
    # Check if user can run docker commands
    if docker ps &> /dev/null; then
        log_success "User can run Docker commands without sudo"
    else
        log_warning "Docker group membership updated"
        log_warning "To apply group changes, you have three options:"
        log_info "  1. Run: newgrp docker (then re-run this script)"
        log_info "  2. Logout and login again"
        log_info "  3. Continue with sudo (will work but less convenient)"
        echo ""
        read -p "Try to continue with newgrp? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Re-executing script with newgrp..."
            exec sg docker "$0 $@"
        fi
    fi
    
    # Verify docker-compose/docker compose
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
        log_success "docker-compose is available"
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
        log_success "docker compose is available"
    else
        log_error "Neither docker-compose nor docker compose is available"
        exit 1
    fi
    
    export COMPOSE_CMD
}

# =============================================================================
# Fix File and Directory Permissions
# =============================================================================

fix_file_permissions() {
    log_section "Fixing File and Directory Permissions"
    
    cd "$SCRIPT_DIR"
    
    # Ensure logs directory exists and is writable
    log_fix "Setting up logs directory"
    sudo mkdir -p /var/log/studybuddy
    sudo chown "$USER:$USER" /var/log/studybuddy
    sudo chmod 755 /var/log/studybuddy
    log_success "Logs directory configured"
    
    # Fix auto-update script permissions
    if [ -f "$SCRIPT_DIR/scripts/auto-update.sh" ]; then
        log_fix "Fixing auto-update script permissions"
        chmod +x "$SCRIPT_DIR/scripts/auto-update.sh"
        log_success "auto-update.sh is executable"
    fi
    
    if [ -f "$SCRIPT_DIR/update_app.sh" ]; then
        log_fix "Fixing update_app.sh permissions"
        chmod +x "$SCRIPT_DIR/update_app.sh"
        log_success "update_app.sh is executable"
    fi
    
    # Fix restart script permissions
    if [ -f "$SCRIPT_DIR/scripts/restart-app.sh" ]; then
        chmod +x "$SCRIPT_DIR/scripts/restart-app.sh"
        log_success "restart-app.sh is executable"
    fi
    
    # Ensure data directories have correct permissions
    log_fix "Checking data directory permissions"
    
    # These might be created by Docker, so we check and fix if needed
    if [ -d "$SCRIPT_DIR/data" ]; then
        sudo chown -R "$USER:$USER" "$SCRIPT_DIR/data" 2>/dev/null || true
    fi
    
    log_success "File permissions fixed"
}

# =============================================================================
# Clean Docker State
# =============================================================================

clean_docker_state() {
    log_section "Cleaning Docker State"
    
    cd "$SCRIPT_DIR"
    
    log_warning "This will stop and remove all StudyBuddy containers"
    log_warning "Data in volumes will be PRESERVED"
    echo ""
    read -p "Continue with Docker cleanup? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        log_info "Skipping Docker cleanup"
        return
    fi
    
    # Stop all StudyBuddy containers
    log_fix "Stopping all StudyBuddy containers"
    $COMPOSE_CMD down 2>&1 | tee -a "$LOG_FILE" || log_warning "No containers to stop"
    log_success "Containers stopped"
    
    # Remove StudyBuddy containers
    log_fix "Removing StudyBuddy containers"
    docker ps -a --filter "name=studybuddy" --format "{{.ID}}" | xargs -r docker rm -f 2>&1 | tee -a "$LOG_FILE" || true
    log_success "Old containers removed"
    
    # Remove dangling images
    log_fix "Removing dangling images"
    docker image prune -f 2>&1 | tee -a "$LOG_FILE" || true
    log_success "Dangling images removed"
    
    # Show Docker disk usage
    log_info "Current Docker disk usage:"
    docker system df | tee -a "$LOG_FILE"
    echo ""
    
    read -p "Do you want to prune unused Docker resources? (build cache, unused networks) (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_fix "Pruning Docker system (this may take a moment)..."
        docker system prune -f 2>&1 | tee -a "$LOG_FILE"
        log_success "Docker system pruned"
    else
        log_info "Skipped Docker system prune"
    fi
}

# =============================================================================
# Fix Systemd Service Permissions (if applicable)
# =============================================================================

fix_systemd_permissions() {
    log_section "Checking Systemd Service"
    
    # Check if systemd service exists
    if [ -f "/etc/systemd/system/studybuddy.service" ]; then
        log_info "Found studybuddy systemd service"
        
        log_fix "Reloading systemd daemon"
        sudo systemctl daemon-reload
        log_success "Systemd daemon reloaded"
        
        # Check service status
        if sudo systemctl is-active --quiet studybuddy; then
            log_info "Service is currently running"
            read -p "Stop and disable systemd service? (Y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                log_fix "Stopping systemd service"
                sudo systemctl stop studybuddy
                sudo systemctl disable studybuddy
                log_success "Systemd service stopped and disabled"
                log_info "This script will use Docker Compose directly"
            fi
        else
            log_info "Service is not running"
        fi
    else
        log_info "No systemd service found (this is normal for Docker-only deployments)"
    fi
}

# =============================================================================
# Rebuild and Restart Services
# =============================================================================

rebuild_services() {
    log_section "Rebuilding and Starting Services"
    
    cd "$SCRIPT_DIR"
    
    # Pull latest base images
    log_fix "Pulling latest base images"
    $COMPOSE_CMD pull 2>&1 | tee -a "$LOG_FILE" || log_warning "Some images could not be pulled"
    
    # Build with no cache to ensure clean build
    log_fix "Building services from scratch (this will take a few minutes)..."
    $COMPOSE_CMD build --no-cache 2>&1 | tee -a "$LOG_FILE"
    log_success "Services built successfully"
    
    # Start services
    log_fix "Starting all services"
    $COMPOSE_CMD up -d 2>&1 | tee -a "$LOG_FILE"
    log_success "Services started"
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready (30 seconds)..."
    sleep 30
    
    # Check service status
    log_info "Service status:"
    $COMPOSE_CMD ps | tee -a "$LOG_FILE"
}

# =============================================================================
# Send Email Notification
# =============================================================================

send_email_notification() {
    local subject="$1"
    local message="$2"
    
    # Check if ADMIN_EMAIL is configured
    if [ -z "$ADMIN_EMAIL" ] || [ "$ADMIN_EMAIL" == "your_admin_email@example.com" ]; then
        log_info "Email notification not sent - ADMIN_EMAIL not configured"
        return 0
    fi
    
    log_info "Sending email notification to $ADMIN_EMAIL"
    
    # Create Python script to send email
    python3 << EOF
import sys
import os
sys.path.insert(0, '$SCRIPT_DIR')

# Set required environment variables for config
os.environ.setdefault('SECRET_KEY', 'notification-temp-key')
os.environ.setdefault('MONGO_URI', 'mongodb://localhost:27017/temp')
os.environ.setdefault('RABBITMQ_URI', 'amqp://localhost:5672/')

try:
    from src.services.email_service import send_email
    
    html_body = """
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
            <h2 style="margin: 0;">🦫 StudyBuddy Deployment Notification</h2>
        </div>
        <div style="background: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; border-radius: 0 0 10px 10px;">
            <h3 style="color: #28a745;">$subject</h3>
            <p style="color: #495057; line-height: 1.6;">$message</p>
            <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
            <p style="color: #6c757d; font-size: 12px; margin: 0;">
                Server: $(hostname)<br>
                Time: $(date '+%Y-%m-%d %H:%M:%S')<br>
                User: $USER
            </p>
        </div>
    </body>
    </html>
    """
    
    text_body = """
StudyBuddy Deployment Notification

$subject

$message

Server: $(hostname)
Time: $(date '+%Y-%m-%d %H:%M:%S')
User: $USER
    """
    
    result = send_email('$ADMIN_EMAIL', '$subject', html_body, text_body)
    sys.exit(0 if result else 1)
except Exception as e:
    print(f"Failed to send email: {e}", file=sys.stderr)
    sys.exit(1)
EOF
    
    if [ $? -eq 0 ]; then
        log_success "Email notification sent successfully"
    else
        log_warning "Failed to send email notification (this is non-critical)"
    fi
}

# =============================================================================
# Verify Deployment
# =============================================================================

verify_deployment() {
    log_section "Verifying Deployment"
    
    # Check if containers are running
    log_info "Checking container status..."
    
    CONTAINERS=$($COMPOSE_CMD ps -q)
    if [ -z "$CONTAINERS" ]; then
        log_error "No containers are running!"
        return 1
    fi
    
    RUNNING_COUNT=$($COMPOSE_CMD ps | grep -c "Up" || echo "0")
    log_info "Running containers: $RUNNING_COUNT"
    
    # Check health endpoint
    log_info "Checking application health..."
    sleep 5
    
    MAX_RETRIES=6
    RETRY_COUNT=0
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -sf http://localhost:5000/health > /dev/null 2>&1; then
            log_success "✓ Application health check passed!"
            
            # Get detailed health if available
            if curl -sf http://localhost:5000/health/detailed > /tmp/health.json 2>&1; then
                log_info "Detailed health check:"
                cat /tmp/health.json | tee -a "$LOG_FILE"
                rm -f /tmp/health.json
            fi
            
            return 0
        fi
        
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            log_info "Health check attempt $RETRY_COUNT/$MAX_RETRIES failed, retrying in 10s..."
            sleep 10
        fi
    done
    
    log_warning "Health check failed after $MAX_RETRIES attempts"
    log_info "Check logs with: $COMPOSE_CMD logs -f app"
    return 1
}

# =============================================================================
# Configure Auto-Update
# =============================================================================

configure_auto_update() {
    log_section "Configuring Auto-Update"
    
    log_info "Auto-update can be configured to run automatically via cron"
    log_info "The auto-update script is: $SCRIPT_DIR/scripts/auto-update.sh"
    
    if [ ! -f "$SCRIPT_DIR/scripts/auto-update.sh" ]; then
        log_warning "Auto-update script not found!"
        return
    fi
    
    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "auto-update.sh"; then
        log_info "Cron job for auto-update already exists:"
        crontab -l | grep "auto-update.sh" | tee -a "$LOG_FILE"
    else
        log_info "No auto-update cron job found"
        echo ""
        read -p "Would you like to set up automatic updates? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_fix "Setting up auto-update cron job"
            
            # Create cron job to run daily at 3 AM
            CRON_JOB="0 3 * * * $SCRIPT_DIR/scripts/auto-update.sh >> /var/log/studybuddy/auto-update.log 2>&1"
            
            (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
            log_success "Auto-update scheduled for daily 3 AM"
            log_info "Logs will be in: /var/log/studybuddy/auto-update.log"
        else
            log_info "Skipped auto-update setup"
            log_info "To update manually, run: ./scripts/auto-update.sh"
        fi
    fi
}

# =============================================================================
# Show Final Summary
# =============================================================================

show_summary() {
    log_section "Hard Restart Complete!"
    
    echo -e "${GREEN}┌─────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${GREEN}│                   DEPLOYMENT SUMMARY                        │${NC}"
    echo -e "${GREEN}└─────────────────────────────────────────────────────────────┘${NC}"
    echo ""
    
    log_success "All permissions have been fixed:"
    echo "  ✓ Git repository ownership and permissions"
    echo "  ✓ Docker group membership"
    echo "  ✓ File and directory permissions"
    echo "  ✓ Shell script executable permissions"
    echo "  ✓ Auto-update flow configured"
    echo ""
    
    log_success "Services have been rebuilt and started:"
    echo "  ✓ Docker containers rebuilt from scratch"
    echo "  ✓ All services are running"
    echo "  ✓ Health checks passed"
    echo ""
    
    log_info "Access your application:"
    echo "  • Web App: http://localhost:5000"
    echo "  • RabbitMQ: http://localhost:15672 (user/password from .env)"
    echo ""
    
    log_info "Useful commands:"
    echo "  • View logs:        $COMPOSE_CMD logs -f app"
    echo "  • Restart services: $COMPOSE_CMD restart"
    echo "  • Stop services:    $COMPOSE_CMD down"
    echo "  • Update app:       ./scripts/auto-update.sh"
    echo "  • Manual restart:   ./scripts/restart-app.sh"
    echo ""
    
    log_info "Full log saved to: $LOG_FILE"
    echo ""
    
    # Show next steps
    echo -e "${CYAN}Next steps:${NC}"
    echo "  1. Test the application at http://localhost:5000"
    echo "  2. Check logs: $COMPOSE_CMD logs -f app"
    echo "  3. Test auto-update: ./scripts/auto-update.sh"
    echo ""
    
    # Warning about logout if needed
    if ! docker ps &> /dev/null; then
        log_warning "Docker group changes require logout/login to take full effect"
        log_info "For now, you may need to use 'sudo' with docker commands"
        log_info "Or run: newgrp docker"
    fi
    
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    show_banner
    
    log "Starting hard restart deploy process"
    START_TIME=$(date +%s)
    
    # Run all steps
    check_prerequisites
    fix_git_permissions
    fix_docker_permissions
    fix_file_permissions
    clean_docker_state
    fix_systemd_permissions
    rebuild_services
    
    # Verify everything works
    if verify_deployment; then
        configure_auto_update
        
        # Send success notification email
        send_email_notification \
            "✅ StudyBuddy Hard Restart Completed Successfully" \
            "The StudyBuddy application has been successfully rebuilt and restarted. All services are running and health checks passed. The application is now accessible at http://localhost:5000"
        
        show_summary
        
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        log_success "Total time: ${DURATION}s"
        
        exit 0
    else
        # Send failure notification email
        send_email_notification \
            "⚠️ StudyBuddy Hard Restart - Verification Failed" \
            "The StudyBuddy application was rebuilt but health checks failed. Please check the logs at: $LOG_FILE"
        
        log_error "Deployment verification failed"
        log_info "Check logs: $COMPOSE_CMD logs -f"
        log_info "Full log: $LOG_FILE"
        exit 1
    fi
}

# Trap errors
trap 'log_error "Script failed at line $LINENO"' ERR

# Run main function
main "$@"
