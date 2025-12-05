#!/bin/bash
# =============================================================================
# StudyBuddy AI - Cloudflare Tunnel Production Deployment
# =============================================================================

set -e # Exit immediately if a command exits with a non-zero status

# Colors for pretty output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}   StudyBuddy AI: Cloudflare Tunnel Deployment    ${NC}"
echo -e "${BLUE}======================================================${NC}"

# 1. Check Root Privileges
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root.${NC}" 
   echo -e "Try running: ${YELLOW}sudo ./deploy.sh${NC}"
   exit 1
fi

# 2. Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found.${NC}"
    echo "Please create one from .env.example"
    exit 1
fi

# 3. Verify Cloudflare Token
if ! grep -q "TUNNEL_TOKEN=" .env; then
    echo -e "${YELLOW}Missing TUNNEL_TOKEN in .env file.${NC}"
    echo -e "Please paste your Cloudflare Tunnel token:"
    read -p "Token > " TOKEN_INPUT
    
    if [ -z "$TOKEN_INPUT" ]; then
        echo -e "${RED}Token cannot be empty.${NC}"
        exit 1
    fi
    
    echo "" >> .env
    echo "# Cloudflare Tunnel Token" >> .env
    echo "TUNNEL_TOKEN=$TOKEN_INPUT" >> .env
    echo -e "${GREEN}Token added to .env${NC}"
fi

# 4. Install Docker & Compose (if missing)
if ! command -v docker &> /dev/null; then
    echo -e "${BLUE}Installing Docker...${NC}"
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker $SUDO_USER
fi

# 5. Install/Update Tailscale (For private SSH access)
if ! command -v tailscale &> /dev/null; then
    echo -e "${BLUE}Installing Tailscale...${NC}"
    curl -fsSL https://tailscale.com/install.sh | sh
    echo -e "${YELLOW}IMPORTANT: Run 'sudo tailscale up' after this script to log in.${NC}"
fi

# 6. Secure Firewall (UFW)
if command -v ufw &> /dev/null; then
    echo -e "${BLUE}Configuring Firewall (Zero Trust Mode)...${NC}"
    ufw --force reset > /dev/null
    
    # Block all incoming by default
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH (Ideally restrict this to Tailscale interface 'tailscale0')
    ufw allow ssh
    
    # Note: We do NOT need to open port 80 or 443! Cloudflare Tunnel handles this.
    
    ufw --force enable
    echo -e "${GREEN}Firewall active. Incoming ports closed (Secure).${NC}"
else
    echo -e "${YELLOW}UFW not found, skipping firewall setup.${NC}"
fi

# 7. Start Docker Containers
echo -e "${BLUE}Starting Application...${NC}"
# Stop old containers if running
docker compose down --remove-orphans 2>/dev/null || true
# Start new setup
docker compose up -d --build

# 8. Setup Auto-Restart (Systemd)
WORKING_DIR=$(pwd)
SERVICE_FILE="/etc/systemd/system/studybuddy.service"

echo -e "${BLUE}Creating Systemd Service...${NC}"
cat > $SERVICE_FILE << EOF
[Unit]
Description=StudyBuddy AI (Cloudflare Tunnel)
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$WORKING_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable studybuddy.service

echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN}   DEPLOYMENT COMPLETE! 🚀   ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "1. Go to Cloudflare Zero Trust Dashboard."
echo -e "2. In your Tunnel settings, go to 'Public Hostname'."
echo -e "3. Add a hostname:"
echo -e "   - Subdomain: ${YELLOW}www${NC} (or your preference)"
echo -e "   - Domain:    ${YELLOW}studybuddyai.my${NC}"
echo -e "   - Service:   ${YELLOW}HTTP${NC} : ${YELLOW}studybuddy_app:5000${NC}"
echo -e ""
echo -e "SSH Access: Use Tailscale IP (run 'tailscale ip -4')"
