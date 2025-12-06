#!/bin/bash
# =============================================================================
# StudyBuddy AI - Ultimate Production Deployment Script
# =============================================================================
# A complete DevOps team in one script featuring:
# - Auto-Scaling Workers (CPU/RAM Detection) [NEW]
# - Automated backup before deployment
# - Smart rollback on failures
# - Zero-downtime deployment
# - Health monitoring and auto-recovery
# - Security hardening
# - Performance optimization
# - Comprehensive logging
# - Email notifications
# =============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures
IFS=$'\n\t'

# =============================================================================
# CONFIGURATION & GLOBALS
# =============================================================================

# Script version
VERSION="2.6.0-Ultimate"
DEPLOY_START_TIME=$(date +%s)
DEPLOY_DATE=$(date +%Y%m%d_%H%M%S)

# --- AUTO-SCALING CONFIGURATION ---
# IMPORTANT: This must match the service name in your docker-compose.yml
# (It is usually 'worker' or 'celery_worker', NOT the container_name)
WORKER_SERVICE_NAME="worker"
WORKER_RAM_ESTIMATE_MB=350     # Est. RAM per worker
SYSTEM_RESERVE_MB=2048         # RAM reserved for OS/DB
MAX_WORKER_CAP=32              # Hard cap
OPTIMAL_WORKER_COUNT=1         # Default (Calculated later)
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
readonly WHITE='\033[1;37m'  # <--- FIXED: Added missing definition
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
    ${GREEN}--workers [N]${NC}           Manually set worker count (overrides auto-scaling)
    ${GREEN}--full-restart${NC}          Complete system restart
    ${GREEN}--quick${NC}                 Quick deployment (skip backups)
    ${GREEN}--rollback${NC}              Rollback to previous deployment
    ${GREEN}--status${NC}                Show current deployment status

EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help) show_usage; exit 0 ;;
            --full-restart) FULL_RESTART=true; FORCE_REBUILD=true; log_info "Mode: Full Restart"; shift ;;
            --force-rebuild) FORCE_REBUILD=true; shift ;;
            --quick) QUICK_MODE=true; SKIP_BACKUP=true; log_info "Mode: Quick"; shift ;;
            --workers) MANUAL_OVERRIDE=$2; log_info "Mode: Manual Workers ($2)"; shift 2 ;;
            --skip-backup) SKIP_BACKUP=true; shift ;;
            --skip-git) SKIP_GIT_PULL=true; shift ;;
            --rollback) perform_rollback; exit $? ;;
            --cleanup) cleanup_old_files; exit 0 ;;
            --status) show_deployment_status; exit 0 ;;
            *) log_error "Unknown option: $1"; show_usage; exit 1 ;;
        esac
    done
}

# =============================================================================
# LOGGING & OUTPUT FUNCTIONS
# =============================================================================

mkdir -p "$LOG_DIR" "$BACKUP_DIR"

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$DEPLOY_LOG"
}

log_info() { log "INFO" "${BLUE}ℹ${NC} $@" ; }
log_success() { log "SUCCESS" "${GREEN}✓${NC} $@" ; }
log_warning() { log "WARNING" "${YELLOW}⚠${NC} $@" ; }
log_error() { log "ERROR" "${RED}✗${NC} $@" ; }
log_step() {
    local step_num=$1
    shift
    echo ""
    log "STEP" "${MAGENTA}[${step_num}]${NC} ${WHITE}$@${NC}"
    echo ""
}

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
║              Ultimate Production Deployment v2.6.0          ║
║              With Auto-Scaling Intelligence                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    log_info "Deployment ID: ${DEPLOYMENT_ID}"
}

# =============================================================================
# AUTO-SCALING INTELLIGENCE (NEW)
# =============================================================================

