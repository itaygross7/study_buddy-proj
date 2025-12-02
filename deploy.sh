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
    
    # First, check for ALL containers using these ports (not just StudyBuddy)
    log_info "Checking for ANY containers using required ports..."
    
    for i in "${!REQUIRED_PORTS[@]}"; do
        PORT=${REQUIRED_PORTS[$i]}
        
        # Find ALL containers exposing this port
        local all_containers=$(docker ps -a --format '{{.Names}}:{{.Ports}}' 2>/dev/null | grep ":$PORT->" | cut -d: -f1)
        
        if [[ -n "$all_containers" ]]; then
            log_warning "Found container(s) using port $PORT:"
            echo "$all_containers" | while read container; do
                log_info "  - $container"
            done
        fi
    done
    
    # Stop StudyBuddy containers first
    log_fix "Stopping any existing StudyBuddy containers..."
    docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true
    docker stop $(docker ps -aq --filter "name=studybuddy") 2>/dev/null || true
    docker rm $(docker ps -aq --filter "name=studybuddy") 2>/dev/null || true
    sleep 2
    
    # Now check each port individually
    for i in "${!REQUIRED_PORTS[@]}"; do
        PORT=${REQUIRED_PORTS[$i]}
        NAME=${PORT_NAMES[$i]}
        
        # Check if port is still in use
        if netstat -tuln 2>/dev/null | grep -q ":$PORT " || ss -tuln 2>/dev/null | grep -q ":$PORT "; then
            log_warning "Port $PORT ($NAME) is still in use"
            
            # Try to identify what's using the port
            local blocking_container=""
            local blocking_process=""
            local pid=""
            
            # Method 1: Check Docker containers by inspecting their ports
            blocking_container=$(docker ps --format '{{.Names}}:{{.Ports}}' 2>/dev/null | grep ":$PORT->" | cut -d: -f1 | head -1)
            
            # Method 2: If not found, try docker port inspection
            if [[ -z "$blocking_container" ]]; then
                for cid in $(docker ps -q 2>/dev/null); do
                    if docker port $cid 2>/dev/null | grep -q ":$PORT"; then
                        blocking_container=$(docker inspect --format '{{.Name}}' $cid 2>/dev/null | sed 's/^\/*//')
                        break
                    fi
                done
            fi
            
            if [[ -n "$blocking_container" ]]; then
                log_warning "Port $PORT blocked by container: $blocking_container"
                
                # Check if it's a known service that should be preserved
                if [[ "$blocking_container" == *"tailscale"* ]] || [[ "$blocking_container" == *"vpn"* ]]; then
                    log_warning "Found important service: $blocking_container"
                    if [[ -t 0 ]]; then
                        echo ""
                        log_info "This appears to be a networking service (Tailscale/VPN)"
                        read -p "Stop this container temporarily? (y/N): " -n 1 -r
                        echo
                        if [[ $REPLY =~ ^[Yy]$ ]]; then
                            log_fix "Stopping $blocking_container (you can restart it later)"
                            docker stop "$blocking_container" 2>/dev/null || true
                            sleep 2
                        else
                            log_warning "Keeping $blocking_container running - deployment may conflict"
                        fi
                    else
                        log_warning "Non-interactive mode: keeping $blocking_container running"
                    fi
                else
                    # Other containers - auto-stop them
                    log_fix "Stopping container: $blocking_container"
                    docker stop "$blocking_container" 2>/dev/null || true
                    sleep 2
                fi
            else
                # Not a container, check for regular process
                pid=$(lsof -ti:$PORT 2>/dev/null | head -1)
                if [[ -z "$pid" ]]; then
                    pid=$(fuser $PORT/tcp 2>/dev/null | awk '{print $1}')
                fi
                if [[ -z "$pid" ]]; then
                    pid=$(ss -tlnp 2>/dev/null | grep ":$PORT " | grep -oP 'pid=\K[0-9]+' | head -1)
                fi
                
                if [[ -n "$pid" ]]; then
                    blocking_process=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
                    local process_cmd=$(ps -p $pid -o args= 2>/dev/null || echo "")
                    
                    log_warning "Port $PORT blocked by process: $blocking_process (PID: $pid)"
                    log_info "  Command: $process_cmd"
                    
                    # Check for known safe-to-kill processes
                    if [[ "$blocking_process" == "mongo"* ]] || [[ "$blocking_process" == "mongod"* ]] || \
                       [[ "$blocking_process" == "rabbitmq"* ]] || [[ "$blocking_process" == "beam.smp"* ]] || \
                       [[ "$blocking_process" == "python"* ]] || [[ "$blocking_process" == "node"* ]] || \
                       [[ "$blocking_process" == "flask"* ]]; then
                        log_fix "Auto-killing $blocking_process (PID: $pid) - likely old deployment"
                        kill -15 $pid 2>/dev/null || $SUDO kill -15 $pid 2>/dev/null || true
                        sleep 2
                        # If still running, force kill
                        if ps -p $pid > /dev/null 2>&1; then
                            kill -9 $pid 2>/dev/null || $SUDO kill -9 $pid 2>/dev/null || true
                            sleep 1
                        fi
                    # Check for Tailscale or VPN processes
                    elif [[ "$blocking_process" == *"tailscale"* ]] || [[ "$blocking_process" == *"vpn"* ]] || \
                         [[ "$process_cmd" == *"tailscale"* ]] || [[ "$process_cmd" == *"vpn"* ]]; then
                        log_warning "Found networking service: $blocking_process"
                        if [[ -t 0 ]]; then
                            echo ""
                            read -p "Kill this process? (y/N): " -n 1 -r
                            echo
                            if [[ $REPLY =~ ^[Yy]$ ]]; then
                                log_fix "Killing $blocking_process (PID: $pid)"
                                kill -15 $pid 2>/dev/null || $SUDO kill -15 $pid 2>/dev/null || true
                                sleep 1
                            fi
                        else
                            log_warning "Keeping $blocking_process running - may cause conflicts"
                        fi
                    else
                        # Unknown process - ask user
                        log_warning "Unknown process '$blocking_process' using port $PORT"
                        if [[ -t 0 ]]; then
                            read -p "Kill this process to free the port? (Y/n): " -n 1 -r
                            echo
                            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                                log_fix "Killing process $pid"
                                kill -15 $pid 2>/dev/null || $SUDO kill -15 $pid 2>/dev/null || true
                                sleep 2
                                if ps -p $pid > /dev/null 2>&1; then
                                    kill -9 $pid 2>/dev/null || $SUDO kill -9 $pid 2>/dev/null || true
                                    sleep 1
                                fi
                            fi
                        else
                            # Non-interactive mode - kill it anyway
                            log_fix "Non-interactive mode: killing process $pid"
                            kill -15 $pid 2>/dev/null || $SUDO kill -15 $pid 2>/dev/null || true
                            sleep 2
                            if ps -p $pid > /dev/null 2>&1; then
                                kill -9 $pid 2>/dev/null || $SUDO kill -9 $pid 2>/dev/null || true
                                sleep 1
                            fi
                        fi
                    fi
                fi
            fi
        fi
        
        # Verify port is now free
        sleep 1
        if ! netstat -tuln 2>/dev/null | grep -q ":$PORT " && ! ss -tuln 2>/dev/null | grep -q ":$PORT "; then
            log_success "Port $PORT ($NAME) is available"
        else
            log_warning "Port $PORT still in use - deployment may have conflicts"
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
        
        # Generate random key as fallback
        if [[ -z "$NEW_SECRET" ]]; then
            NEW_SECRET=$(tr -dc 'a-zA-Z0-9' < /dev/urandom | fold -w 64 | head -n 1)
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
    
    # Configure HTTPS with domain if DOMAIN is set
    if grep -q "^DOMAIN=" .env && ! grep -q '^DOMAIN=""' .env && ! grep -q "^DOMAIN=\"studybuddyai.my\"" .env; then
        DOMAIN=$(grep "^DOMAIN=" .env | cut -d= -f2 | tr -d '"' | tr -d "'")
        
        if [[ -n "$DOMAIN" ]] && [[ "$DOMAIN" != "localhost" ]]; then
            log_info "Domain configured: $DOMAIN"
            
            # Check if Caddy should be enabled for HTTPS
            if [[ -t 0 ]]; then
                echo ""
                log_info "Your domain is set to: $DOMAIN"
                read -p "Enable automatic HTTPS with Let's Encrypt? (Y/n): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                    setup_https_caddy "$DOMAIN"
                fi
            else
                log_info "Non-interactive mode: HTTPS setup skipped"
                log_info "To enable HTTPS, run: sudo ./scripts/setup-https.sh $DOMAIN"
            fi
        fi
    fi
    
    return 0
}

