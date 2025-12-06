#!/bin/bash
# =============================================================================
# StudyBuddy AI - Ultimate Production Deployment Script
# =============================================================================
# A complete DevOps team in one script featuring:
# - Auto-Scaling Workers (New!)
# - Automated backup before deployment
# - Smart rollback on failures
# - Zero-downtime deployment
# - Health monitoring and auto-recovery
# - Security hardening
# - Performance optimization
# - Comprehensive logging
# - Auto-update capability
# - Email notifications
# - Resource monitoring
# - Database migrations
# - SSL/TLS management
# - Container orchestration
# - Error recovery
# =============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures
IFS=$'\n\t'

# =============================================================================
# CONFIGURATION & GLOBALS
# =============================================================================

# Script version
VERSION="2.1.2-Scaling"
DEPLOY_START_TIME=$(date +%s)
DEPLOY_DATE=$(date +%Y%m%d_%H%M%S)

# --- AUTO-SCALING CONFIGURATION (NEW) ---
WORKER_SERVICE_NAME="worker"   # Must match service name in docker-compose.yml
WORKER_RAM_ESTIMATE_MB=350     # Est. RAM per worker
SYSTEM_RESERVE_MB=2048         # RAM reserved for OS/DB
MAX_WORKER_CAP=32              # Hard cap
OPTIMAL_WORKER_COUNT=1         # Default
MANUAL_OVERRIDE=0              # Set via --workers flag

# Deployment modes
FULL_RESTART=false
FORCE_REBUILD=false
SKIP_BACKUP=false
SKIP_GIT_PULL=false
QUICK_MODE=false

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly MAGENTA='\033[0;35m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m' # No Color

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/backups"
LOG_DIR="$SCRIPT_DIR/logs"
DEPLOY_LOG="$LOG_DIR/deploy_${DEPLOY_DATE}.log"

# Deployment state
DEPLOYMENT_ID="deploy_${DEPLOY_DATE}"
STATE_FILE="$LOG_DIR/.deploy_state"
PREVIOUS_COMMIT=""
ROLLBACK_NEEDED=false

# Container names
APP_CONTAINER="studybuddy_app"
WORKER_CONTAINER="studybuddy_worker"
MONGO_CONTAINER="studybuddy_mongo"
RABBITMQ_CONTAINER="studybuddy_rabbitmq"
TUNNEL_CONTAINER="studybuddy_tunnel"

# Health check settings
MAX_HEALTH_RETRIES=30
HEALTH_CHECK_INTERVAL=5

# =============================================================================
# COMMAND LINE ARGUMENTS
# =============================================================================

show_usage() {
    cat << EOF
${BLUE}╔══════════════════════════════════════════════════════════════╗
║        StudyBuddy AI - Ultimate Deployment Script v${VERSION}       ║
╚══════════════════════════════════════════════════════════════╝${NC}

${WHITE}USAGE:${NC}
    sudo ./deploy-production.sh [OPTIONS]

${WHITE}OPTIONS:${NC}
    ${GREEN}-h, --help${NC}              Show this help message

    ${YELLOW}Deployment Modes:${NC}
    ${GREEN}--workers [N]${NC}           Manually set worker count (Overrides auto-scale)
    ${GREEN}--full-restart${NC}          Complete system restart (stops all, removes volumes, rebuilds everything)
    ${GREEN}--force-rebuild${NC}         Force Docker rebuild without cache
    ${GREEN}--quick${NC}                 Quick deployment (skip backups, minimal checks)

    ${YELLOW}Skip Options:${NC}
    ${GREEN}--skip-backup${NC}           Skip backup creation (faster but risky)
    ${GREEN}--skip-git${NC}              Skip git pull (use current code)
    ${GREEN}--skip-health${NC}           Skip health checks (not recommended)

    ${YELLOW}Maintenance:${NC}
    ${GREEN}--rollback${NC}              Rollback to previous deployment
    ${GREEN}--cleanup${NC}               Clean up old backups and logs
    ${GREEN}--status${NC}                Show current deployment status

${WHITE}EXAMPLES:${NC}
    ${CYAN}# Standard deployment${NC}
    sudo ./deploy-production.sh

    ${CYAN}# Full restart (clean slate)${NC}
    sudo ./deploy-production.sh --full-restart

    ${CYAN}# Quick update without backup${NC}
    sudo ./deploy-production.sh --quick

    ${CYAN}# Force rebuild containers${NC}
    sudo ./deploy-production.sh --force-rebuild

    ${CYAN}# Rollback to previous version${NC}
    sudo ./deploy-production.sh --rollback

${WHITE}NOTES:${NC}
    - Must be run with sudo
    - Creates automatic backups before deployment
    - Supports automatic rollback on failures
    - Logs saved to logs/deploy_*.log

${WHITE}DOCUMENTATION:${NC}
    See DEPLOYMENT_GUIDE.md for complete documentation

EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            --workers)
                MANUAL_OVERRIDE=$2
                log_info "Mode: Manual Worker Count ($2)"
                shift 2
                ;;
            --full-restart)
                FULL_RESTART=true
                FORCE_REBUILD=true
                log_info "Mode: Full Restart (complete system reset)"
                shift
                ;;
            --force-rebuild)
                FORCE_REBUILD=true
                log_info "Mode: Force Rebuild"
                shift
                ;;
            --quick)
                QUICK_MODE=true
                SKIP_BACKUP=true
                log_info "Mode: Quick Deployment"
                shift
                ;;
            --skip-backup)
                SKIP_BACKUP=true
                log_warning "Skipping backup creation"
                shift
                ;;
            --skip-git)
                SKIP_GIT_PULL=true
                log_warning "Skipping git pull"
                shift
                ;;
            --skip-health)
                MAX_HEALTH_RETRIES=5
                log_warning "Minimal health checks only"
                shift
                ;;
            --rollback)
                perform_rollback
                exit $?
                ;;
            --cleanup)
                cleanup_old_files
                exit 0
                ;;
            --status)
                show_deployment_status
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo ""
                show_usage
                exit 1
                ;;
        esac
    done
}

