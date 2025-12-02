#!/bin/bash
# =============================================================================
# StudyBuddyAI Smart Deployment Script
# =============================================================================
# Auto-fixes common issues and deploys
# Tested on: Ubuntu 22.04 LTS
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_error() { echo -e "${RED}[✗]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $*"; }
log_fix() { echo -e "${YELLOW}[FIX]${NC} $*"; }

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
    echo -e "${NC}${BLUE}Smart Auto-Fix Deployment${NC}\n"
}

# =============================================================================
# Auto-Fix Functions
# =============================================================================

fix_docker() {
    log_info "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        log_warning "Docker not installed"
        log_fix "Installing Docker..."
        
        if curl -fsSL https://get.docker.com -o /tmp/get-docker.sh 2>/dev/null; then
            sudo sh /tmp/get-docker.sh
            rm /tmp/get-docker.sh
            log_success "Docker installed"
        else
            log_error "Failed to download Docker installer"
            log_info "Install manually: curl -fsSL https://get.docker.com | sudo sh"
            return 1
        fi
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_warning "Docker daemon not running"
        log_fix "Starting Docker daemon..."
        
        sudo systemctl start docker
        sudo systemctl enable docker
        
        if docker info &> /dev/null; then
            log_success "Docker daemon started"
        else
            log_error "Failed to start Docker daemon"
            return 1
        fi
    else
        log_success "Docker is running"
    fi
    
    # Check Docker permissions
    if ! docker ps &> /dev/null; then
        log_warning "Docker permission issues"
        log_fix "Adding user to docker group..."
        
        sudo usermod -aG docker $USER
        log_warning "Trying with newgrp..."
        
        # Try to use newgrp to apply group immediately
        if sg docker "docker ps" &> /dev/null; then
            log_success "Docker permissions fixed"
        else
            log_warning "Please logout and login again for Docker permissions to take effect"
            log_info "Or run: newgrp docker"
        fi
    fi
    
    return 0
}

fix_docker_compose() {
    log_info "Checking Docker Compose..."
    
    if docker compose version &> /dev/null; then
        export COMPOSE_CMD="docker compose"
        log_success "Docker Compose V2 found"
        return 0
    elif command -v docker-compose &> /dev/null; then
        export COMPOSE_CMD="docker-compose"
        log_success "Docker Compose V1 found"
        return 0
    fi
    
    log_warning "Docker Compose not found"
    log_fix "Installing Docker Compose plugin..."
    
    if sudo apt-get update && sudo apt-get install -y docker-compose-plugin; then
        export COMPOSE_CMD="docker compose"
        log_success "Docker Compose installed"
        return 0
    else
        log_error "Failed to install Docker Compose"
        log_info "Install manually: sudo apt install docker-compose-plugin"
        return 1
    fi
}

fix_ports() {
    log_info "Checking port availability..."
    
    REQUIRED_PORTS=(5000 27017 5672 15672)
    PORT_NAMES=("Flask" "MongoDB" "RabbitMQ" "RabbitMQ-UI")
    PORTS_OK=true
    
    for i in "${!REQUIRED_PORTS[@]}"; do
        PORT=${REQUIRED_PORTS[$i]}
        NAME=${PORT_NAMES[$i]}
        
        if command -v ss &> /dev/null && ss -tuln | grep -q ":$PORT "; then
            log_warning "Port $PORT ($NAME) is in use"
            
            # Try to find and stop the process
            PID=$(sudo lsof -ti:$PORT 2>/dev/null || echo "")
            if [[ -n "$PID" ]]; then
                PROCESS=$(ps -p $PID -o comm= 2>/dev/null || echo "unknown")
                
                # Check if it's our own Docker container
                if [[ "$PROCESS" == *"docker"* ]] || docker ps --format '{{.Names}}' | grep -q "studybuddy"; then
                    log_fix "Stopping existing StudyBuddy containers on port $PORT..."
                    docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true
                    sleep 2
                else
                    log_warning "Port $PORT used by: $PROCESS (PID: $PID)"
                    log_info "To free it: sudo kill $PID"
                    PORTS_OK=false
                fi
            fi
        else
            log_success "Port $PORT available"
        fi
    done
    
    if [[ "$PORTS_OK" == false ]]; then
        log_warning "Some ports are still in use - deployment may fail"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 1
        fi
    fi
    
    return 0
}

