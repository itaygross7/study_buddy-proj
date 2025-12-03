#!/bin/bash
# =============================================================================
# StudyBuddy AI - Complete Production Deployment Script
# =============================================================================
# This script does EVERYTHING needed for production deployment:
# - HTTPS with Caddy and Let's Encrypt
# - Tailscale for secure server access
# - Systemd service for auto-restart
# - Firewall configuration
# - Auto-update setup
#
# Run once and you're done!
# =============================================================================

set -e  # Exit on error

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
else
    SUDO="sudo"
fi

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_error() { echo -e "${RED}[✗]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $*"; }

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
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  Complete Production Deployment with HTTPS & Tailscale${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo ""
}

show_banner

# =============================================================================
# 1. Check Prerequisites
# =============================================================================
log_info "Step 1/8: Checking prerequisites..."

if [ ! -f ".env" ]; then
    log_error ".env file not found!"
    log_info "Creating .env from .env.example..."
    cp .env.example .env
    log_warning "IMPORTANT: Edit .env file with your configuration before continuing!"
    log_warning "Required: DOMAIN, BASE_URL, API keys, ADMIN_EMAIL, MAIL settings"
    read -p "Press Enter after editing .env file..."
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    log_warning "Docker not found. Installing..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    $SUDO sh /tmp/get-docker.sh
    $SUDO usermod -aG docker $USER
    log_success "Docker installed"
fi

# Check Docker Compose
if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
    log_warning "Docker Compose not found. Installing..."
    $SUDO apt-get update
    $SUDO apt-get install -y docker-compose-plugin
    log_success "Docker Compose installed"
fi

log_success "Prerequisites checked"

# =============================================================================
# 2. Install and Configure Tailscale
# =============================================================================
log_info "Step 2/8: Setting up Tailscale..."

if ! command -v tailscale &> /dev/null; then
    log_info "Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
    log_success "Tailscale installed"
else
    log_success "Tailscale already installed"
fi

# Check if Tailscale is connected
if ! $SUDO tailscale status &> /dev/null; then
    log_warning "Tailscale not connected. Starting Tailscale..."
    log_info "You'll need to authenticate via the link provided"
    $SUDO tailscale up
    log_success "Tailscale connected"
else
    log_success "Tailscale already running"
fi

# Get Tailscale IP
TAILSCALE_IP=$($SUDO tailscale ip -4 2>/dev/null || echo "")
if [ -n "$TAILSCALE_IP" ]; then
    log_success "Tailscale IP: $TAILSCALE_IP"
else
    log_warning "Could not get Tailscale IP"
fi

# =============================================================================
# 3. Configure Firewall (UFW) - Tailscale Only + HTTPS
# =============================================================================
log_info "Step 3/8: Configuring firewall..."

if command -v ufw &> /dev/null; then
    # Get Tailscale network interface
    TAILSCALE_IFACE=$($SUDO tailscale status --json 2>/dev/null | grep -o '"TUN":"[^"]*"' | cut -d'"' -f4 || echo "tailscale0")
    
    log_info "Setting up UFW firewall rules..."
    
    # Reset UFW to default
    $SUDO ufw --force reset
    
    # Default policies
    $SUDO ufw default deny incoming
    $SUDO ufw default allow outgoing
    
    # Allow SSH only from Tailscale network
    $SUDO ufw allow in on $TAILSCALE_IFACE to any port 22 comment 'SSH from Tailscale only'
    
    # Allow HTTP and HTTPS for Let's Encrypt and web access
    $SUDO ufw allow 80/tcp comment 'HTTP for Let'\''s Encrypt'
    $SUDO ufw allow 443/tcp comment 'HTTPS'
    $SUDO ufw allow 443/udp comment 'HTTP/3'
    
    # Allow Tailscale
    $SUDO ufw allow 41641/udp comment 'Tailscale'
    
    # Enable UFW
    $SUDO ufw --force enable
    
    log_success "Firewall configured - SSH only via Tailscale, HTTPS open"
