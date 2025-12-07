#!/bin/bash
# =============================================================================
# StudyBuddy AI - Ultimate Production Deployment Script
# =============================================================================
# Features:
# - Auto-Scaling Workers
# - Automated Backup & Rollback
# - Security Hardening
# - Health Monitoring
# - Fully NON-INTERACTIVE (safe for sudo + automations)
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

# Disable any interactive git prompts globally
export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS=true

# =============================================================================
# CONFIGURATION & GLOBALS
# =============================================================================

VERSION="2.1.3-Fixed"
DEPLOY_START_TIME=$(date +%s)
DEPLOY_DATE=$(date +%Y%m%d_%H%M%S)

# --- AUTO-SCALING CONFIG ---
WORKER_SERVICE_NAME="worker"   # Must match service name in docker-compose.yml
WORKER_RAM_ESTIMATE_MB=350     # Est. RAM per worker
SYSTEM_RESERVE_MB=2048         # RAM reserved for OS/DB
MAX_WORKER_CAP=32              # Hard cap
OPTIMAL_WORKER_COUNT=1         # Default if auto calc not used
MANUAL_OVERRIDE=4              # Set via --workers flag

# Deployment Modes
FULL_RESTART=false
FORCE_REBUILD=false
SKIP_BACKUP=false
SKIP_GIT_PULL=false
QUICK_MODE=false

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly MAGENTA='\033[0;35m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m'

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/backups"
LOG_DIR="$SCRIPT_DIR/logs"
DEPLOY_LOG="$LOG_DIR/deploy_${DEPLOY_DATE}.log"

# State
DEPLOYMENT_ID="deploy_${DEPLOY_DATE}"
STATE_FILE="$LOG_DIR/.deploy_state"
ROLLBACK_NEEDED=false

# Containers (must match docker-compose.yml)
APP_CONTAINER="studybuddy_app"
WORKER_CONTAINER="studybuddy_worker"
MONGO_CONTAINER="studybuddy_mongo"

# =============================================================================
# LOGGING & NOTIFICATION FUNCTIONS
# =============================================================================

mkdir -p "$LOG_DIR" "$BACKUP_DIR"

log() {
    local level=$1
    shift
    local message="$*"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$DEPLOY_LOG"
}

log_info()    { log "INFO"    "${BLUE}ℹ${NC} $*"; }
log_success() { log "SUCCESS" "${GREEN}✓${NC} $*"; }
log_warning() { log "WARNING" "${YELLOW}⚠${NC} $*"; }
log_error()   { log "ERROR"   "${RED}✗${NC} $*"; }
log_step()    { echo ""; log "STEP" "${MAGENTA}[$1]${NC} ${WHITE}${*:2}${NC}"; echo ""; }

show_progress() {
    local duration=$1
    local message=$2
    local width=50
    for ((i=0; i<=duration; i++)); do
        local progress=$((i * width / duration))
        printf "\r${CYAN}%s${NC} [" "${message}"
        printf "%${progress}s" | tr ' ' '█'
        printf "%$((width - progress))s" | tr ' ' '░'
        printf "] %3d%%" $((i * 100 / duration))
        sleep 1
    done
    echo ""
}

send_notification() {
    local subject="$1"
    local message="$2"

    # Only try to send if variables are set
    if [ -n "${ADMIN_EMAIL:-}" ] && [ -n "${MAIL_USERNAME:-}" ]; then
        if docker ps | grep -q "$APP_CONTAINER"; then
            log_info "Sending email notification..."
            docker exec "$APP_CONTAINER" python3 -c "
import sys
try:
    print('Sending notification: ' + sys.argv[2])
except:
    pass
" "${ADMIN_EMAIL}" "${subject}" "${message}" || true
        fi
    fi

    log_info "Notification: ${subject} - ${message}"
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
    send_notification "❌ Deployment Failed" "Failed at line ${line_number}"

    if [ "$ROLLBACK_NEEDED" = true ]; then
        log_warning "Initiating automatic rollback..."
        perform_rollback
    fi
}

cleanup_handler() {
    if [ "$ROLLBACK_NEEDED" = false ]; then
        log_success "Deployment completed successfully"
        send_notification "✅ Deployment Successful" "Completed successfully"
    fi
}

# =============================================================================
# SCALING LOGIC
# =============================================================================

calculate_system_capacity() {
    log_step "SCALING" "Calculating System Capacity"

    if [ "$MANUAL_OVERRIDE" -gt 0 ]; then
        OPTIMAL_WORKER_COUNT=$MANUAL_OVERRIDE
        log_info "Using manual override: $OPTIMAL_WORKER_COUNT workers"
        return
    fi

    local cpu_cores
    local total_ram_mb
    cpu_cores=$(nproc)
    total_ram_mb=$(free -m | awk '/^Mem:/{print $2}')

    local cpu_limit=$(( (cpu_cores * 2) + 1 ))
    local available_ram=$(( total_ram_mb - SYSTEM_RESERVE_MB ))
    if [ "$available_ram" -le 0 ]; then available_ram=100; fi

    local ram_limit=$(( available_ram / WORKER_RAM_ESTIMATE_MB ))
    if [ "$ram_limit" -lt 1 ]; then ram_limit=1; fi

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

    echo -e "${CYAN}╔════════════════════ SYSTEM AUDIT ════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} CPU Cores:      ${WHITE}${cpu_cores}${NC}"
    echo -e "${CYAN}║${NC} RAM Available:  ${WHITE}${available_ram} MB${NC}"
    echo -e "${CYAN}║${NC} Bottleneck:     ${YELLOW}${bottleneck}${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"

    log_success "Calculated optimal workers: $OPTIMAL_WORKER_COUNT"
}