fix_network() {
    log_info "Checking network connectivity..."
    
    # Test DNS resolution
    if ! nslookup google.com &> /dev/null && ! host google.com &> /dev/null; then
        log_warning "DNS resolution issues detected"
        log_fix "Configuring Docker DNS..."
        
        sudo mkdir -p /etc/docker
        if [[ ! -f /etc/docker/daemon.json ]] || ! grep -q "dns" /etc/docker/daemon.json; then
            sudo tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
    "dns": ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
}
EOF
            log_fix "Restarting Docker with new DNS settings..."
            sudo systemctl restart docker
            sleep 3
            log_success "DNS configuration updated"
        fi
    else
        log_success "Network connectivity OK"
    fi
    
    return 0
}

fix_env() {
    log_info "Checking environment configuration..."
    
    if [[ ! -f .env ]]; then
        log_warning ".env file not found"
        log_fix "Creating .env from template..."
        
        if [[ -f .env.example ]]; then
            cp .env.example .env
            log_success ".env created from template"
        else
            log_error ".env.example not found"
            return 1
        fi
    fi
    
    # Check for placeholder values
    NEEDS_CONFIG=false
    
    if grep -q "change-this" .env 2>/dev/null; then
        log_warning "SECRET_KEY has placeholder value"
        log_fix "Generating secure SECRET_KEY..."
        
        NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
        
        if [[ -n "$NEW_SECRET" ]]; then
            # Use @ as delimiter for sed since / might be in the key
            sed -i "s@SECRET_KEY=\"change-this-to-a-very-secret-key-in-production\"@SECRET_KEY=\"$NEW_SECRET\"@g" .env
            log_success "SECRET_KEY generated"
        else
            log_warning "Could not auto-generate SECRET_KEY"
            NEEDS_CONFIG=true
        fi
    fi
    
    if ! grep -q "^GEMINI_API_KEY=.*[a-zA-Z0-9]" .env && ! grep -q "^OPENAI_API_KEY=.*[a-zA-Z0-9]" .env; then
        log_warning "No AI API key configured"
        NEEDS_CONFIG=true
    fi
    
    if ! grep -q "^ADMIN_EMAIL=.*@" .env; then
        log_warning "ADMIN_EMAIL not configured"
        NEEDS_CONFIG=true
    fi
    
    if [[ "$NEEDS_CONFIG" == true ]]; then
        log_warning "Manual configuration required in .env:"
        echo ""
        echo "  Required settings:"
        echo "  1. ADMIN_EMAIL=your_email@example.com"
        echo "  2. GEMINI_API_KEY=your_key  (or OPENAI_API_KEY)"
        echo ""
        read -p "Open .env for editing now? (Y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            ${EDITOR:-nano} .env
        else
            log_error "Configuration incomplete - deployment will fail"
            return 1
        fi
    else
        log_success "Configuration OK"
    fi
    
    return 0
}

fix_disk_space() {
    log_info "Checking disk space..."
    
    DISK_GB=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    
    if [[ $DISK_GB -lt 2 ]]; then
        log_warning "Low disk space: ${DISK_GB}GB available"
        log_fix "Cleaning Docker resources..."
        
        docker system prune -f &> /dev/null || true
        
        DISK_GB=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
        if [[ $DISK_GB -lt 2 ]]; then
            log_error "Still low on disk space after cleanup: ${DISK_GB}GB"
            log_info "Free up space manually or use: docker system prune -a --volumes"
            return 1
        else
            log_success "Freed up disk space: ${DISK_GB}GB available"
        fi
    else
        log_success "Disk space OK: ${DISK_GB}GB available"
    fi
    
    return 0
}