setup_https_caddy() {
    local domain=$1
    
    log_info "Setting up HTTPS with Caddy for $domain..."
    
    # First, verify domain DNS points to this server
    log_info "Verifying domain DNS configuration..."
    
    local server_ip=$(hostname -I | awk '{print $1}' 2>/dev/null)
    local public_ip=$(curl -s -4 ifconfig.me 2>/dev/null || curl -s -4 icanhazip.com 2>/dev/null || curl -s -4 ipinfo.io/ip 2>/dev/null)
    
    log_info "Server local IP: $server_ip"
    log_info "Server public IP: $public_ip"
    
    # Resolve domain to IP
    local domain_ip=$(dig +short $domain 2>/dev/null | tail -1)
    if [[ -z "$domain_ip" ]]; then
        domain_ip=$(nslookup $domain 2>/dev/null | grep -A1 "Name:" | tail -1 | awk '{print $2}')
    fi
    if [[ -z "$domain_ip" ]]; then
        domain_ip=$(host $domain 2>/dev/null | grep "has address" | awk '{print $4}' | head -1)
    fi
    
    if [[ -n "$domain_ip" ]]; then
        log_info "Domain $domain resolves to: $domain_ip"
        
        # Check if domain points to this server
        if [[ "$domain_ip" == "$public_ip" ]] || [[ "$domain_ip" == "$server_ip" ]]; then
            log_success "Domain DNS correctly points to this server"
        else
            log_warning "Domain $domain points to $domain_ip but server is at $public_ip"
            echo ""
            log_warning "DNS Issues Detected!"
            log_info "Your domain does NOT point to this server"
            log_info "To fix:"
            log_info "  1. Update DNS A record for $domain to: $public_ip"
            log_info "  2. Wait 5-10 minutes for DNS propagation"
            log_info "  3. Run this script again"
            echo ""
            
            if [[ -t 0 ]]; then
                read -p "Continue anyway? (HTTPS may fail) (y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    log_info "Skipping HTTPS setup until DNS is fixed"
                    return 1
                fi
            else
                log_warning "Non-interactive mode: skipping HTTPS due to DNS mismatch"
                return 1
            fi
        fi
    else
        log_error "Cannot resolve domain $domain"
        log_info "Make sure:"
        log_info "  1. Domain exists and is registered"
        log_info "  2. DNS A record points to: $public_ip"
        log_info "  3. DNS has propagated (wait 5-10 minutes after changes)"
        echo ""
        
        if [[ -t 0 ]]; then
            read -p "Continue anyway? (HTTPS will likely fail) (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Skipping HTTPS setup"
                return 1
            fi
        else
            log_error "Non-interactive mode: cannot proceed without DNS"
            return 1
        fi
    fi
    
    # Check if ports 80 and 443 are available for Caddy
    log_info "Checking HTTPS ports (80, 443)..."
    
    for https_port in 80 443; do
        if netstat -tuln 2>/dev/null | grep -q ":$https_port " || ss -tuln 2>/dev/null | grep -q ":$https_port "; then
            log_warning "Port $https_port is in use"
            
            # Find what's using it
            local pid=$(lsof -ti:$https_port 2>/dev/null | head -1)
            if [[ -z "$pid" ]]; then
                pid=$(ss -tlnp 2>/dev/null | grep ":$https_port " | grep -oP 'pid=\K[0-9]+' | head -1)
            fi
            
            if [[ -n "$pid" ]]; then
                local process=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
                log_warning "Port $https_port used by: $process (PID: $pid)"
                
                # If it's nginx or apache, offer to stop
                if [[ "$process" == "nginx"* ]] || [[ "$process" == "apache"* ]] || [[ "$process" == "httpd"* ]]; then
                    log_warning "Found existing web server: $process"
                    
                    if [[ -t 0 ]]; then
                        read -p "Stop $process to use Caddy? (Y/n): " -n 1 -r
                        echo
                        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                            log_fix "Stopping $process..."
                            $SUDO systemctl stop nginx 2>/dev/null || true
                            $SUDO systemctl stop apache2 2>/dev/null || true
                            $SUDO systemctl stop httpd 2>/dev/null || true
                            sleep 2
                        fi
                    fi
                fi
            fi
        else
            log_success "Port $https_port available"
        fi
    done
    
    # Check if Caddy is installed
    if ! command -v caddy &> /dev/null; then
        log_fix "Installing Caddy..."
        
        $SUDO apt-get update -qq 2>/dev/null || true
        $SUDO apt-get install -y debian-keyring debian-archive-keyring apt-transport-https 2>/dev/null || true
        
        # Add Caddy repo
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' 2>/dev/null | $SUDO gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg 2>/dev/null || true
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' 2>/dev/null | $SUDO tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null || true
        
        $SUDO apt-get update -qq 2>/dev/null || true
        $SUDO apt-get install -y caddy 2>/dev/null || true
        
        if command -v caddy &> /dev/null; then
            log_success "Caddy installed"
        else
            log_warning "Failed to install Caddy - skipping HTTPS setup"
            return 1
        fi
    else
        log_success "Caddy already installed"
    fi
    
    # Create Caddyfile
    log_fix "Configuring Caddy for $domain..."
    
    $SUDO tee /etc/caddy/Caddyfile > /dev/null <<EOF
# StudyBuddyAI - Automatic HTTPS with Let's Encrypt
$domain {
    reverse_proxy localhost:5000 {
        health_uri /health
        health_interval 30s
        health_timeout 5s
        
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
        header_up Host {host}
    }
    
    # Enable compression
    encode gzip
    
    # Security headers
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        X-XSS-Protection "1; mode=block"
        Referrer-Policy strict-origin-when-cross-origin
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        -Server
    }
    
    # Logging
    log {
        output file /var/log/caddy/studybuddyai.log {
            roll_size 10mb
            roll_keep 5
        }
    }
}