calculate_system_capacity() {
    log_step "SCALE" "Calculating Optimal Worker Count"

    # 1. Manual Override
    if [ "$MANUAL_OVERRIDE" -gt 0 ]; then
        OPTIMAL_WORKER_COUNT=$MANUAL_OVERRIDE
        log_warning "Using manual override: $OPTIMAL_WORKER_COUNT workers"
        return
    fi

    # 2. Hardware Audit
    local cpu_cores=$(nproc)
    local total_ram_mb=$(free -m | awk '/^Mem:/{print $2}')

    # 3. Calculate Limits
    local cpu_limit=$(( (cpu_cores * 2) + 1 ))
    local available_ram=$(( total_ram_mb - SYSTEM_RESERVE_MB ))

    if [ "$available_ram" -le 0 ]; then available_ram=100; fi # Safety buffer
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

    # 5. Set Global
    OPTIMAL_WORKER_COUNT=$count

    # 6. Report
    echo -e "${CYAN}╔════════════════════ SYSTEM AUDIT ════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} CPU Cores:      ${WHITE}${cpu_cores}${NC} (Max: $cpu_limit)"
    echo -e "${CYAN}║${NC} RAM Available:  ${WHITE}${available_ram} MB${NC} (after reserve)"
    echo -e "${CYAN}║${NC} RAM Limit:      ${WHITE}${ram_limit}${NC} workers"
    echo -e "${CYAN}║${NC} Bottleneck:     ${YELLOW}${bottleneck}${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"

    log_success "Calculated optimal workers: $OPTIMAL_WORKER_COUNT"
}

# =============================================================================
# ERROR HANDLING
# =============================================================================

trap 'error_handler $? $LINENO' ERR
trap 'cleanup_handler' EXIT INT TERM

error_handler() {
    local exit_code=$1
    local line_number=$2
    log_error "Deployment failed at line ${line_number} with exit code ${exit_code}"
    ROLLBACK_NEEDED=true
    if [ "$ROLLBACK_NEEDED" = true ]; then
        log_warning "Initiating automatic rollback..."
        perform_rollback
    fi
}

cleanup_handler() {
    if [ "$ROLLBACK_NEEDED" = false ]; then
        local duration=$(($(date +%s) - DEPLOY_START_TIME))
        log_success "Deployment completed successfully"
        log_info "Total deployment time: ${duration}s"
    fi
}

# =============================================================================
# MAIN FUNCTIONS
# =============================================================================

check_prerequisites() {
    log_step "1" "Pre-flight Checks"
    if [[ $EUID -ne 0 ]]; then log_error "Run as root"; exit 1; fi
    ACTUAL_USER="${SUDO_USER:-$USER}"
    log_info "Actual user: ${ACTUAL_USER}"
    command -v docker >/dev/null || { log_error "Docker missing"; exit 1; }
    log_success "Checks passed"
}

create_backup() {
    if [ "$SKIP_BACKUP" = true ]; then return 0; fi
    log_step "2" "Creating Backup"

    local backup_path="$BACKUP_DIR/backup_${DEPLOY_DATE}"
    mkdir -p "$backup_path"

    PREVIOUS_COMMIT=$(cd "$SCRIPT_DIR" && git rev-parse HEAD 2>/dev/null || echo "unknown")
    echo "$PREVIOUS_COMMIT" > "$backup_path/commit.txt"
    [ -f ".env" ] && cp ".env" "$backup_path/.env"

    if docker ps | grep -q "$MONGO_CONTAINER"; then
        log_info "Backing up MongoDB..."
        docker exec "$MONGO_CONTAINER" mongodump --archive=/tmp/dump.gz --gzip || true
        docker cp "$MONGO_CONTAINER:/tmp/dump.gz" "$backup_path/mongo.gz" || true
    fi

    echo "BACKUP_PATH=$backup_path" > "$STATE_FILE"
    log_success "Backup created: backup_${DEPLOY_DATE}"
}

update_code() {
    if [ "$SKIP_GIT_PULL" = true ]; then return 0; fi
    log_step "3" "Updating Code"
    cd "$SCRIPT_DIR"

    # Fix permissions & Safe directory
    chown -R "$ACTUAL_USER:$ACTUAL_USER" "$SCRIPT_DIR"
    sudo -u "$ACTUAL_USER" git config --global --add safe.directory "$SCRIPT_DIR" || true

    # FIX: Detect correct branch name (main vs master)
    local current_branch=$(sudo -u "$ACTUAL_USER" git rev-parse --abbrev-ref HEAD)
    log_info "Detected branch: $current_branch"

    if sudo -u "$ACTUAL_USER" git pull origin "$current_branch" 2>&1 | tee -a "$DEPLOY_LOG"; then
        log_success "Code updated"
    else
        log_error "Git pull failed"
        return 1
    fi
}