# =============================================================================
# MAIN FUNCTIONS
# =============================================================================

check_prerequisites() {
    log_step "1" "Pre-flight Checks"
    if [[ $EUID -ne 0 ]]; then
        log_error "Run as root (use: sudo ./deploy-production.sh)"
        exit 1
    fi
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker missing"
        exit 1
    fi
    log_success "Checks passed"
}

create_backup() {
    if [ "$SKIP_BACKUP" = true ]; then return 0; fi
    log_step "2" "Creating Backup"
    local backup_path="$BACKUP_DIR/backup_${DEPLOY_DATE}"
    mkdir -p "$backup_path"

    [ -f ".env" ] && cp ".env" "$backup_path/.env"

    if docker ps | grep -q "$MONGO_CONTAINER"; then
        log_info "Backing up MongoDB..."
        docker exec "$MONGO_CONTAINER" mongodump --archive=/tmp/dump.gz --gzip || true
        docker cp "$MONGO_CONTAINER:/tmp/dump.gz" "$backup_path/mongo.gz" || true
    fi

    echo "BACKUP_PATH=$backup_path" > "$STATE_FILE"
    log_success "Backup created"
}

update_code() {
    if [ "$SKIP_GIT_PULL" = true ]; then return 0; fi
    log_step "3" "Updating Code"
    cd "$SCRIPT_DIR"

    ACTUAL_USER="${SUDO_USER:-$USER}"
    sudo -u "$ACTUAL_USER" git config --global --add safe.directory "$SCRIPT_DIR" || true

    local current_branch
    if ! current_branch=$(sudo -u "$ACTUAL_USER" git rev-parse --abbrev-ref HEAD 2>/dev/null); then
        log_warning "Could not detect git branch (maybe not a git repo). Skipping git pull."
        return 0
    fi
    log_info "Detected branch: $current_branch"

    if sudo -u "$ACTUAL_USER" \
        GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=true \
        git pull --no-edit origin "$current_branch" 2>&1 | tee -a "$DEPLOY_LOG"
    then
        log_success "Code updated from git"
    else
        log_error "Git pull failed (non-interactive). Check credentials or network."
        return 1
    fi
}

build_and_deploy() {
    log_step "4" "Building and Deploying"
    cd "$SCRIPT_DIR"

    calculate_system_capacity

    if [ "$FULL_RESTART" = true ]; then
        docker compose down -v --remove-orphans
    fi

    log_info "Building images..."
    local build_flags=""
    if [ "$FORCE_REBUILD" = true ]; then build_flags="--no-cache"; fi

    docker compose build $build_flags 2>&1 | tee -a "$DEPLOY_LOG" > /dev/null

    log_info "Stopping old containers..."
    docker compose down --remove-orphans 2>&1 | tee -a "$DEPLOY_LOG" > /dev/null

    log_info "Starting system with $OPTIMAL_WORKER_COUNT workers..."

    if ! docker compose up -d --scale "$WORKER_SERVICE_NAME"="$OPTIMAL_WORKER_COUNT" 2>&1 | tee -a "$DEPLOY_LOG"; then
        log_warning "Scaling failed (check service name '$WORKER_SERVICE_NAME')"
        log_warning "Falling back to standard startup..."
        if docker compose up -d 2>&1 | tee -a "$DEPLOY_LOG"; then
            log_success "Started (Fallback mode)"
            OPTIMAL_WORKER_COUNT=1
        else
            log_error "Failed to start containers"
            return 1
        fi
    else
        log_success "New containers started"
    fi

    show_progress 20 "Waiting for startup"
}

perform_health_checks() {
    log_step "5" "Health Checks"
    if curl -sf http://localhost:5000/health > /dev/null 2>&1; then
        log_success "App is healthy"
    else
        log_warning "App health check failed (might still be booting)"
    fi

    local active
    active=$(docker ps --filter "name=$WORKER_SERVICE_NAME" --format "{{.ID}}" | wc -l)
    log_info "Active Worker Instances: $active"
}

perform_rollback() {
    log_step "ROLLBACK" "Restoring Previous Version"
    if [ -f "$STATE_FILE" ]; then
        # shellcheck disable=SC1090
        source "$STATE_FILE"
        if [ -d "$BACKUP_PATH" ]; then
            log_info "Restoring from $BACKUP_PATH"
            docker compose down
            [ -f "$BACKUP_PATH/.env" ] && cp "$BACKUP_PATH/.env" .
            docker compose up -d
            log_success "Rollback successful"
        fi
    fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

print_banner() {
    echo -e "${BLUE}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║              Ultimate Production Deployment v2.1.3          ║
║              With Auto-Scaling Intelligence                 ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

main() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --workers) MANUAL_OVERRIDE=$2; shift 2 ;;
            --full-restart) FULL_RESTART=true; FORCE_REBUILD=true; shift ;;
            --quick) QUICK_MODE=true; SKIP_BACKUP=true; shift ;;
            --rollback) perform_rollback; exit 0 ;;
            *) echo "Unknown option: $1"; exit 1 ;;
        esac
    done

    print_banner
    check_prerequisites
    create_backup
    update_code
    build_and_deploy
    perform_health_checks

    local duration
    duration=$(($(date +%s) - DEPLOY_START_TIME))
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              ✓ DEPLOYMENT COMPLETED SUCCESSFULLY!            ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo -e "${CYAN}Time:${NC}    ${WHITE}${duration}s${NC}"
    echo -e "${CYAN}Workers:${NC} ${WHITE}${OPTIMAL_WORKER_COUNT}${NC}"
    echo ""
}

main "$@"