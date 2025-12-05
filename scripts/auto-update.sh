#!/bin/bash
# =============================================================================
# StudyBuddy Auto-Update Script
# =============================================================================
# This script pulls the latest changes from git and restarts the application
# Can be run manually or via cron/webhook
# =============================================================================

# Configuration
INSTALL_DIR="${INSTALL_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
LOG_FILE="${LOG_FILE:-/var/log/studybuddy-update.log}"
BRANCH="${BRANCH:-master}"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$LOG_FILE"
}

# Ensure we're in the right directory
cd "$INSTALL_DIR" || {
    log_error "Failed to change to directory: $INSTALL_DIR"
    exit 1
}

log_info "Starting auto-update process..."
log_info "Working directory: $INSTALL_DIR"

# Check if git repo
if [ ! -d ".git" ]; then
    log_error "Not a git repository"
    exit 1
fi

# Stash any local changes
log_info "Stashing local changes..."
git stash push -u -m "Auto-update stash $(date +%s)" 2>&1 | tee -a "$LOG_FILE"

# Fetch latest changes
log_info "Fetching latest changes from origin..."
if ! git fetch origin 2>&1 | tee -a "$LOG_FILE"; then
    log_error "Failed to fetch from origin"
    exit 1
fi

# Check if updates available
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/$BRANCH)

if [ "$LOCAL" = "$REMOTE" ]; then
    log_success "Already up to date ($(git rev-parse --short HEAD))"
    exit 0
fi

log_info "Updates found: $LOCAL -> $REMOTE"

# Backup .env file
if [ -f ".env" ]; then
    log_info "Backing up .env file..."
    cp .env .env.backup.$(date +%s)
fi

# Pull changes (support force push scenarios)
log_info "Pulling changes..."
if ! git pull origin $BRANCH 2>&1 | tee -a "$LOG_FILE"; then
    # Check if this is a force push scenario using git rev-list
    # If local has commits not in remote and vice versa, history diverged
    LOCAL_ONLY=$(git rev-list HEAD..origin/$BRANCH 2>/dev/null | wc -l)
    REMOTE_ONLY=$(git rev-list origin/$BRANCH..HEAD 2>/dev/null | wc -l)
    
    if [ "$LOCAL_ONLY" -gt 0 ] && [ "$REMOTE_ONLY" -gt 0 ]; then
        log_info "Detected force push (diverged history) - resetting to remote branch..."
        if git reset --hard origin/$BRANCH 2>&1 | tee -a "$LOG_FILE"; then
            log_success "Successfully reset to remote branch"
        else
            log_error "Failed to reset to remote branch"
            exit 1
        fi
    else
        log_error "Failed to pull changes"
        # Restore from stash if available
        if git stash list | grep -q "Auto-update stash"; then
            log_info "Attempting to restore from stash..."
            git stash pop
        fi
        exit 1
    fi
fi

# Restore .env if it was overwritten
if ls .env.backup.* >/dev/null 2>&1; then
    LATEST_BACKUP=$(ls -t .env.backup.* 2>/dev/null | head -1)
    if [ -f "$LATEST_BACKUP" ]; then
        log_info "Restoring .env from backup..."
        cp "$LATEST_BACKUP" .env
    fi
fi

# Check if docker-compose.yml changed
if git diff --name-only $LOCAL $REMOTE | grep -q "docker-compose.yml\|Dockerfile\|requirements.txt"; then
    log_info "Infrastructure files changed, rebuilding containers..."
    REBUILD="--build"
else
    REBUILD=""
fi

# Restart the application
log_info "Restarting application..."

# If running as systemd service
if systemctl is-active --quiet studybuddy 2>/dev/null; then
    log_info "Restarting via systemd..."
    sudo systemctl restart studybuddy 2>&1 | tee -a "$LOG_FILE"
    
    # Wait for service to be ready
    sleep 5
    
    if systemctl is-active --quiet studybuddy; then
        log_success "Service restarted successfully"
    else
        log_error "Service failed to restart"
        sudo systemctl status studybuddy | tee -a "$LOG_FILE"
        exit 1
    fi
# Otherwise use docker compose directly
elif command -v docker compose &> /dev/null || command -v docker-compose &> /dev/null; then
    log_info "Restarting via docker compose..."
    docker compose down 2>&1 | tee -a "$LOG_FILE"
    docker compose up -d $REBUILD 2>&1 | tee -a "$LOG_FILE"
    
    # Wait for containers to be ready
    sleep 10
    
    if docker compose ps | grep -q "Up"; then
        log_success "Containers restarted successfully"
    else
        log_error "Containers failed to start"
        docker compose logs --tail=50 | tee -a "$LOG_FILE"
        exit 1
    fi
else
    log_error "Neither systemd service nor docker compose available"
    exit 1
fi

# Verify application is responding
log_info "Verifying application health..."
sleep 5

# Try to reach health endpoint
if curl -sf http://localhost:5000/health > /dev/null 2>&1; then
    log_success "Application is healthy"
elif curl -sf http://localhost/health > /dev/null 2>&1; then
    log_success "Application is healthy (via proxy)"
else
    log_error "Application health check failed"
    log_info "Check logs: docker compose logs"
fi

log_success "Update completed successfully!"
log_info "Previous version: $(git rev-parse --short $LOCAL)"
log_info "Current version: $(git rev-parse --short HEAD)"

# Clean up old backups (keep last 5)
find . -name ".env.backup.*" -type f | sort -r | tail -n +6 | xargs rm -f 2>/dev/null

exit 0