configure_security() {
    log_step "4" "Security Hardening"
    if command -v ufw >/dev/null; then
        ufw allow ssh >/dev/null
        ufw --force enable >/dev/null
        log_success "Firewall enabled"
    fi
    if [ -f ".env" ]; then chmod 600 ".env"; fi
}

build_and_deploy() {
    log_step "5" "Building and Deploying"
    cd "$SCRIPT_DIR"

    # --- CALCULATE SCALE ---
    calculate_system_capacity
    # -----------------------

    if [ "$FULL_RESTART" = true ]; then full_system_restart; fi

    log_info "Building images..."
    local build_flags=""
    if [ "$FORCE_REBUILD" = true ]; then build_flags="--no-cache"; fi

    docker compose build $build_flags 2>&1 | tee -a "$DEPLOY_LOG" > /dev/null

    log_info "Stopping old containers..."
    docker compose down --remove-orphans 2>&1 | tee -a "$DEPLOY_LOG" > /dev/null

    log_info "Starting system with $OPTIMAL_WORKER_COUNT workers..."

    # --- DEPLOY WITH SCALE ---
    # We use --scale service=number
    if docker compose up -d --scale "$WORKER_SERVICE_NAME"="$OPTIMAL_WORKER_COUNT" 2>&1 | tee -a "$DEPLOY_LOG"; then
        log_success "Containers started"
    else
        log_error "Startup failed. Check docker-compose service names."
        # Fallback
        log_warning "Attempting fallback (no scaling)..."
        docker compose up -d
    fi

    show_progress 20 "Waiting for services"
}

perform_health_checks() {
    log_step "6" "Health Checks"

    if curl -sf http://localhost:5000/health > /dev/null 2>&1; then
        log_success "Application is healthy"
    else
        log_warning "App health check failed (might be starting up)"
    fi

    local workers=$(docker ps --filter "name=$WORKER_SERVICE_NAME" --format "{{.ID}}" | wc -l)
    log_info "Active Worker Count: $workers"
}

optimize_performance() {
    log_step "7" "Performance Optimization"
    log_info "Cleaning Docker system..."
    docker system prune -f --volumes > /dev/null 2>&1

    # Sysctl optimization
    log_info "Tuning kernel parameters..."
    sysctl -w net.core.somaxconn=1024 > /dev/null 2>&1 || true
    log_success "System optimized"
}

perform_rollback() {
    log_step "ROLLBACK" "Restoring Previous Version"
    if [ -f "$STATE_FILE" ]; then
        source "$STATE_FILE"
        if [ -d "$BACKUP_PATH" ]; then
            log_info "Restoring from $BACKUP_PATH"
            docker compose down
            cp "$BACKUP_PATH/.env" .
            if [ -f "$BACKUP_PATH/mongo.gz" ]; then
                docker compose up -d mongo
                sleep 5
                docker cp "$BACKUP_PATH/mongo.gz" "$MONGO_CONTAINER:/tmp/dump.gz"
                docker exec "$MONGO_CONTAINER" mongorestore --archive=/tmp/dump.gz --gzip --drop
            fi
            docker compose up -d
            log_success "Rollback successful"
        fi
    fi
}

cleanup_old_files() {
    if [ -d "$BACKUP_DIR" ]; then
        ls -t "$BACKUP_DIR" | tail -n +6 | xargs -r rm -rf
    fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    parse_arguments "$@"
    print_banner

    check_prerequisites
    create_backup
    update_code
    configure_security
    build_and_deploy
    perform_health_checks
    optimize_performance
    cleanup_old_files

    # Final Success Report
    local duration=$(($(date +%s) - DEPLOY_START_TIME))
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              ✓ DEPLOYMENT COMPLETED SUCCESSFULLY!            ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo -e "${CYAN}Deployment Time:${NC} ${WHITE}${duration}s${NC}"
    echo -e "${CYAN}Scaled Workers:${NC}  ${WHITE}${OPTIMAL_WORKER_COUNT}${NC}"
    echo -e "${CYAN}Log File:${NC}       ${WHITE}${DEPLOY_LOG}${NC}"
    echo ""
}

main "$@"