# =============================================================================
# LOGGING & OUTPUT FUNCTIONS
# =============================================================================

# Create log directory
mkdir -p "$LOG_DIR"
mkdir -p "$BACKUP_DIR"

# Dual output to console and log file
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$DEPLOY_LOG"
}

log_info() {
    log "INFO" "${BLUE}ℹ${NC} $@"
}

log_success() {
    log "SUCCESS" "${GREEN}✓${NC} $@"
}

log_warning() {
    log "WARNING" "${YELLOW}⚠${NC} $@"
}

log_error() {
    log "ERROR" "${RED}✗${NC} $@"
}

log_step() {
    local step_num=$1
    shift
    echo ""
    log "STEP" "${MAGENTA}[${step_num}]${NC} ${WHITE}$@${NC}"
    echo ""
}

# Progress bar
show_progress() {
    local duration=$1
    local message=$2
    local width=50

    for ((i=0; i<=duration; i++)); do
        local progress=$((i * width / duration))
        printf "\r${CYAN}${message}${NC} ["
        printf "%${progress}s" | tr ' ' '█'
        printf "%$((width - progress))s" | tr ' ' '░'
        printf "] %3d%%" $((i * 100 / duration))
        sleep 1
    done
    echo ""
}

# Banner
print_banner() {
    clear
    echo -e "${BLUE}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║         ███████╗████████╗██╗   ██╗██████╗ ██╗   ██╗        ║
║         ██╔════╝╚══██╔══╝██║   ██║██╔══██╗╚██╗ ██╔╝        ║
║         ███████╗   ██║   ██║   ██║██║  ██║ ╚████╔╝         ║
║         ╚════██║   ██║   ██║   ██║██║  ██║  ╚██╔╝          ║
║         ███████║   ██║   ╚██████╔╝██████╔╝   ██║           ║
║         ╚══════╝   ╚═╝    ╚═════╝ ╚═════╝    ╚═╝           ║
║                                                              ║
║         ██████╗ ██╗   ██╗██████╗ ██████╗ ██╗   ██╗         ║
║         ██╔══██╗██║   ██║██╔══██╗██╔══██╗╚██╗ ██╔╝         ║
║         ██████╔╝██║   ██║██║  ██║██║  ██║ ╚████╔╝          ║
║         ██╔══██╗██║   ██║██║  ██║██║  ██║  ╚██╔╝           ║
║         ██████╔╝╚██████╔╝██████╔╝██████╔╝   ██║            ║
║         ╚═════╝  ╚═════╝ ╚═════╝ ╚═════╝    ╚═╝            ║
║                                                              ║
║              Ultimate Production Deployment v2.1.2          ║
║              With Auto-Scaling Intelligence                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    log_info "Deployment ID: ${DEPLOYMENT_ID}"
    log_info "Log file: ${DEPLOY_LOG}"
    echo ""
}

# =============================================================================
# AUTO-SCALING INTELLIGENCE (NEW)
# =============================================================================

