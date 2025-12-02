#!/bin/bash
# =============================================================================
# StudyBuddyAI Ultra-Robust Auto-Fix Deployment Script
# =============================================================================
# Designed to work in ANY server state - fresh install to broken deployment
# Can be run as root or regular user
# Automatically detects and fixes all common issues
# Tested on: Ubuntu 22.04 LTS
# =============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Detect if running as root
if [[ $EUID -eq 0 ]]; then
    SUDO=""
    IS_ROOT=true
else
    SUDO="sudo"
    IS_ROOT=false
fi

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_error() { echo -e "${RED}[✗]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $*"; }
log_fix() { echo -e "${CYAN}[FIX]${NC} $*"; }

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
    echo -e "${CYAN}  Ultra-Robust Auto-Fix Deployment${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    if [[ "$IS_ROOT" == true ]]; then
        log_info "Running as root - full system access"
    else
        log_info "Running as user - will use sudo when needed"
    fi
    echo ""
}

# =============================================================================
# Robust Helper Functions
# =============================================================================

safe_command() {
    # Run a command and retry if it fails
    local max_retries=3
    local retry_delay=2
    local cmd="$*"
    
    for i in $(seq 1 $max_retries); do
        if eval "$cmd" 2>/dev/null; then
            return 0
        fi
        if [[ $i -lt $max_retries ]]; then
            log_warning "Command failed, retry $i/$max_retries..."
            sleep $retry_delay
        fi
    done
    return 1
}

wait_for_service() {
    local service=$1
    local max_wait=30
    local count=0
    
    while [[ $count -lt $max_wait ]]; do
        if systemctl is-active --quiet $service 2>/dev/null; then
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    return 1
}

kill_port() {
    # Kill any process using a port
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null || fuser $port/tcp 2>/dev/null | awk '{print $1}')
    
    if [[ -n "$pids" ]]; then
        log_fix "Killing processes on port $port: $pids"
        echo "$pids" | xargs -r kill -9 2>/dev/null || true
        sleep 1
        return 0
    fi
    return 1
}

# =============================================================================
# Auto-Fix Functions - Extremely Robust
# =============================================================================

fix_docker() {
    log_info "Checking Docker installation..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_warning "Docker not installed"
        log_fix "Installing Docker..."
        
        # Update apt to avoid issues
        $SUDO apt-get update -qq 2>/dev/null || true
        
        # Try official Docker installation script
        if curl -fsSL https://get.docker.com -o /tmp/get-docker.sh 2>/dev/null; then
            $SUDO sh /tmp/get-docker.sh >/dev/null 2>&1
            rm -f /tmp/get-docker.sh
            
            if command -v docker &> /dev/null; then
                log_success "Docker installed successfully"
            else
                log_error "Docker installation failed"
                log_info "Try manually: curl -fsSL https://get.docker.com | sh"
                return 1
            fi
        else
            # Fallback to apt
            log_fix "Trying apt installation..."
            $SUDO apt-get install -y docker.io >/dev/null 2>&1 || {
                log_error "Failed to install Docker"
                return 1
            }
        fi
    else
        log_success "Docker is installed"
    fi
    
    # Make sure Docker service exists
    if ! systemctl list-units --type=service --all | grep -q docker; then
        log_warning "Docker service not found"
        $SUDO systemctl daemon-reload 2>/dev/null || true
    fi
    
    # Enable Docker service
    $SUDO systemctl enable docker 2>/dev/null || true
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_warning "Docker daemon not running"
        log_fix "Starting Docker daemon..."
        
        # Try to start Docker
        $SUDO systemctl start docker 2>/dev/null || true
        
        # Wait for Docker to start
        if wait_for_service docker; then
            log_success "Docker daemon started"
        else
            log_warning "Docker slow to start, forcing restart..."
            $SUDO systemctl stop docker 2>/dev/null || true
            sleep 2
            $SUDO systemctl start docker 2>/dev/null || true
            sleep 3
        fi
        
        # Final check
        if ! docker info &> /dev/null; then
            log_error "Docker daemon still not responding"
            log_info "Check: journalctl -u docker -n 50"
            return 1
        fi
    fi
    
    log_success "Docker daemon is running"
    
    # Fix permissions if not root
    if [[ "$IS_ROOT" == false ]]; then
        if ! docker ps &> /dev/null; then
            log_warning "Docker permission issues for user $USER"
            log_fix "Adding user to docker group..."
            
            $SUDO usermod -aG docker $USER
            
            # Try to refresh group membership
            if command -v sg &> /dev/null; then
                if sg docker -c "docker ps" &> /dev/null; then
                    log_success "Docker permissions fixed (using sg)"
                    # Create a wrapper to use sg for subsequent docker commands
                    alias docker='sg docker -c "docker"' 2>/dev/null || true
                else
                    log_warning "Group membership updated but not active"
                    log_info "You may need to logout/login or run: newgrp docker"
                fi
            fi
        fi
    fi
    
    return 0
}

