#!/bin/bash
# =============================================================================
# StudyBuddy Health Check Monitor
# =============================================================================
# Continuously monitors application health and restarts components if needed
# =============================================================================

# Configuration
CHECK_INTERVAL=${CHECK_INTERVAL:-30}  # Seconds between checks
MAX_FAILURES=${MAX_FAILURES:-3}      # Failures before restart
LOG_FILE="${LOG_FILE:-/var/log/studybuddy-healthcheck.log}"

# Failure counters
APP_FAILURES=0
MONGO_FAILURES=0
RABBITMQ_FAILURES=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $*" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$LOG_FILE"
}

# Check if running in Docker
if [ -f /.dockerenv ]; then
    IN_DOCKER=true
    APP_URL="http://app:5000"
else
    IN_DOCKER=false
    APP_URL="http://localhost:5000"
fi

check_app_health() {
    # Check basic health endpoint
    if curl -sf "${APP_URL}/health" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

check_detailed_health() {
    # Check detailed health endpoint
    response=$(curl -sf "${APP_URL}/health/detailed" 2>&1)
    if [ $? -eq 0 ]; then
        # Parse response to check component health
        if echo "$response" | grep -q '"status":"healthy"'; then
            return 0
        else
            log_warning "Detailed health check shows unhealthy components"
            echo "$response" | tee -a "$LOG_FILE"
            return 1
        fi
    else
        return 1
    fi
}

check_container_health() {
    local container=$1
    
    if [ "$IN_DOCKER" = true ]; then
        # Running inside Docker, can't check other containers directly
        return 0
    fi
    
    # Check if container is running
    if docker ps --filter "name=$container" --filter "status=running" | grep -q "$container"; then
        # Check container health status
        health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null)
        if [ "$health" = "healthy" ] || [ -z "$health" ]; then
            return 0
        else
            return 1
        fi
    else
        return 1
    fi
}

restart_component() {
    local component=$1
    
    log "Restarting $component..."
    
    if [ "$IN_DOCKER" = true ]; then
        # Can't restart from inside Docker
        log_error "Cannot restart components from inside container"
        return 1
    fi
    
    case "$component" in
        "app")
            if systemctl is-active --quiet studybuddy 2>/dev/null; then
                sudo systemctl restart studybuddy
            else
                docker compose restart app
            fi
            ;;
        "mongo")
            docker compose restart mongo
            ;;
        "rabbitmq")
            docker compose restart rabbitmq
            ;;
        "all")
            if systemctl is-active --quiet studybuddy 2>/dev/null; then
                sudo systemctl restart studybuddy
            else
                docker compose restart
            fi
            ;;
    esac
    
    # Wait for restart
    sleep 10
    
    log_success "$component restarted"
}

# Main monitoring loop
log "Starting StudyBuddy health check monitor"
log "Check interval: ${CHECK_INTERVAL}s, Max failures: ${MAX_FAILURES}"

while true; do
    # Check application health
    if check_app_health; then
        log_success "Application is healthy"
        APP_FAILURES=0
        
        # Check detailed health
        if ! check_detailed_health; then
            log_warning "Some components are unhealthy but app is responding"
        fi
    else
        APP_FAILURES=$((APP_FAILURES + 1))
        log_error "Application health check failed (${APP_FAILURES}/${MAX_FAILURES})"
        
        if [ $APP_FAILURES -ge $MAX_FAILURES ]; then
            log_error "Application failed ${MAX_FAILURES} times, restarting..."
            restart_component "app"
            APP_FAILURES=0
        fi
    fi
    
    # Check MongoDB container (if not in Docker)
    if [ "$IN_DOCKER" = false ]; then
        if check_container_health "studybuddy_mongo"; then
            MONGO_FAILURES=0
        else
            MONGO_FAILURES=$((MONGO_FAILURES + 1))
            log_error "MongoDB check failed (${MONGO_FAILURES}/${MAX_FAILURES})"
            
            if [ $MONGO_FAILURES -ge $MAX_FAILURES ]; then
                log_error "MongoDB failed ${MAX_FAILURES} times, restarting..."
                restart_component "mongo"
                MONGO_FAILURES=0
            fi
        fi
        
        # Check RabbitMQ container
        if check_container_health "studybuddy_rabbitmq"; then
            RABBITMQ_FAILURES=0
        else
            RABBITMQ_FAILURES=$((RABBITMQ_FAILURES + 1))
            log_error "RabbitMQ check failed (${RABBITMQ_FAILURES}/${MAX_FAILURES})"
            
            if [ $RABBITMQ_FAILURES -ge $MAX_FAILURES ]; then
                log_error "RabbitMQ failed ${MAX_FAILURES} times, restarting..."
                restart_component "rabbitmq"
                RABBITMQ_FAILURES=0
            fi
        fi
    fi
    
    # Wait before next check
    sleep "$CHECK_INTERVAL"
done