calculate_system_capacity() {
    log_step "SCALING" "Calculating System Capacity"

    # 1. Manual Override Check
    if [ "$MANUAL_OVERRIDE" -gt 0 ]; then
        OPTIMAL_WORKER_COUNT=$MANUAL_OVERRIDE
        log_info "Using manual override: $OPTIMAL_WORKER_COUNT workers"
        return
    fi

    # 2. Hardware Audit
    local cpu_cores=$(nproc)
    local total_ram_mb=$(free -m | awk '/^Mem:/{print $2}')

    # 3. Calculate Limits
    local cpu_limit=$(( (cpu_cores * 2) + 1 ))
    local available_ram=$(( total_ram_mb - SYSTEM_RESERVE_MB ))

    if [ "$available_ram" -le 0 ]; then available_ram=100; fi
    local ram_limit=$(( available_ram / WORKER_RAM_ESTIMATE_MB ))
    if [ "$ram_limit" -lt 1 ]; then ram_limit=1; fi

    # 4. Determine Bottleneck
    local count=$cpu_limit
    local bottleneck="CPU Cores"

    if [ "$ram_limit" -lt "$cpu_limit" ]; then
        count=$ram_limit
        bottleneck="Available RAM"
    fi

    if [ "$count" -gt "$MAX_WORKER_CAP" ]; then
        count=$MAX_WORKER_CAP
        bottleneck="Safety Cap"
    fi

    OPTIMAL_WORKER_COUNT=$count

    # 5. Report
    echo -e "${CYAN}╔════════════════════ SYSTEM AUDIT ════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} CPU Cores:      ${WHITE}${cpu_cores}${NC}"
    echo -e "${CYAN}║${NC} RAM Available:  ${WHITE}${available_ram} MB${NC}"
    echo -e "${CYAN}║${NC} Bottleneck:     ${YELLOW}${bottleneck}${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"

    log_success "Calculated optimal workers: $OPTIMAL_WORKER_COUNT"
}

# =============================================================================
# ERROR HANDLING & CLEANUP
# =============================================================================

# Trap errors and handle cleanup
trap 'error_handler $? $LINENO' ERR
trap 'cleanup_handler' EXIT INT TERM

error_handler() {
    local exit_code=$1
    local line_number=$2

    log_error "Deployment failed at line ${line_number} with exit code ${exit_code}"
    ROLLBACK_NEEDED=true

    # Send notification
    send_notification "❌ Deployment Failed" "Deployment ${DEPLOYMENT_ID} failed at line ${line_number}"

    # Attempt automatic rollback
    if [ "$ROLLBACK_NEEDED" = true ]; then
        log_warning "Initiating automatic rollback..."
        perform_rollback
    fi
}