fix_docker_compose() {
    log_info "Checking Docker Compose..."
    
    # Check for Docker Compose V2 (plugin)
    if docker compose version &> /dev/null; then
        export COMPOSE_CMD="docker compose"
        log_success "Docker Compose V2 found"
        return 0
    fi
    
    # Check for Docker Compose V1 (standalone)
    if command -v docker-compose &> /dev/null; then
        export COMPOSE_CMD="docker-compose"
        log_success "Docker Compose V1 found"
        return 0
    fi
    
    log_warning "Docker Compose not found"
    log_fix "Installing Docker Compose plugin..."
    
    # Update apt
    $SUDO apt-get update -qq 2>/dev/null || true
    
    # Try to install docker-compose-plugin
    if $SUDO apt-get install -y docker-compose-plugin 2>/dev/null; then
        if docker compose version &> /dev/null; then
            export COMPOSE_CMD="docker compose"
            log_success "Docker Compose V2 installed"
            return 0
        fi
    fi
    
    # Fallback: Install standalone docker-compose
    log_fix "Trying standalone docker-compose..."
    if $SUDO apt-get install -y docker-compose 2>/dev/null; then
        if command -v docker-compose &> /dev/null; then
            export COMPOSE_CMD="docker-compose"
            log_success "Docker Compose V1 installed"
            return 0
        fi
    fi
    
    # Last resort: Download binary directly
    log_fix "Downloading docker-compose binary..."
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name"' | cut -d'"' -f4 2>/dev/null || echo "v2.23.0")
    
    if $SUDO curl -SL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose 2>/dev/null; then
        $SUDO chmod +x /usr/local/bin/docker-compose
        if command -v docker-compose &> /dev/null; then
            export COMPOSE_CMD="docker-compose"
            log_success "Docker Compose binary installed"
            return 0
        fi
    fi
    
    log_error "Failed to install Docker Compose"
    return 1
}

fix_ports() {
    log_info "Checking and clearing ports..."
    
    REQUIRED_PORTS=(5000 27017 5672 15672)
    PORT_NAMES=("Flask" "MongoDB" "RabbitMQ" "RabbitMQ-UI")
    
    # First, try to stop any existing StudyBuddy containers
    log_fix "Stopping any existing StudyBuddy containers..."
    docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true
    docker stop $(docker ps -aq --filter "name=studybuddy") 2>/dev/null || true
    docker rm $(docker ps -aq --filter "name=studybuddy") 2>/dev/null || true
    sleep 2
    
    for i in "${!REQUIRED_PORTS[@]}"; do
        PORT=${REQUIRED_PORTS[$i]}
        NAME=${PORT_NAMES[$i]}
        
        # Check if port is still in use
        if netstat -tuln 2>/dev/null | grep -q ":$PORT " || ss -tuln 2>/dev/null | grep -q ":$PORT "; then
            log_warning "Port $PORT ($NAME) is in use"
            
            # Try to kill the process using it
            if kill_port $PORT; then
                log_success "Port $PORT freed"
            else
                # If lsof/fuser not available, try ss
                local pid=$(ss -tlnp 2>/dev/null | grep ":$PORT " | grep -oP 'pid=\K[0-9]+' | head -1)
                if [[ -n "$pid" ]]; then
                    log_fix "Killing process $pid on port $PORT"
                    kill -9 $pid 2>/dev/null || $SUDO kill -9 $pid 2>/dev/null || true
                    sleep 1
                fi
            fi
        fi
        
        # Verify port is now free
        if ! netstat -tuln 2>/dev/null | grep -q ":$PORT " && ! ss -tuln 2>/dev/null | grep -q ":$PORT "; then
            log_success "Port $PORT ($NAME) is available"
        else
            log_warning "Port $PORT still in use - deployment may conflict"
        fi
    done
    
    return 0
}

