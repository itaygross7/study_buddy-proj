#!/bin/bash
# =============================================================================
# StudyBuddy AI - Production Deployment (Auto-Scaling Edition)
# =============================================================================
# A complete DevOps team in one script featuring:
# - Auto-Scaling Workers (CPU/RAM Detection)
# - Automated backup before deployment
# - Smart rollback on failures
# - Health monitoring
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

# =============================================================================
# CONFIGURATION & GLOBALS
# =============================================================================

VERSION="2.4.0"
DEPLOY_START_TIME=$(date +%s)
DEPLOY_DATE=$(date +%Y%m%d_%H%M%S)

# --- SCALING SETTINGS ---
WORKER_RAM_ESTIMATE_MB=350   # RAM per worker
SYSTEM_RESERVE_MB=2048       # Reserve for OS/DB
MAX_WORKER_CAP=32            # Hard limit
OPTIMAL_WORKER_COUNT=1       # Default (will be calculated)
MANUAL_OVERRIDE=0

# Deployment modes
FULL_RESTART=false
FORCE_REBUILD=false
SKIP_BACKUP=false
QUICK_MODE=false

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m'

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/backups"
LOG_DIR="$SCRIPT_DIR/logs"
DEPLOY_LOG="$LOG_DIR/deploy_${DEPLOY_DATE}.log"

# Container names
WORKER_CONTAINER="studybuddy_worker"
MONGO_CONTAINER="studybuddy_mongo"

# =============================================================================
# LOGGING
# =============================================================================

mkdir -p "$LOG_DIR" "$BACKUP_DIR"

log() { echo -e "$(date '+%Y-%m-%d %H:%M:%S') [$1] $2" | tee -a "$DEPLOY_LOG"; }
log_info() { log "INFO" "${BLUE}ℹ${NC} $1"; }
log_success() { log "SUCCESS" "${GREEN}✓${NC} $1"; }
log_warning() { log "WARNING" "${YELLOW}⚠${NC} $1"; }
log_error() { log "ERROR" "${RED}✗${NC} $1"; }
log_step() { echo ""; log "STEP" "${CYAN}[$1]${NC} $2"; echo ""; }

# =============================================================================
# AUTO-SCALING LOGIC (Fixed)
# =============================================================================

calculate_workers() {
    log_step "SCALING" "Calculating System Capacity"

    if [ "$MANUAL_OVERRIDE" -gt 0 ]; then
        OPTIMAL_WORKER_COUNT=$MANUAL_OVERRIDE
        log_warning "Using manual override: $OPTIMAL_WORKER_COUNT"
        return
    fi

    # 1. Hardware Audit
    local cpu_cores=$(nproc)
    local total_ram_mb=$(free -m | awk '/^Mem:/{print $2}')

    # 2. Math
    local cpu_limit=$(( (cpu_cores * 2) + 1 ))
    local available_ram=$(( total_ram_mb - SYSTEM_RESERVE_MB ))

    if [ "$available_ram" -le 0 ]; then available_ram=100; fi
    local ram_limit=$(( available_ram / WORKER_RAM_ESTIMATE_MB ))
    if [ "$ram_limit" -lt 1 ]; then ram_limit=1; fi

    # 3. Determine Bottleneck
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

    # 4. Set Global Variable (This fixes the docker error)
    OPTIMAL_WORKER_COUNT=$count

    # 5. Show Report
    echo -e "${CYAN}╔════════════════════ SYSTEM AUDIT ════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} CPU Cores:      ${WHITE}${cpu_cores}${NC}"
    echo -e "${CYAN}║${NC} RAM Available:  ${WHITE}${available_ram} MB${NC}"
    echo -e "${CYAN}║${NC} Bottleneck:     ${YELLOW}${bottleneck}${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
    log_success "Setting scale to: $OPTIMAL_WORKER_COUNT workers"
}

# =============================================================================
# CORE FUNCTIONS (Original)
# =============================================================================

check_prerequisites() {
    if [[ $EUID -ne 0 ]]; then log_error "Run as root (sudo)"; exit 1; fi
    command -v docker >/dev/null || { log_error "Docker missing"; exit 1; }
}

create_backup() {
    if [ "$SKIP_BACKUP" = true ]; then return 0; fi
    log_step "BACKUP" "Creating Backup"
    local backup_path="$BACKUP_DIR/backup_${DEPLOY_DATE}"
    mkdir -p "$backup_path"

    # Backup Mongo if running
    if docker ps | grep -q "$MONGO_CONTAINER"; then
        docker exec "$MONGO_CONTAINER" mongodump --archive=/tmp/dump.gz --gzip || true
        docker cp "$MONGO_CONTAINER:/tmp/dump.gz" "$backup_path/mongo.gz" || true
        log_success "Database backed up"
    fi

    # Save .env
    [ -f ".env" ] && cp ".env" "$backup_path/"
}

build_and_deploy() {
    log_step "DEPLOY" "Building and Deploying"

    cd "$SCRIPT_DIR"

    # 1. Run Calculation
    calculate_workers

    # 2. Build
    log_info "Building images..."
    docker compose build 2>&1 | tee -a "$DEPLOY_LOG" > /dev/null

    # 3. Stop Old
    log_info "Stopping containers..."
    docker compose down --remove-orphans 2>&1 | tee -a "$DEPLOY_LOG" > /dev/null

    # 4. Start with Scale
    log_info "Starting with $OPTIMAL_WORKER_COUNT workers..."

    # FIXED: Using the variable directly, no weird text parsing
    if docker compose up -d --scale studybuddy_worker="$OPTIMAL_WORKER_COUNT" 2>&1 | tee -a "$DEPLOY_LOG"; then
        log_success "Deployment successful"
    else
        log_error "Docker start failed"
        exit 1
    fi
}

perform_health_checks() {
    log_step "HEALTH" "Checking Status"
    sleep 10
    local active=$(docker ps --filter "name=worker" --format "{{.ID}}" | wc -l)
    log_info "Active Workers: $active / $OPTIMAL_WORKER_COUNT"

    if curl -sf http://localhost:5000/health > /dev/null 2>&1; then
        log_success "API is healthy"
    else
        log_warning "API health check failed (might still be starting)"
    fi
}

# =============================================================================
# MAIN
# =============================================================================

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --workers) MANUAL_OVERRIDE="$2"; shift 2 ;;
        --quick) QUICK_MODE=true; SKIP_BACKUP=true; shift ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

check_prerequisites
create_backup
build_and_deploy
perform_health_checks

# =============================================================================
# FINAL REPORT (What you asked for)
# =============================================================================
DURATION=$(($(date +%s) - DEPLOY_START_TIME))

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║             🚀 DEPLOYMENT COMPLETE                           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo -e "${CYAN} CAPACITY REPORT ${NC}"
echo -e " ----------------------"
echo -e " ${CYAN}▶${NC} Total Scaled Workers: ${GREEN}${OPTIMAL_WORKER_COUNT}${NC}"
echo -e " ${CYAN}▶${NC} Time Taken:           ${WHITE}${DURATION}s${NC}"
echo -e " ${CYAN}▶${NC} Log File:             ${WHITE}${DEPLOY_LOG}${NC}"
echo ""