#!/bin/bash
# =============================================================================
# StudyBuddyAI Pre-Deployment Check Script
# =============================================================================
# Tested on: Ubuntu 22.04 LTS (also works on Ubuntu 20.04+, Debian, and other Linux distributions)
#
# This script performs comprehensive checks before deploying with Docker Compose:
# - System requirements (Docker, Docker Compose)
# - Port availability (5000, 27017, 5672, 15672)
# - Network connectivity and DNS resolution
# - Environment configuration
# - System resources (disk space, memory)
# - Docker daemon health
#
# Usage:
#   ./scripts/pre-deploy-check.sh
#   OR
#   bash scripts/pre-deploy-check.sh
# =============================================================================

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters for checks
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
    ((CHECKS_PASSED++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $*"
    ((CHECKS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $*"
    ((CHECKS_WARNING++))
}

section_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $*${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
}

# =============================================================================
# Check Functions
# =============================================================================

check_os() {
    section_header "Operating System Check"
    
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        log_info "OS: $NAME $VERSION"
        log_info "Kernel: $(uname -r)"
        log_success "Operating system detected"
    else
        log_warning "Could not detect OS version"
    fi
}

check_docker() {
    section_header "Docker Installation Check"
    
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        log_info "Found: $DOCKER_VERSION"
        
        # Check if docker daemon is running
        if docker info &> /dev/null; then
            log_success "Docker daemon is running"
        else
            log_error "Docker daemon is not running or user lacks permissions"
            log_info "Try: sudo systemctl start docker"
            log_info "Or add user to docker group: sudo usermod -aG docker \$USER"
        fi
    else
        log_error "Docker is not installed"
        log_info "Install with: curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
    fi
}

check_docker_compose() {
    section_header "Docker Compose Check"
    
    # Check for docker-compose (standalone) or docker compose (plugin)
    if docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(docker compose version)
        log_info "Found: $COMPOSE_VERSION (Docker Compose V2 plugin)"
        log_success "Docker Compose is available"
        export COMPOSE_COMMAND="docker compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version)
        log_info "Found: $COMPOSE_VERSION (standalone)"
        log_success "Docker Compose is available"
        export COMPOSE_COMMAND="docker-compose"
    else
        log_error "Docker Compose is not installed"
        log_info "Install with: sudo apt install docker-compose-plugin"
    fi
}

check_ports() {
    section_header "Port Availability Check"
    
    # Required ports for StudyBuddyAI
    REQUIRED_PORTS=(5000 27017 5672 15672)
    PORT_NAMES=("Flask App" "MongoDB" "RabbitMQ AMQP" "RabbitMQ Management")
    
    for i in "${!REQUIRED_PORTS[@]}"; do
        PORT=${REQUIRED_PORTS[$i]}
        NAME=${PORT_NAMES[$i]}
        
        # Check if port is in use
        if command -v netstat &> /dev/null; then
            if netstat -tuln 2>/dev/null | grep -q ":$PORT "; then
                log_warning "Port $PORT ($NAME) is already in use"
                log_info "Process using port: $(sudo lsof -i :$PORT -t 2>/dev/null | head -1 || echo 'unknown')"
            else
                log_success "Port $PORT ($NAME) is available"
            fi
        elif command -v ss &> /dev/null; then
            if ss -tuln 2>/dev/null | grep -q ":$PORT "; then
                log_warning "Port $PORT ($NAME) is already in use"
            else
                log_success "Port $PORT ($NAME) is available"
            fi
        else
            log_warning "Cannot check port $PORT - netstat/ss not available"
        fi
    done
}

check_network() {
    section_header "Network Connectivity Check"
    
    # Test internet connectivity
    if ping -c 1 -W 2 8.8.8.8 &> /dev/null; then
        log_success "Internet connectivity (ICMP)"
    else
        log_warning "Cannot reach 8.8.8.8 via ping (may be blocked)"
    fi
    
    # Test DNS resolution with multiple providers
    DNS_TESTS=("google.com" "github.com" "pypi.org" "hub.docker.com")
    
    for domain in "${DNS_TESTS[@]}"; do
        if nslookup "$domain" &> /dev/null || host "$domain" &> /dev/null; then
            log_success "DNS resolution: $domain"
        else
            log_error "DNS resolution failed: $domain"
        fi
    done
    
    # Test HTTPS connectivity
    if command -v curl &> /dev/null; then
        if curl -Is --connect-timeout 5 https://www.google.com &> /dev/null; then
            log_success "HTTPS connectivity test"
        else
            log_error "HTTPS connectivity test failed"
        fi
    fi
}

check_env_file() {
    section_header "Environment Configuration Check"
    
    if [[ -f .env ]]; then
        log_success "Found .env file"
        
        # Check for required environment variables
        REQUIRED_VARS=("SECRET_KEY" "ADMIN_EMAIL")
        OPTIONAL_VARS=("GEMINI_API_KEY" "OPENAI_API_KEY")
        
        for var in "${REQUIRED_VARS[@]}"; do
            if grep -q "^${var}=" .env && ! grep -q "^${var}=\"\"" .env && ! grep -q "^${var}=''" .env; then
                if grep "^${var}=" .env | grep -v -q "change-this\|your_.*_here\|example"; then
                    log_success "Required variable set: $var"
                else
                    log_error "Required variable not configured: $var (still has placeholder value)"
                fi
            else
                log_error "Required variable missing: $var"
            fi
        done
        
        # Check at least one AI API key
        HAS_API_KEY=false
        for var in "${OPTIONAL_VARS[@]}"; do
            if grep -q "^${var}=" .env && ! grep -q "^${var}=\"\"" .env; then
                if grep "^${var}=" .env | grep -v -q "your_.*_here"; then
                    log_success "AI API key configured: $var"
                    HAS_API_KEY=true
                fi
            fi
        done
        
        if [[ "$HAS_API_KEY" == false ]]; then
            log_error "No AI API key configured (need GEMINI_API_KEY or OPENAI_API_KEY)"
        fi
        
    else
        log_error ".env file not found"
        log_info "Copy .env.example to .env and configure: cp .env.example .env"
    fi
}

check_system_resources() {
    section_header "System Resources Check"
    
    # Check disk space
    DISK_AVAILABLE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [[ $DISK_AVAILABLE -gt 5 ]]; then
        log_success "Disk space: ${DISK_AVAILABLE}GB available"
    elif [[ $DISK_AVAILABLE -gt 2 ]]; then
        log_warning "Disk space: ${DISK_AVAILABLE}GB available (low)"
    else
        log_error "Disk space: ${DISK_AVAILABLE}GB available (critically low)"
    fi
    
    # Check memory
    if command -v free &> /dev/null; then
        TOTAL_MEM=$(free -g | awk 'NR==2 {print $2}')
        AVAILABLE_MEM=$(free -g | awk 'NR==2 {print $7}')
        log_info "Memory: ${AVAILABLE_MEM}GB available / ${TOTAL_MEM}GB total"
        
        if [[ $AVAILABLE_MEM -gt 1 ]]; then
            log_success "Sufficient memory available"
        else
            log_warning "Low memory available (${AVAILABLE_MEM}GB)"
        fi
    fi
    
    # Check CPU
    CPU_CORES=$(nproc 2>/dev/null || echo "unknown")
    log_info "CPU cores: $CPU_CORES"
    log_success "CPU check completed"
}

check_docker_network() {
    section_header "Docker Network Check"
    
    # Check Docker networks
    if docker network ls &> /dev/null; then
        log_success "Docker network subsystem operational"
        
        # Check if our network already exists
        if docker network ls | grep -q "studybuddy_network"; then
            log_info "StudyBuddy network already exists"
        fi
    else
        log_error "Docker network check failed"
    fi
}

check_docker_images() {
    section_header "Docker Images Check"
    
    # Check if images need to be built/updated
    if docker images | grep -q "studybuddy"; then
        log_info "Found existing StudyBuddy images"
        log_info "Will rebuild with docker compose up --build"
    else
        log_info "No existing StudyBuddy images (first time deployment)"
    fi
    
    # Check for base images that will be needed
    BASE_IMAGES=("python:3.11-slim" "mongo:5.0" "rabbitmq:3.9-management")
    for image in "${BASE_IMAGES[@]}"; do
        if docker images | grep -q "${image%%:*}"; then
            log_info "Base image available: $image"
        else
            log_info "Base image will be pulled: $image"
        fi
    done
    
    log_success "Docker images check completed"
}

cleanup_docker() {
    section_header "Docker Cleanup (Optional)"
    
    log_info "Checking for Docker resources to clean up..."
    
    # Count stopped containers
    STOPPED_CONTAINERS=$(docker ps -aq -f status=exited 2>/dev/null | wc -l)
    if [[ $STOPPED_CONTAINERS -gt 0 ]]; then
        log_warning "Found $STOPPED_CONTAINERS stopped containers"
        log_info "To clean up: docker container prune -f"
    fi
    
    # Count dangling images
    DANGLING_IMAGES=$(docker images -qf dangling=true 2>/dev/null | wc -l)
    if [[ $DANGLING_IMAGES -gt 0 ]]; then
        log_warning "Found $DANGLING_IMAGES dangling images"
        log_info "To clean up: docker image prune -f"
    fi
    
    # Check Docker disk usage
    if command -v docker &> /dev/null; then
        log_info "Docker disk usage:"
        docker system df 2>/dev/null || true
    fi
    
    log_success "Cleanup check completed"
}

check_firewall() {
    section_header "Firewall Check"
    
    # Check if firewall is active
    if command -v ufw &> /dev/null; then
        if sudo ufw status 2>/dev/null | grep -q "Status: active"; then
            log_warning "UFW firewall is active"
            log_info "Ensure ports 5000 (or 80/443 for proxy) are open"
            log_info "Example: sudo ufw allow 5000/tcp"
        else
            log_info "UFW firewall is inactive"
        fi
    elif command -v firewall-cmd &> /dev/null; then
        if sudo firewall-cmd --state 2>/dev/null | grep -q "running"; then
            log_warning "firewalld is active"
            log_info "Ensure required ports are open"
        else
            log_info "firewalld is not running"
        fi
    else
        log_info "No common firewall detected (ufw/firewalld)"
    fi
    
    log_success "Firewall check completed"
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
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
    echo -e "${BLUE}Pre-Deployment System Check${NC}"
    echo ""
    
    # Change to script directory's parent (project root)
    cd "$(dirname "$0")/.."
    log_info "Working directory: $(pwd)"
    
    # Run all checks
    check_os
    check_docker
    check_docker_compose
    check_ports
    check_network
    check_env_file
    check_system_resources
    check_docker_network
    check_docker_images
    cleanup_docker
    check_firewall
    
    # Summary
    section_header "Check Summary"
    echo ""
    echo -e "  ${GREEN}Passed:${NC}   $CHECKS_PASSED"
    echo -e "  ${YELLOW}Warnings:${NC} $CHECKS_WARNING"
    echo -e "  ${RED}Failed:${NC}   $CHECKS_FAILED"
    echo ""
    
    if [[ $CHECKS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}✓ All critical checks passed!${NC}"
        echo ""
        log_info "System is ready for deployment"
        return 0
    else
        echo -e "${RED}✗ Some checks failed - please address the issues above${NC}"
        echo ""
        log_error "Fix the errors before deploying"
        return 1
    fi
}

# Run main function
main
exit $?