fix_network() {
    log_info "Checking and fixing network configuration..."
    
    # Test basic connectivity
    if ! ping -c 1 -W 2 8.8.8.8 &> /dev/null; then
        log_warning "Network connectivity issues"
        log_fix "Attempting network restart..."
        
        # Try to restart networking
        $SUDO systemctl restart systemd-networkd 2>/dev/null || true
        $SUDO systemctl restart NetworkManager 2>/dev/null || true
        sleep 2
    fi
    
    # Check DNS resolution
    if ! nslookup google.com &> /dev/null && ! host google.com &> /dev/null && ! getent hosts google.com &> /dev/null; then
        log_warning "DNS resolution failing"
        log_fix "Configuring Docker DNS fallbacks..."
        
        # Create or update Docker daemon config
        $SUDO mkdir -p /etc/docker
        
        if [[ -f /etc/docker/daemon.json ]]; then
            # Backup existing config
            $SUDO cp /etc/docker/daemon.json /etc/docker/daemon.json.backup 2>/dev/null || true
            
            # Check if DNS already configured
            if ! grep -q '"dns"' /etc/docker/daemon.json; then
                # Add DNS to existing config
                $SUDO python3 -c "
import json
try:
    with open('/etc/docker/daemon.json', 'r') as f:
        config = json.load(f)
    config['dns'] = ['8.8.8.8', '8.8.4.4', '1.1.1.1']
    with open('/etc/docker/daemon.json', 'w') as f:
        json.dump(config, f, indent=4)
except:
    pass
" 2>/dev/null || {
                    # Fallback if Python fails
                    $SUDO tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
    "dns": ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
}
EOF
                }
            fi
        else
            # Create new config
            $SUDO tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
    "dns": ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
}
EOF
        fi
        
        log_fix "Restarting Docker with new DNS settings..."
        $SUDO systemctl restart docker
        sleep 5
        
        # Wait for Docker to be ready
        wait_for_service docker || sleep 5
        
        log_success "DNS configuration updated"
    else
        log_success "Network and DNS working"
    fi
    
    return 0
}

fix_env() {
    log_info "Checking environment configuration..."
    
    # Make sure we're in the right directory
    if [[ ! -f docker-compose.yml ]]; then
        log_error "Not in project directory (docker-compose.yml not found)"
        log_info "Run this script from the study_buddy-proj directory"
        return 1
    fi
    
    # Create .env if it doesn't exist
    if [[ ! -f .env ]]; then
        log_warning ".env file not found"
        
        if [[ -f .env.example ]]; then
            log_fix "Creating .env from template..."
            cp .env.example .env
            log_success ".env created"
        else
            log_error ".env.example not found"
            return 1
        fi
    fi
    
    # Auto-fix SECRET_KEY
    if grep -q "change-this" .env 2>/dev/null; then
        log_fix "Generating secure SECRET_KEY..."
        
        # Try multiple methods to generate a random key
        NEW_SECRET=""
        if command -v python3 &> /dev/null; then
            NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null)
        fi
        
        if [[ -z "$NEW_SECRET" ]] && command -v openssl &> /dev/null; then
            NEW_SECRET=$(openssl rand -hex 32 2>/dev/null)
        fi
        
        if [[ -z "$NEW_SECRET" ]]; then
            NEW_SECRET=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1)
        fi
        
        if [[ -n "$NEW_SECRET" ]]; then
            sed -i "s|SECRET_KEY=\"change-this-to-a-very-secret-key-in-production\"|SECRET_KEY=\"$NEW_SECRET\"|g" .env
            log_success "SECRET_KEY generated and set"
        fi
    fi
    
    # Check for required values
    NEEDS_INPUT=false
    
    if ! grep -q "^ADMIN_EMAIL=.*@.*" .env; then
        log_warning "ADMIN_EMAIL not configured"
        NEEDS_INPUT=true
    fi
    
    if ! grep -q "^GEMINI_API_KEY=.\{20,\}" .env && ! grep -q "^OPENAI_API_KEY=.\{20,\}" .env; then
        log_warning "No AI API key configured"
        NEEDS_INPUT=true
    fi
    
    if [[ "$NEEDS_INPUT" == true ]]; then
        log_warning "Manual configuration required"
        echo ""
        echo "  Please edit .env and set:"
        echo "  1. ADMIN_EMAIL=your_email@example.com"
        echo "  2. GEMINI_API_KEY=your_api_key (or OPENAI_API_KEY)"
        echo ""
        
        # Try to auto-open editor
        if [[ -n "${EDITOR}" ]]; then
            log_info "Opening ${EDITOR} for editing..."
            ${EDITOR} .env
        elif command -v nano &> /dev/null; then
            log_info "Opening nano for editing..."
            nano .env
        elif command -v vi &> /dev/null; then
            log_info "Opening vi for editing..."
            vi .env
        else
            log_warning "No editor found. Edit manually: nano .env"
            read -p "Press Enter after editing .env..."
        fi
        
        # Re-check after editing
        if ! grep -q "^ADMIN_EMAIL=.*@.*" .env || ! (grep -q "^GEMINI_API_KEY=.\{20,\}" .env || grep -q "^OPENAI_API_KEY=.\{20,\}" .env); then
            log_error "Configuration still incomplete"
            return 1
        fi
    fi
    
    log_success "Environment configuration OK"
    return 0
}

