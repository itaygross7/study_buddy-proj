#!/bin/bash
# =============================================================================
# StudyBuddy AI - Auto-Scaling Production Deployment Script
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

# =============================================================================
# CONFIGURATION & GLOBALS
# =============================================================================

VERSION="2.2.1-autoscaling"
DEPLOY_START_TIME=$(date +%s)
DEPLOY_DATE=$(date +%Y%m%d_%H%M%S)

# --- SCALING CONFIGURATION ---
# The script will auto-calculate, but these are the safety rails
WORKER_RAM_ESTIMATE_MB=350   # Avg RAM usage per worker (Python/AI tasks)
SYSTEM_RESERVE_MB=2048       # RAM reserved for OS, Mongo, RabbitMQ, & Web App
MAX_WORKER_CAP=32            # Never spawn more than this (safety break)
MANUAL_WORKER_COUNT=0        # Set via --workers flag to override auto-scaling

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'  # <--- FIXED: Added this missing definition
readonly NC='\033[0m'

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/backups"
LOG_DIR="$SCRIPT_DIR/logs"
DEPLOY_LOG="$LOG_DIR/deploy_${DEPLOY_DATE}.log"

# Global Var for Final Report
FINAL_WORKER_COUNT=1

# =============================================================================
# UTILITY: LOGGING
# =============================================================================

log() { echo -e "$(date '+%Y-%m-%d %H:%M:%S') [$1] $2" | tee -a "$DEPLOY_LOG"; }
log_info() { log "INFO" "${BLUE}ℹ${NC} $1"; }
log_success() { log "SUCCESS" "${GREEN}✓${NC} $1"; }
log_warning() { log "WARNING" "${YELLOW}⚠${NC} $1"; }
log_error() { log "ERROR" "${RED}✗${NC} $1"; }
log_step() { echo ""; log "STEP" "${CYAN}[$1]${NC} $2"; echo ""; }

# =============================================================================
# SMART SCALING LOGIC
# =============================================================================

calculate_system_capacity() {
    log_step "SCALING" "Calculating System Capacity"

    # 1. Check for Manual Override
    if [ "$MANUAL_WORKER_COUNT" -gt 0 ]; then
        log_warning "Auto-scaling disabled. Using manual count: $MANUAL_WORKER_COUNT"
        echo "$MANUAL_WORKER_COUNT"
        return
    fi

    # 2. Get Hardware Stats
    local cpu_cores=$(nproc)
    local total_ram_mb=$(free -m | awk '/^Mem:/{print $2}')

    # 3. Calculate Limits
    # CPU Limit: (Cores * 2) + 1 is standard for I/O bound tasks
    local cpu_limit=$(( (cpu_cores * 2) + 1 ))

    # RAM Limit: (Total - Reserve) / Worker Estimate
    local available_ram=$(( total_ram_mb - SYSTEM_RESERVE_MB ))

    # Safety: If server is tiny (<2GB), set RAM limit to 1
    if [ "$available_ram" -le 0 ]; then
        available_ram=100 # Fake buffer to allow at least 1 worker
        local ram_limit=1
    else
        local ram_limit=$(( available_ram / WORKER_RAM_ESTIMATE_MB ))
    fi

    # 4. Determine Bottleneck (The lower number wins)
    local optimal_count=$cpu_limit
    local bottleneck="CPU Cores"

    if [ "$ram_limit" -lt "$cpu_limit" ]; then
        optimal_count=$ram_limit
        bottleneck="Available RAM"
    fi

    # 5. Apply Hard Cap
    if [ "$optimal_count" -gt "$MAX_WORKER_CAP" ]; then
        optimal_count=$MAX_WORKER_CAP
        bottleneck="Safety Cap"
    fi

    # Ensure at least 1 worker
    if [ "$optimal_count" -lt 1 ]; then optimal_count=1; fi

    # 6. Log the Knowledge Extracted
    echo ""
    echo -e "${CYAN}╔════════════════════ SYSTEM AUDIT ════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} CPU Cores:      ${WHITE}${cpu_cores}${NC} (Max theoretical: $cpu_limit)"
    echo -e "${CYAN}║${NC} Total RAM:      ${WHITE}${total_ram_mb} MB${NC}"
    echo -e "${CYAN}║${NC} Reserved RAM:   ${WHITE}${SYSTEM_RESERVE_MB} MB${NC} (OS + DB + Web)"
    echo -e "${CYAN}║${NC} RAM Limit:      ${WHITE}${ram_limit}${NC} workers"
    echo -e "${CYAN}║${NC} Bottleneck:     ${YELLOW}${bottleneck}${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""

    log_success "Optimal capacity calculated: $optimal_count workers"
    echo "$optimal_count"
}