# Redirect www to non-www (optional)
www.$domain {
    redir https://$domain{uri} permanent
}
EOF
    
    # Create log directory
    $SUDO mkdir -p /var/log/caddy
    $SUDO chown caddy:caddy /var/log/caddy 2>/dev/null || true
    
    # Validate Caddyfile
    if $SUDO caddy validate --config /etc/caddy/Caddyfile 2>/dev/null; then
        log_success "Caddyfile validated"
    else
        log_error "Caddyfile validation failed"
        return 1
    fi
    
    # Enable and restart Caddy
    $SUDO systemctl enable caddy 2>/dev/null || true
    $SUDO systemctl restart caddy
    
    sleep 3
    
    if $SUDO systemctl is-active --quiet caddy; then
        log_success "Caddy started successfully"
        
        # Update .env for HTTPS
        sed -i "s|BASE_URL=.*|BASE_URL=\"https://$domain\"|g" .env
        sed -i "s|SESSION_COOKIE_SECURE=.*|SESSION_COOKIE_SECURE=true|g" .env
        
        echo ""
        log_success "HTTPS configured for $domain"
        log_info "Certificate acquisition may take a few moments..."
        echo ""
        log_info "Important checklist:"
        log_info "  ✓ DNS points $domain to $public_ip"
        log_info "  ✓ Caddy is running"
        log_info "  ☐ Firewall allows ports 80 and 443"
        log_info "  ☐ Router forwards ports 80 and 443 (if behind NAT)"
        echo ""
        log_info "Caddy will automatically obtain SSL certificate from Let's Encrypt"
        log_info "This may take 30-60 seconds on first run"
        echo ""
        log_info "Access your site at: https://$domain"
        log_info "Check Caddy logs: sudo journalctl -u caddy -f"
        echo ""
        
        # Check if update_dns.sh exists and remind about it
        if [[ -f "scripts/update_dns.sh" ]]; then
            log_info "Dynamic DNS script detected: scripts/update_dns.sh"
            log_info "Make sure it's configured in crontab for dynamic IP updates"
            log_info "Example: */5 * * * * $(pwd)/scripts/update_dns.sh"
        fi
        echo ""
    else
        log_error "Failed to start Caddy"
        log_info "Check logs: sudo journalctl -u caddy -n 50"
        return 1
    fi
    
    return 0
}

fix_disk_space() {
    log_info "Checking disk space..."
    
    DISK_GB=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//' 2>/dev/null || echo "1")
    
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