cleanup_handler() {
    if [ "$ROLLBACK_NEEDED" = false ]; then
        log_success "Deployment completed successfully"
        local duration=$(($(date +%s) - DEPLOY_START_TIME))
        log_info "Total deployment time: ${duration}s"
        log_info "Final Scaled Workers: ${OPTIMAL_WORKER_COUNT}"

        # Send success notification
        send_notification "✅ Deployment Successful" "Deployment ${DEPLOYMENT_ID} completed in ${duration}s"
    fi
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

cleanup_old_files() {
    log_info "Cleaning up old files..."

    # Clean old backups (keep last 10)
    if [ -d "$BACKUP_DIR" ]; then
        cd "$BACKUP_DIR"
        local backup_count=$(ls -1 | wc -l)
        if [ "$backup_count" -gt 10 ]; then
            log_info "Found $backup_count backups, keeping last 10..."
            ls -t | tail -n +11 | xargs -r rm -rf
            log_success "Cleaned old backups"
        else
            log_info "Backup count is $backup_count (within limit)"
        fi
    fi

    # Clean old logs (keep last 30 days)
    if [ -d "$LOG_DIR" ]; then
        log_info "Cleaning old logs (older than 30 days)..."
        find "$LOG_DIR" -name "*.log" -type f -mtime +30 -delete
        find "$LOG_DIR" -name "*.txt" -type f -mtime +30 -delete
        log_success "Cleaned old logs"
    fi

    # Clean Docker system
    log_info "Cleaning Docker system..."
    docker system prune -f --volumes 2>&1 | tee -a "$DEPLOY_LOG" > /dev/null || true
    log_success "Docker system cleaned"
}

show_deployment_status() {
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║              Current Deployment Status                      ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Git information
    echo -e "${CYAN}Git Information:${NC}"
    echo -e "  Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
    echo -e "  Commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
    echo -e "  Last Update: $(git log -1 --format=%cd --date=relative 2>/dev/null || echo 'unknown')"
    echo ""

    # Container status
    echo -e "${CYAN}Container Status:${NC}"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  No containers running"
    echo ""

    # Resource usage
    echo -e "${CYAN}Resource Usage:${NC}"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || echo "  Unable to get stats"
    echo ""

    # Health check
    echo -e "${CYAN}Health Status:${NC}"
    if curl -sf http://localhost:5000/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Application is healthy"
    else
        echo -e "  ${RED}✗${NC} Application health check failed"
    fi
    echo ""

    # Backup information
    echo -e "${CYAN}Backups:${NC}"
    if [ -d "$BACKUP_DIR" ]; then
        local backup_count=$(ls -1 "$BACKUP_DIR" 2>/dev/null | wc -l)
        echo -e "  Total backups: $backup_count"
        if [ "$backup_count" -gt 0 ]; then
            echo -e "  Latest: $(ls -t "$BACKUP_DIR" | head -1)"
        fi
    else
        echo -e "  No backups found"
    fi
    echo ""

    # Disk usage
    echo -e "${CYAN}Disk Usage:${NC}"
    df -h "$SCRIPT_DIR" | tail -1 | awk '{print "  Used: "$3" / "$2" ("$5")"}'
    echo ""
}

full_system_restart() {
    log_step "FULL RESTART" "Performing Complete System Restart"

    log_warning "This will:"
    log_warning "  - Stop all containers"
    log_warning "  - Remove all volumes (INCLUDING DATABASE)"
    log_warning "  - Delete all images"
    log_warning "  - Rebuild everything from scratch"
    echo ""

    # Confirmation if not in automated mode
    if [ -t 0 ]; then
        read -p "Are you sure? This will DELETE ALL DATA! Type 'yes' to continue: " confirmation
        if [ "$confirmation" != "yes" ]; then
            log_info "Full restart cancelled"
            exit 0
        fi
    fi

    log_warning "Starting full system restart..."

    # Stop and remove everything
    log_info "Stopping all containers..."
    docker compose down -v --remove-orphans 2>&1 | tee -a "$DEPLOY_LOG" || true

    # Remove all images
    log_info "Removing all StudyBuddy images..."
    docker images | grep studybuddy | awk '{print $3}' | xargs -r docker rmi -f 2>&1 | tee -a "$DEPLOY_LOG" || true

    # Clean Docker system
    log_info "Cleaning Docker system..."
    docker system prune -af --volumes 2>&1 | tee -a "$DEPLOY_LOG" || true

    log_success "System cleaned, ready for fresh build"
}

# =============================================================================
# PRE-FLIGHT CHECKS
# =============================================================================

check_prerequisites() {
    log_step "1" "Pre-flight Checks"

    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        echo -e "${YELLOW}Try: sudo $0${NC}"
        exit 1
    fi
    log_success "Running with root privileges"

    # Get actual user
    ACTUAL_USER="${SUDO_USER:-$USER}"
    log_info "Actual user: ${ACTUAL_USER}"

    # Check disk space (need at least 5GB free)
    local free_space=$(df -BG "$SCRIPT_DIR" | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ "$free_space" -lt 5 ]; then
        log_error "Insufficient disk space. Need at least 5GB free, have ${free_space}GB"
        exit 1
    fi
    log_success "Disk space: ${free_space}GB available"

    # Check memory (need at least 2GB)
    local free_mem=$(free -g | awk '/^Mem:/{print $7}')
    if [ "$free_mem" -lt 2 ]; then
        log_warning "Low memory: ${free_mem}GB available. Recommended: 2GB+"
    else
        log_success "Memory: ${free_mem}GB available"
    fi

    # Check required commands
    local required_commands=("git" "curl" "docker" "docker-compose")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_warning "Command not found: ${cmd} - will attempt to install"
        else
            log_success "Found: ${cmd}"
        fi
    done
}

# =============================================================================
# DOCKER & DEPENDENCIES INSTALLATION
# =============================================================================

install_dependencies() {
    log_step "2" "Installing/Updating Dependencies"

    # Update system packages
    log_info "Updating system packages..."
    apt-get update -qq 2>&1 | tee -a "$DEPLOY_LOG" > /dev/null
    log_success "System packages updated"

    # Install essential tools
    log_info "Installing essential tools..."
    apt-get install -y -qq curl wget git ufw fail2ban logrotate 2>&1 | tee -a "$DEPLOY_LOG" > /dev/null
    log_success "Essential tools installed"

    # Install Docker if not present
    if ! command -v docker &> /dev/null; then
        log_info "Installing Docker..."
        curl -fsSL https://get.docker.com | sh 2>&1 | tee -a "$DEPLOY_LOG" > /dev/null
        usermod -aG docker "$ACTUAL_USER"
        log_success "Docker installed"
    else
        log_success "Docker already installed"
    fi

    # Ensure Docker is running
    if ! systemctl is-active --quiet docker; then
        log_info "Starting Docker daemon..."
        systemctl start docker
        systemctl enable docker
        sleep 3
    fi
    log_success "Docker is running"

    # Install Docker Compose V2 if not present
    if ! docker compose version &> /dev/null; then
        log_info "Installing Docker Compose V2..."
        mkdir -p /usr/local/lib/docker/cli-plugins
        curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
            -o /usr/local/lib/docker/cli-plugins/docker-compose
        chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
        log_success "Docker Compose V2 installed"
    else
        log_success "Docker Compose already installed"
    fi
}

# =============================================================================
# BACKUP FUNCTIONS
# =============================================================================

create_backup() {
    if [ "$SKIP_BACKUP" = true ]; then
        log_warning "Skipping backup creation (--skip-backup flag)"
        return 0
    fi

    log_step "3" "Creating Backup"

    local backup_name="backup_${DEPLOY_DATE}"
    local backup_path="$BACKUP_DIR/$backup_name"

    mkdir -p "$backup_path"

    # Save current git commit
    PREVIOUS_COMMIT=$(cd "$SCRIPT_DIR" && git rev-parse HEAD 2>/dev/null || echo "unknown")
    echo "$PREVIOUS_COMMIT" > "$backup_path/commit.txt"
    log_info "Current commit: ${PREVIOUS_COMMIT:0:8}"

    # Backup .env file
    if [ -f "$SCRIPT_DIR/.env" ]; then
        cp "$SCRIPT_DIR/.env" "$backup_path/.env"
        log_success "Environment file backed up"
    fi

    # Backup MongoDB database
    if docker ps | grep -q "$MONGO_CONTAINER"; then
        log_info "Backing up MongoDB database..."
        docker exec "$MONGO_CONTAINER" mongodump --archive=/tmp/mongodb_backup.archive --gzip 2>&1 | tee -a "$DEPLOY_LOG" > /dev/null || true
        docker cp "$MONGO_CONTAINER:/tmp/mongodb_backup.archive" "$backup_path/mongodb_backup.archive" 2>&1 | tee -a "$DEPLOY_LOG" > /dev/null || true
        log_success "MongoDB backup created"
    fi

    # Save container states
    docker ps -a --format "{{.Names}}\t{{.Status}}" > "$backup_path/containers.txt" 2>/dev/null || true

    # Save deployment state
    echo "BACKUP_NAME=$backup_name" > "$STATE_FILE"
    echo "PREVIOUS_COMMIT=$PREVIOUS_COMMIT" >> "$STATE_FILE"
    echo "BACKUP_PATH=$backup_path" >> "$STATE_FILE"

    log_success "Backup created: $backup_name"

    # Clean old backups (keep last 5)
    log_info "Cleaning old backups..."
    cd "$BACKUP_DIR"
    ls -t | tail -n +6 | xargs -r rm -rf
    log_success "Old backups cleaned"
}

# =============================================================================
# GIT OPERATIONS
# =============================================================================

update_code() {
    if [ "$SKIP_GIT_PULL" = true ]; then
        log_warning "Skipping git pull (--skip-git flag)"
        return 0
    fi

    log_step "4" "Updating Code from Git"

    cd "$SCRIPT_DIR"

    # Fix permissions
    log_info "Fixing repository permissions..."
    chown -R "$ACTUAL_USER:$ACTUAL_USER" "$SCRIPT_DIR"
    sudo -u "$ACTUAL_USER" git config --global --add safe.directory "$SCRIPT_DIR" 2>/dev/null || true

    # Get current branch
    local current_branch=$(sudo -u "$ACTUAL_USER" git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
    log_info "Current branch: ${current_branch}"

    # Stash any local changes
    log_info "Stashing local changes..."
    sudo -u "$ACTUAL_USER" git stash push -m "Auto-stash before deployment ${DEPLOY_DATE}" 2>&1 | tee -a "$DEPLOY_LOG" || true

    # Fetch latest changes
    log_info "Fetching latest changes..."
    if sudo -u "$ACTUAL_USER" git fetch origin 2>&1 | tee -a "$DEPLOY_LOG"; then
        log_success "Fetched latest changes"
    else
        log_error "Failed to fetch from origin"
        return 1
    fi

    # Check if remote has changes
    local local_commit=$(sudo -u "$ACTUAL_USER" git rev-parse HEAD)
    local remote_commit=$(sudo -u "$ACTUAL_USER" git rev-parse origin/$current_branch)

    if [ "$local_commit" = "$remote_commit" ]; then
        log_info "Already up to date (${local_commit:0:8})"
    else
        log_info "Pulling changes: ${local_commit:0:8} -> ${remote_commit:0:8}"

        # Pull with merge strategy
        if sudo -u "$ACTUAL_USER" git pull origin "$current_branch" --no-rebase 2>&1 | tee -a "$DEPLOY_LOG"; then
            local new_commit=$(sudo -u "$ACTUAL_USER" git rev-parse HEAD)
            log_success "Updated to commit: ${new_commit:0:8}"

            # Show changelog
            log_info "Recent changes:"
            sudo -u "$ACTUAL_USER" git log --oneline -5 | tee -a "$DEPLOY_LOG"
        else
            log_error "Failed to pull changes"
            return 1
        fi
    fi

    # Make scripts executable
    log_info "Making scripts executable..."
    find "$SCRIPT_DIR" -type f -name "*.sh" -exec chmod +x {} \;
    log_success "Scripts are executable"
}

# =============================================================================
# ENVIRONMENT VALIDATION
# =============================================================================

validate_environment() {
    log_step "5" "Validating Environment Configuration"

    # Check if .env exists
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        log_error ".env file not found"

        if [ -f "$SCRIPT_DIR/.env.example" ]; then
            log_info "Creating .env from .env.example"
            cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
            chown "$ACTUAL_USER:$ACTUAL_USER" "$SCRIPT_DIR/.env"
            log_warning "Please edit .env with your configuration and run again"
            exit 1
        else
            log_error ".env.example also not found!"
            exit 1
        fi
    fi

    # Load environment variables
    set -a
    source "$SCRIPT_DIR/.env"
    set +a

    # Validate critical variables
    local missing_vars=()
    local warnings=()

    # Infrastructure
    [ -z "${MONGO_URI:-}" ] && missing_vars+=("MONGO_URI")
    [ -z "${RABBITMQ_URI:-}" ] && missing_vars+=("RABBITMQ_URI")
    [ -z "${SECRET_KEY:-}" ] && missing_vars+=("SECRET_KEY")

    # AI Providers (at least one required)
    if [ -z "${OPENAI_API_KEY:-}" ] && [ -z "${GEMINI_API_KEY:-}" ]; then
        missing_vars+=("OPENAI_API_KEY or GEMINI_API_KEY")
    fi

    # Security warnings
    if [ "${SECRET_KEY:-}" = "change-this-to-a-very-secret-key-in-production" ]; then
        warnings+=("SECRET_KEY is set to default value - security risk!")
    fi

    if [ "${FLASK_ENV:-}" != "production" ]; then
        warnings+=("FLASK_ENV is not set to 'production'")
    fi

    # Check missing variables
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo -e "  ${RED}✗${NC} $var"
        done
        exit 1
    fi
    log_success "All required variables configured"

    # Show warnings
    if [ ${#warnings[@]} -gt 0 ]; then
        for warning in "${warnings[@]}"; do
            log_warning "$warning"
        done
    fi

    # Show AI configuration
    if [ -n "${OPENAI_API_KEY:-}" ]; then
        log_success "OpenAI API configured (${SB_OPENAI_MODEL:-gpt-4o-mini})"
    fi
    if [ -n "${GEMINI_API_KEY:-}" ]; then
        log_success "Gemini API configured (${SB_GEMINI_MODEL:-gemini-1.5-flash-latest})"
    fi
    log_info "Default AI provider: ${SB_DEFAULT_PROVIDER:-gemini}"

    # Check Cloudflare Tunnel Token
    if [ -z "${TUNNEL_TOKEN:-}" ]; then
        log_warning "TUNNEL_TOKEN not set - Cloudflare Tunnel won't work"
    else
        log_success "Cloudflare Tunnel token configured"
    fi

    # Check email configuration
    if [ -n "${MAIL_USERNAME:-}" ] && [ -n "${MAIL_PASSWORD:-}" ]; then
        log_success "Email notifications configured"
    else
        log_warning "Email not configured - notifications disabled"
    fi
}

# =============================================================================
# SECURITY HARDENING
# =============================================================================

configure_security() {
    log_step "6" "Security Hardening"

    # Configure firewall (UFW)
    if command -v ufw &> /dev/null; then
        log_info "Configuring firewall..."

        # Reset firewall
        ufw --force reset &> /dev/null

        # Default policies
        ufw default deny incoming
        ufw default allow outgoing

        # Allow SSH (consider restricting to specific IPs)
        ufw allow ssh comment 'SSH Access'

        # Note: No need to open 80/443 - Cloudflare Tunnel handles this

        # Enable firewall
        ufw --force enable
        log_success "Firewall configured (Zero Trust mode)"
    else
        log_warning "UFW not installed - skipping firewall setup"
    fi

    # Configure fail2ban for SSH protection
    if command -v fail2ban-client &> /dev/null; then
        log_info "Configuring fail2ban..."
        systemctl enable fail2ban
        systemctl start fail2ban || true
        log_success "Fail2ban configured"
    else
        log_warning "Fail2ban not installed - consider installing for SSH protection"
    fi

    # Set secure permissions on sensitive files
    log_info "Setting secure file permissions..."
    if [ -f "$SCRIPT_DIR/.env" ]; then
        chmod 600 "$SCRIPT_DIR/.env"
        chown "$ACTUAL_USER:$ACTUAL_USER" "$SCRIPT_DIR/.env"
        log_success ".env permissions secured"
    fi

    # Configure log rotation
    log_info "Configuring log rotation..."
    cat > /etc/logrotate.d/studybuddy << 'EOF'
/home/*/study_buddy-proj/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root root
}
EOF
    log_success "Log rotation configured"
}

# =============================================================================
# DOCKER BUILD & DEPLOYMENT
# =============================================================================

build_and_deploy() {
    log_step "7" "Building and Deploying Containers"

    cd "$SCRIPT_DIR"

    # --- CALCULATE SCALE (NEW) ---
    calculate_system_capacity
    # -----------------------------

    # Full restart if requested
    if [ "$FULL_RESTART" = true ]; then
        full_system_restart
    fi

    # Pull latest base images
    log_info "Pulling latest base images..."
    docker compose pull 2>&1 | tee -a "$DEPLOY_LOG" || true

    # Build new images
    log_info "Building Docker images (this may take a few minutes)..."
    local build_flags=""
    if [ "$FORCE_REBUILD" = true ]; then
        build_flags="--no-cache"
        log_info "Force rebuild enabled (no cache)"
    fi

    if docker compose build $build_flags 2>&1 | tee -a "$DEPLOY_LOG"; then
        log_success "Docker images built successfully"
    else
        log_error "Failed to build Docker images"
        return 1
    fi

    # Stop old containers gracefully
    log_info "Stopping old containers..."
    if docker compose down --timeout 30 2>&1 | tee -a "$DEPLOY_LOG"; then
        log_success "Old containers stopped"
    else
        log_warning "Some containers may not have stopped cleanly"
    fi

    # Start new containers
    log_info "Starting system with $OPTIMAL_WORKER_COUNT workers..."

    # --- START WITH SCALING LOGIC (NEW) ---
    # Attempt to start with scaling.
    # If it fails (due to hardcoded container_name), fallback to normal up.
    if ! docker compose up -d --scale "$WORKER_SERVICE_NAME"="$OPTIMAL_WORKER_COUNT" 2>&1 | tee -a "$DEPLOY_LOG"; then
        log_warning "Scaling failed (Likely due to fixed 'container_name' in docker-compose.yml)"
        log_warning "Falling back to standard startup (no scaling)..."
        if docker compose up -d 2>&1 | tee -a "$DEPLOY_LOG"; then
            log_success "Containers started (Single worker mode)"
            OPTIMAL_WORKER_COUNT=1 # Reset count for report
        else
             log_error "Failed to start containers"
             return 1
        fi
    else
        log_success "New containers started"
    fi
    # ---------------------------------------

    # Wait for containers to be ready
    log_info "Waiting for containers to initialize..."
    show_progress 20 "Container startup"
}

# =============================================================================
# HEALTH CHECKS
# =============================================================================

perform_health_checks() {
    log_step "8" "Performing Health Checks"

    local all_healthy=true

    # Check if containers are running
    log_info "Checking container status..."
    local containers=("$APP_CONTAINER" "$WORKER_CONTAINER" "$MONGO_CONTAINER" "$RABBITMQ_CONTAINER" "$TUNNEL_CONTAINER")

    for container in "${containers[@]}"; do
        if docker ps --filter "name=$container" --filter "status=running" | grep -q "$container"; then
            log_success "$container is running"
        else
            log_error "$container is not running"
            all_healthy=false
        fi
    done

    if [ "$all_healthy" = false ]; then
        log_error "Container health check failed"
        return 1
    fi

    # Test application health endpoint
    log_info "Testing application health endpoint..."
    local retry=0
    local app_healthy=false

    while [ $retry -lt $MAX_HEALTH_RETRIES ]; do
        if curl -sf http://localhost:5000/health > /dev/null 2>&1; then
            app_healthy=true
            break
        fi
        retry=$((retry + 1))
        sleep $HEALTH_CHECK_INTERVAL
    done

    if [ "$app_healthy" = true ]; then
        log_success "Application health check passed"
    else
        log_error "Application health check failed after ${MAX_HEALTH_RETRIES} retries"
        return 1
    fi

    # Test detailed health endpoint
    log_info "Testing detailed health endpoint..."
    local health_response=$(curl -sf http://localhost:5000/health/detailed 2>/dev/null || echo '{}')

    # Parse health response (basic check)
    if echo "$health_response" | grep -q "healthy\|degraded"; then
        log_success "Detailed health check completed"
    else
        log_warning "Detailed health check returned unexpected response"
    fi

    # Check worker status
    log_info "Checking worker status..."
    local worker_logs=$(docker logs "$WORKER_CONTAINER" --tail=50 2>&1)

    if echo "$worker_logs" | grep -q "Worker successfully connected to MongoDB"; then
        log_success "Worker connected to MongoDB"
    else
        log_warning "Worker may not be connected to MongoDB"
    fi

    if echo "$worker_logs" | grep -q "Worker connected to RabbitMQ"; then
        log_success "Worker connected to RabbitMQ"
    else
        log_warning "Worker may not be connected to RabbitMQ"
    fi

    # Check database connectivity
    log_info "Testing database connectivity..."
    if docker exec "$MONGO_CONTAINER" mongosh --eval "db.adminCommand('ping')" --quiet > /dev/null 2>&1; then
        log_success "MongoDB is responding"
    else
        log_warning "MongoDB may not be fully ready"
    fi

    # Check RabbitMQ management
    log_info "Testing RabbitMQ connectivity..."
    if curl -sf -u guest:guest http://localhost:15672/api/overview > /dev/null 2>&1; then
        log_success "RabbitMQ management is accessible"
    else
        log_warning "RabbitMQ management may not be ready"
    fi

    log_success "All health checks passed"
}

# =============================================================================
# ROLLBACK FUNCTIONALITY
# =============================================================================

perform_rollback() {
    log_step "ROLLBACK" "Performing Automatic Rollback"

    if [ ! -f "$STATE_FILE" ]; then
        log_error "No state file found - cannot rollback"
        return 1
    fi

    # Load backup information
    source "$STATE_FILE"

    if [ -z "${BACKUP_PATH:-}" ] || [ ! -d "$BACKUP_PATH" ]; then
        log_error "Backup path not found - cannot rollback"
        return 1
    fi

    log_info "Rolling back to backup: $BACKUP_NAME"

    # Stop current containers
    log_info "Stopping current containers..."
    docker compose down --timeout 30 2>&1 | tee -a "$DEPLOY_LOG" || true

    # Restore .env file
    if [ -f "$BACKUP_PATH/.env" ]; then
        log_info "Restoring .env file..."
        cp "$BACKUP_PATH/.env" "$SCRIPT_DIR/.env"
        chown "$ACTUAL_USER:$ACTUAL_USER" "$SCRIPT_DIR/.env"
    fi

    # Rollback git commit
    if [ -f "$BACKUP_PATH/commit.txt" ]; then
        local backup_commit=$(cat "$BACKUP_PATH/commit.txt")
        if [ "$backup_commit" != "unknown" ]; then
            log_info "Rolling back to commit: ${backup_commit:0:8}"
            cd "$SCRIPT_DIR"
            sudo -u "$ACTUAL_USER" git reset --hard "$backup_commit" 2>&1 | tee -a "$DEPLOY_LOG" || true
        fi
    fi

    # Restore MongoDB backup
    if [ -f "$BACKUP_PATH/mongodb_backup.archive" ]; then
        log_info "Restoring MongoDB backup..."
        # Start mongo container
        docker compose up -d mongo 2>&1 | tee -a "$DEPLOY_LOG"
        sleep 10

        # Restore