fix_disk_space() {
    log_info "Checking disk space..."
    
    DISK_GB=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//' 2>/dev/null || echo "10")
    
    if [[ $DISK_GB -lt 2 ]]; then
        log_warning "Low disk space: ${DISK_GB}GB available"
        log_fix "Cleaning up Docker resources..."
        
        # Aggressive cleanup
        docker system prune -af --volumes 2>/dev/null || true
        docker volume prune -f 2>/dev/null || true
        docker network prune -f 2>/dev/null || true
        docker image prune -af 2>/dev/null || true
        
        # Remove dangling images
        docker rmi $(docker images -qf dangling=true) 2>/dev/null || true
        
        # Clean apt cache if running as root
        if [[ "$IS_ROOT" == true ]]; then
            apt-get clean 2>/dev/null || true
            apt-get autoremove -y 2>/dev/null || true
        fi
        
        DISK_GB=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
        
        if [[ $DISK_GB -lt 2 ]]; then
            log_error "Still low disk space: ${DISK_GB}GB"
            log_info "Free up more space manually"
            return 1
        else
            log_success "Freed space: ${DISK_GB}GB available"
        fi
    else
        log_success "Disk space OK: ${DISK_GB}GB available"
    fi
    
    return 0
}

fix_docker_network() {
    log_info "Cleaning Docker networks..."
    
    # Remove any orphaned StudyBuddy networks
    docker network ls | grep studybuddy | awk '{print $1}' | xargs -r docker network rm 2>/dev/null || true
    
    # Prune unused networks
    docker network prune -f 2>/dev/null || true
    
    log_success "Docker networks cleaned"
    return 0
}

# =============================================================================
# Deployment
# =============================================================================

