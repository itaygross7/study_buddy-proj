#!/bin/bash
# =============================================================================
# StudyBuddy - Start for Local Network Access
# =============================================================================
# This script starts StudyBuddy optimized for local network access without
# Caddy/HTTPS. Use this when you want to access the app from other devices
# on the same network (phones, tablets, other computers).
#
# For production deployment with HTTPS, use: ./deploy-production.sh
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Detect sudo
if [[ $EUID -eq 0 ]]; then
    SUDO=""
else
    SUDO="sudo"
fi

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
echo -e "${NC}${CYAN}Local Network Access Mode${NC}\n"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found${NC}"
    echo "Install: curl -fsSL https://get.docker.com | sudo sh"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}✗ Docker daemon not running${NC}"
    echo "Start: sudo systemctl start docker"
    exit 1
fi

# Check Docker Compose
if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE="docker-compose"
else
    echo -e "${RED}✗ Docker Compose not found${NC}"
    echo "Install: sudo apt install docker-compose-plugin"
    exit 1
fi

echo -e "${BLUE}[1/5]${NC} Checking configuration..."

# Check .env file
if [[ ! -f .env ]]; then
    echo -e "${YELLOW}!${NC} Creating .env from template..."
    cp .env.example .env
    
    # Generate SECRET_KEY
    if command -v python3 &> /dev/null; then
        SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))' 2>/dev/null || echo "")
        if [[ -n "$SECRET" ]]; then
            sed -i "s/change-this-to-a-very-secret-key-in-production/$SECRET/" .env
            echo -e "${GREEN}✓${NC} Generated SECRET_KEY"
        fi
    fi
    
    echo -e "${YELLOW}!${NC} Please configure at least one AI provider in .env:"
    echo "  - GEMINI_API_KEY (recommended, has free tier)"
    echo "  - OR OPENAI_API_KEY"
    echo ""
    read -p "Press Enter after editing .env (or Ctrl+C to cancel)..."
fi

echo -e "${GREEN}✓${NC} Configuration ready"

echo -e "${BLUE}[2/5]${NC} Stopping any existing containers..."
$COMPOSE down 2>/dev/null || true

echo -e "${BLUE}[3/5]${NC} Starting services (without Caddy)..."
echo -e "${CYAN}Using local network configuration...${NC}"
$COMPOSE -f docker-compose.yml -f docker-compose.local.yml up -d --build

echo -e "${BLUE}[4/5]${NC} Waiting for services to start..."
sleep 15

# Wait for app to be healthy
echo -n "Waiting for app to be ready"
for i in {1..20}; do
    if curl -sf http://localhost:5000/health &> /dev/null; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 2
done
echo ""

echo -e "${BLUE}[5/5]${NC} Checking firewall..."

# Try to open firewall port
if command -v ufw &> /dev/null && $SUDO ufw status | grep -q "Status: active"; then
    echo -e "${CYAN}Detected UFW firewall...${NC}"
    if ! $SUDO ufw status | grep -q "5000/tcp"; then
        echo -e "${YELLOW}!${NC} Opening port 5000..."
        $SUDO ufw allow 5000/tcp comment 'StudyBuddy Local Network'
        echo -e "${GREEN}✓${NC} Port 5000 opened"
    else
        echo -e "${GREEN}✓${NC} Port 5000 already open"
    fi
elif command -v firewall-cmd &> /dev/null && $SUDO firewall-cmd --state &> /dev/null; then
    echo -e "${CYAN}Detected firewalld...${NC}"
    if ! $SUDO firewall-cmd --list-ports | grep -q "5000/tcp"; then
        echo -e "${YELLOW}!${NC} Opening port 5000..."
        $SUDO firewall-cmd --permanent --add-port=5000/tcp
        $SUDO firewall-cmd --reload
        echo -e "${GREEN}✓${NC} Port 5000 opened"
    else
        echo -e "${GREEN}✓${NC} Port 5000 already open"
    fi
else
    echo -e "${YELLOW}!${NC} No firewall detected or firewall inactive"
    echo -e "    If you can't access from other devices, check your firewall manually"
fi

# Get IP address
IP=$(hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  StudyBuddy Started Successfully! 🦫${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}Access your app:${NC}"
echo -e "  ${GREEN}→${NC} From this computer:    ${BLUE}http://localhost:5000${NC}"
if [[ -n "$IP" ]]; then
    echo -e "  ${GREEN}→${NC} From other devices:    ${BLUE}http://$IP:5000${NC}"
fi
echo ""
echo -e "${CYAN}Services running:${NC}"
$COMPOSE ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || $COMPOSE ps
echo ""
echo -e "${CYAN}Useful commands:${NC}"
echo -e "  ${BLUE}View logs:${NC}        $COMPOSE logs -f app"
echo -e "  ${BLUE}Stop services:${NC}    $COMPOSE down"
echo -e "  ${BLUE}Restart:${NC}          $COMPOSE restart app"
echo -e "  ${BLUE}Check health:${NC}     curl http://localhost:5000/health"
echo ""
echo -e "${YELLOW}⚠️  Security Note:${NC}"
echo -e "    This setup uses HTTP (not HTTPS) and is suitable for local"
echo -e "    networks only. For production use: ${BLUE}./deploy-production.sh${NC}"
echo ""
echo -e "${CYAN}Need help?${NC} See ${BLUE}docs/LOCAL_NETWORK_ACCESS.md${NC}"
echo ""