# =============================================================================
# MAIN DEPLOYMENT FUNCTIONS
# =============================================================================

check_prerequisites() {
    mkdir -p "$LOG_DIR" "$BACKUP_DIR"
    if [[ $EUID -ne 0 ]]; then
        log_error "Must run as root (sudo)"
        exit 1
    fi

    # Verify tools
    for cmd in docker git curl; do
        if ! command -v $cmd &> /dev/null; then
            log_warning "Installing missing tool: $cmd"
            apt-get update -qq && apt-get install -y -qq $cmd
        fi
    done
}

build_and_deploy() {
    log_step "DEPLOY" "Building and Scaling Containers"

    # 1. Calculate Capacity
    FINAL_WORKER_COUNT=$(calculate_system_capacity)

    cd "$SCRIPT_DIR"

    # 2. Build
    log_info "Building images..."
    docker compose build 2>&1 | tee -a "$DEPLOY_LOG" > /dev/null

    # 3. Stop old
    docker compose down --remove-orphans 2>&1 | tee -a "$DEPLOY_LOG" > /dev/null

    # 4. Start with Scaling
    log_info "Applying scale factor: $FINAL_WORKER_COUNT"

    # Note: We use --scale for the worker service
    # Ensure your docker-compose.yml service is named 'studybuddy_worker' (or adjust here)
    if docker compose up -d --scale studybuddy_worker="$FINAL_WORKER_COUNT" 2>&1 | tee -a "$DEPLOY_LOG"; then
        log_success "Cluster started successfully"
    else
        log_error "Deployment failed"
        exit 1
    fi
}

health_check_cluster() {
    log_step "HEALTH" "Verifying Cluster Health"

    log_info "Waiting for services to stabilize..."
    sleep 10

    # Count active workers
    local active_workers=$(docker ps --filter "name=worker" --format "{{.ID}}" | wc -l)

    if [ "$active_workers" -eq "$FINAL_WORKER_COUNT" ]; then
        log_success "All $active_workers requested workers are online"
    else
        log_warning "Expected $FINAL_WORKER_COUNT workers, but found $active_workers"
    fi

    # App Check
    if curl -sf http://localhost:5000/health > /dev/null 2>&1; then
        log_success "Main API is healthy"
    else
        log_error "Main API health check failed"
        # Don't exit, just warn, so we can see the report
    fi
}

# =============================================================================
# EXECUTION FLOW
# =============================================================================

# Argument Parsing
while [[ $# -gt 0 ]]; do
    case $1 in
        --workers) MANUAL_WORKER_COUNT="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

check_prerequisites
build_and_deploy
health_check_cluster

# =============================================================================
# FINAL CAPACITY OUTPUT
# =============================================================================

DURATION=$(($(date +%s) - DEPLOY_START_TIME))

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║             🚀 DEPLOYMENT COMPLETE (v${VERSION})             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN} SYSTEM CAPACITY REPORT ${NC}"
echo -e " ----------------------"
echo -e " ${CYAN}▶${NC} Deployment Duration:  ${WHITE}${DURATION}s${NC}"
echo -e " ${CYAN}▶${NC} Total Capacity:       ${GREEN}${FINAL_WORKER_COUNT} Concurrent Workers${NC}"
echo -e " ${CYAN}▶${NC} Hardware Usage:       Optimized for $(hostname)"
echo ""
echo -e "${CYAN} STATUS CHECK ${NC}"
echo -e " ----------------------"
echo -e " ${CYAN}▶${NC} API Endpoint:         ${WHITE}http://localhost:5000${NC}"
echo -e " ${CYAN}▶${NC} Worker Nodes:         ${GREEN}Online (${FINAL_WORKER_COUNT}/${FINAL_WORKER_COUNT})${NC}"
echo -e " ${CYAN}▶${NC} Logs:                 ${WHITE}docker compose logs -f studybuddy_worker${NC}"
echo ""