fix_docker_network() {
    log_info "Checking Docker network..."
    
    if ! docker network ls &> /dev/null; then
        log_warning "Docker network issues"
        log_fix "Restarting Docker..."
        sudo systemctl restart docker
        sleep 3
    fi
    
    # Clean up any orphaned networks
    if docker network ls | grep -q "studybuddy"; then
        log_info "Cleaning existing StudyBuddy network..."
        docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true
    fi
    
    log_success "Docker network OK"
    return 0
}

# =============================================================================
# Main Deployment
# =============================================================================

deploy() {
    log_info "Building and starting services..."
    
    # Make sure we're using the right compose command
    if [[ -z "$COMPOSE_CMD" ]]; then
        if docker compose version &> /dev/null; then
            COMPOSE_CMD="docker compose"
        else
            COMPOSE_CMD="docker-compose"
        fi
    fi
    
    # Stop any existing containers
    $COMPOSE_CMD down 2>/dev/null || true
    
    # Build and start
    log_info "Building images (this may take a few minutes)..."
    $COMPOSE_CMD build --pull || {
        log_error "Build failed"
        log_info "Check logs above for errors"
        return 1
    }
    
    log_info "Starting services..."
    $COMPOSE_CMD up -d || {
        log_error "Failed to start services"
        return 1
    }
    
    log_info "Waiting for services to be healthy..."
    sleep 15
    
    # Check status
    RUNNING=$($COMPOSE_CMD ps --format json 2>/dev/null | grep -c '"State":"running"' || echo 0)
    
    if [[ $RUNNING -ge 3 ]]; then
        log_success "Services running ($RUNNING containers)"
        return 0
    else
        log_warning "Only $RUNNING containers running (expected 4)"
        log_info "Check status: $COMPOSE_CMD ps"
        log_info "View logs: $COMPOSE_CMD logs -f"
        return 1
    fi
}

show_success() {
    local IP=$(hostname -I | awk '{print $1}')
    
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✓ Deployment Complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BLUE}Access Points:${NC}"
    echo -e "  ${GREEN}→${NC} Application:      http://localhost:5000"
    if [[ -n "$IP" && "$IP" != "127.0.0.1" ]]; then
        echo -e "  ${GREEN}→${NC} External Access:  http://${IP}:5000"
    fi
    echo -e "  ${GREEN}→${NC} RabbitMQ UI:      http://localhost:15672"
    echo ""
    echo -e "${BLUE}Useful Commands:${NC}"
    echo -e "  ${YELLOW}View logs:${NC}    $COMPOSE_CMD logs -f app"
    echo -e "  ${YELLOW}Check status:${NC} $COMPOSE_CMD ps"
    echo -e "  ${YELLOW}Stop:${NC}         $COMPOSE_CMD down"
    echo -e "  ${YELLOW}Restart:${NC}      $COMPOSE_CMD restart app"
    echo ""
    
    # Try to test the health endpoint
    sleep 2
    if curl -sf http://localhost:5000/health &> /dev/null; then
        echo -e "${GREEN}✓ Application is responding${NC}"
    else
        echo -e "${YELLOW}! Application may still be starting up...${NC}"
        echo -e "  Wait 30 seconds and try: curl http://localhost:5000/health"
    fi
    echo ""
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    show_banner
    
    log_info "Starting automated deployment with auto-fix..."
    echo ""
    
    # Run all checks with auto-fix
    fix_docker || exit 1
    fix_docker_compose || exit 1
    fix_network || exit 1
    fix_disk_space || exit 1
    fix_env || exit 1
    fix_ports || exit 1
    fix_docker_network || exit 1
    
    echo ""
    log_info "All checks passed - proceeding with deployment"
    echo ""
    
    # Deploy
    if deploy; then
        show_success
        exit 0
    else
        echo ""
        log_error "Deployment failed"
        log_info "Check the error messages above"
        log_info "View logs: $COMPOSE_CMD logs -f"
        exit 1
    fi
}

# Handle Ctrl+C
trap 'echo ""; log_warning "Deployment interrupted"; exit 130' INT

# Run
main