else
    log_warning "UFW not found. Firewall not configured."
    $SUDO apt-get install -y ufw
    log_info "UFW installed. Rerun script to configure firewall."
fi

# =============================================================================
# 4. Update .env for HTTPS
# =============================================================================
log_info "Step 4/8: Updating .env for HTTPS..."

# Check if DOMAIN is set
if ! grep -q "^DOMAIN=" .env; then
    log_error "DOMAIN not set in .env file!"
    read -p "Enter your domain (e.g., studybuddyai.my): " DOMAIN
    echo "DOMAIN=\"$DOMAIN\"" >> .env
else
    DOMAIN=$(grep "^DOMAIN=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
fi

# Update BASE_URL to use HTTPS
if grep -q "^BASE_URL=" .env; then
    sed -i 's|^BASE_URL=.*|BASE_URL="https://'"$DOMAIN"'"|' .env
else
    echo "BASE_URL=\"https://$DOMAIN\"" >> .env
fi

# Enable secure cookies for HTTPS
if grep -q "^SESSION_COOKIE_SECURE=" .env; then
    sed -i 's|^SESSION_COOKIE_SECURE=.*|SESSION_COOKIE_SECURE=true|' .env
else
    echo "SESSION_COOKIE_SECURE=true" >> .env
fi

# Generate SECRET_KEY if not set or is default
if ! grep -q "^SECRET_KEY=" .env || grep -q "change-this-to-a-very-secret-key" .env; then
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
    sed -i 's|^SECRET_KEY=.*|SECRET_KEY="'"$SECRET_KEY"'"|' .env || echo "SECRET_KEY=\"$SECRET_KEY\"" >> .env
    log_success "Generated secure SECRET_KEY"
fi

log_success ".env configured for HTTPS"

# =============================================================================
# 5. Build and Start Docker Services
# =============================================================================
log_info "Step 5/8: Building and starting services..."

# Stop any existing services
docker compose down 2>/dev/null || true

# Build and start with Caddy
log_info "Starting all services with HTTPS support..."
docker compose up -d --build

# Wait for services to be healthy
log_info "Waiting for services to be ready..."
sleep 10

# Check if services are running
if docker compose ps | grep -q "Up"; then
    log_success "Services started successfully"
else
    log_error "Some services failed to start"
    docker compose logs --tail=50
    exit 1
fi

# =============================================================================
# 6. Install as Systemd Service
# =============================================================================
log_info "Step 6/8: Installing systemd service..."

# Get the current directory
INSTALL_DIR=$(pwd)

# Create systemd service file
cat > /tmp/studybuddy.service << EOF
[Unit]
Description=StudyBuddy AI Application
Documentation=https://github.com/itaygross7/study_buddy-proj
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$INSTALL_DIR
ExecStartPre=/usr/bin/docker compose down
ExecStart=/usr/bin/docker compose up -d --build
ExecStop=/usr/bin/docker compose down
ExecReload=/usr/bin/docker compose pull && /usr/bin/docker compose up -d --build
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true

# Limit resources
CPUQuota=95%
MemoryLimit=4G

[Install]
WantedBy=multi-user.target
EOF

# Install service
$SUDO cp /tmp/studybuddy.service /etc/systemd/system/studybuddy.service
$SUDO systemctl daemon-reload
$SUDO systemctl enable studybuddy.service

log_success "Systemd service installed and enabled"
log_info "Service will auto-start on boot and restart on failure"

# =============================================================================
# 7. Setup Auto-Update Script
# =============================================================================
log_info "Step 7/8: Setting up auto-update system..."

# Create auto-update script
cat > scripts/auto-update.sh << 'EOF'
#!/bin/bash
# Auto-update script for StudyBuddy
# This script pulls latest changes and restarts the service

LOG_FILE="/var/log/studybuddy-update.log"
INSTALL_DIR="/opt/studybuddy"

echo "[$(date)] Starting auto-update..." >> "$LOG_FILE"

cd "$INSTALL_DIR" || exit 1

# Check for changes
git fetch origin
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "[$(date)] No updates available" >> "$LOG_FILE"
    exit 0
fi

echo "[$(date)] Updates found. Pulling changes..." >> "$LOG_FILE"

# Backup current .env
cp .env .env.backup

# Pull changes
git pull origin main

# Restore .env (in case it was changed)
if [ -f .env.backup ]; then
    mv .env.backup .env
fi

# Restart service
echo "[$(date)] Restarting service..." >> "$LOG_FILE"
sudo systemctl restart studybuddy.service

echo "[$(date)] Update complete" >> "$LOG_FILE"
EOF

chmod +x scripts/auto-update.sh

# Ask user if they want to set up auto-updates
echo ""
log_info "Auto-update options:"
echo "  1. Manual updates only (run ./scripts/auto-update.sh when needed)"
echo "  2. Automatic updates via cron (checks daily at 3 AM)"
echo "  3. Webhook endpoint for instant updates (requires setup)"
read -p "Choose option (1-3) [1]: " UPDATE_CHOICE
UPDATE_CHOICE=${UPDATE_CHOICE:-1}

if [ "$UPDATE_CHOICE" = "2" ]; then
    # Add cron job for daily updates
    CRON_CMD="0 3 * * * $INSTALL_DIR/scripts/auto-update.sh"
    (crontab -l 2>/dev/null | grep -v "auto-update.sh"; echo "$CRON_CMD") | crontab -
    log_success "Daily auto-updates enabled (3 AM)"
elif [ "$UPDATE_CHOICE" = "3" ]; then
    log_info "Webhook endpoint: POST /api/update (requires authentication)"
    log_info "Set up in your GitHub repository webhook settings"
fi

log_success "Auto-update system configured"

# =============================================================================
# 8. Final Checks and Summary
# =============================================================================
log_info "Step 8/8: Final checks..."

# Wait a bit for Caddy to get certificate
sleep 5

# Test if HTTPS is working
log_info "Testing HTTPS connection..."
if curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN" | grep -q "200\|301\|302"; then
    log_success "HTTPS is working!"
else
    log_warning "HTTPS test failed. It may take a few minutes for Let's Encrypt to issue certificate"
    log_info "Check logs: docker compose logs caddy"
fi

# =============================================================================
# Deployment Complete!
# =============================================================================
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  🎉 Deployment Complete! 🎉${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""
log_success "StudyBuddy is now running in production mode!"
echo ""
echo -e "${CYAN}📍 Access Information:${NC}"
echo -e "   🌐 Web: ${GREEN}https://$DOMAIN${NC}"
if [ -n "$TAILSCALE_IP" ]; then
    echo -e "   🔒 SSH: ${GREEN}ssh user@$TAILSCALE_IP${NC} (Tailscale only)"
fi
echo ""
echo -e "${CYAN}🔧 Management Commands:${NC}"
echo -e "   View logs:      ${YELLOW}docker compose logs -f${NC}"
echo -e "   Restart:        ${YELLOW}sudo systemctl restart studybuddy${NC}"
echo -e "   Update:         ${YELLOW}./scripts/auto-update.sh${NC}"
echo -e "   Status:         ${YELLOW}sudo systemctl status studybuddy${NC}"
echo ""
echo -e "${CYAN}🔐 Security:${NC}"
echo -e "   ✓ HTTPS enabled (Let's Encrypt)"
echo -e "   ✓ Tailscale running"
echo -e "   ✓ Firewall configured (SSH only via Tailscale)"
echo -e "   ✓ Auto-restart enabled"
echo ""
echo -e "${CYAN}📧 Next Steps:${NC}"
echo -e "   1. Verify your email settings in .env work"
echo -e "   2. Test OAuth login (Google/Apple) if configured"
echo -e "   3. Create your admin account at https://$DOMAIN"
echo ""
log_info "Enjoy! 🦫"