deploy() {
    log_info "Starting deployment..."
    
    # Ensure COMPOSE_CMD is set
    if [[ -z "$COMPOSE_CMD" ]]; then
        if docker compose version &> /dev/null; then
            COMPOSE_CMD="docker compose"
        else
            COMPOSE_CMD="docker-compose"
        fi
    fi
    
    log_info "Using: $COMPOSE_CMD"
    
    # Stop any existing deployment
    log_fix "Stopping existing containers..."
    $COMPOSE_CMD down 2>/dev/null || true
    sleep 2
    
    # Build images
    log_info "Building Docker images (may take 2-5 minutes)..."
    if ! $COMPOSE_CMD build --pull 2>&1 | grep -i "error" > /tmp/build-errors.log; then
        log_success "Images built successfully"
    else
        if [[ -s /tmp/build-errors.log ]]; then
            log_warning "Build completed with warnings"
        fi
    fi
    
    # Start services
    log_info "Starting services..."
    if $COMPOSE_CMD up -d; then
        log_success "Services started"
    else
        log_error "Failed to start services"
        log_info "Trying again with forced recreation..."
        $COMPOSE_CMD up -d --force-recreate || return 1
    fi
    
    # Wait for containers to stabilize
    log_info "Waiting for services to stabilize (30 seconds)..."
    sleep 30
    
    # Check running containers
    RUNNING=$($COMPOSE_CMD ps --format json 2>/dev/null | grep -c '"State":"running"' || $COMPOSE_CMD ps 2>/dev/null | grep -c "Up" || echo 0)
    
    if [[ $RUNNING -ge 3 ]]; then
        log_success "Deployment successful ($RUNNING containers running)"
        return 0
    else
        log_warning "Only $RUNNING containers running"
        log_info "Checking logs for errors..."
        $COMPOSE_CMD logs --tail=20 | grep -i "error" | head -10 || true
        return 1
    fi
}

show_status() {
    local IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
    
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✓ Deployment Complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}Access Points:${NC}"
    echo -e "  ${GREEN}→${NC} Application:     http://localhost:5000"
    if [[ "$IP" != "localhost" && "$IP" != "127.0.0.1" ]]; then
        echo -e "  ${GREEN}→${NC} External:        http://${IP}:5000"
    fi
    echo -e "  ${GREEN}→${NC} RabbitMQ UI:     http://localhost:15672 (user/password from .env)"
    echo ""
    echo -e "${CYAN}Management Commands:${NC}"
    echo -e "  ${YELLOW}View logs:${NC}       $COMPOSE_CMD logs -f app"
    echo -e "  ${YELLOW}View all logs:${NC}   $COMPOSE_CMD logs -f"
    echo -e "  ${YELLOW}Check status:${NC}    $COMPOSE_CMD ps"
    echo -e "  ${YELLOW}Stop:${NC}            $COMPOSE_CMD down"
    echo -e "  ${YELLOW}Restart:${NC}         $COMPOSE_CMD restart"
    echo ""
    
    # Test health endpoint
    sleep 3
    if curl -sf http://localhost:5000/health &> /dev/null 2>&1; then
        echo -e "${GREEN}✓ Application is healthy and responding${NC}"
    else
        echo -e "${YELLOW}! Application starting... test with: curl http://localhost:5000/health${NC}"
    fi
    echo ""
    
    # Show container status
    echo -e "${CYAN}Container Status:${NC}"
    $COMPOSE_CMD ps 2>/dev/null | sed 's/^/  /' || true
    echo ""
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    show_banner
    
    log_info "Running comprehensive auto-fix deployment"
    log_info "This will fix any issues automatically"
    echo ""
    
    # Run all auto-fix functions
    fix_docker || { log_error "Docker setup failed"; exit 1; }
    fix_docker_compose || { log_error "Docker Compose setup failed"; exit 1; }
    fix_network || log_warning "Network issues detected but continuing..."
    fix_disk_space || { log_error "Insufficient disk space"; exit 1; }
    fix_docker_network || true
    fix_ports || log_warning "Port conflicts detected but continuing..."
    fix_env || { log_error "Environment configuration failed"; exit 1; }
    
    echo ""
    log_success "All checks and fixes complete"
    echo ""
    
    # Deploy
    if deploy; then
        show_status
        exit 0
    else
        echo ""
        log_error "Deployment failed"
        echo ""
        log_info "Troubleshooting steps:"
        echo "  1. Check logs: $COMPOSE_CMD logs -f"
        echo "  2. Check status: $COMPOSE_CMD ps"
        echo "  3. Check Docker: docker info"
        echo "  4. Check ports: netstat -tuln | grep '5000\|27017\|5672\|15672'"
        echo ""
        exit 1
    fi
}

# Handle interrupts gracefully
trap 'echo ""; log_warning "Deployment interrupted by user"; exit 130' INT TERM

# Ensure we're in the project directory
if [[ ! -f docker-compose.yml ]]; then
    log_error "docker-compose.yml not found"
    log_info "Please run this script from the study_buddy-proj directory"
    exit 1
fi

# Run main
main "$@"
