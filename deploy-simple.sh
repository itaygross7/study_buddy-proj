#!/bin/bash
# =============================================================================
# StudyBuddyAI Simple Deployment Script
# =============================================================================
# Simplified version - does everything in one go with minimal checks
# Tested on: Ubuntu 22.04 LTS
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
echo -e "${NC}${BLUE}Simple One-Click Deployment${NC}\n"

# Quick checks
echo -e "${BLUE}[1/6]${NC} Checking Docker..."
if ! command -v docker &> /dev/null || ! docker info &> /dev/null; then
    echo -e "${RED}✗ Docker not found or not running${NC}"
    echo "Install: curl -fsSL https://get.docker.com | sudo sh"
    echo "Start: sudo systemctl start docker"
    exit 1
fi
echo -e "${GREEN}✓${NC} Docker OK"

echo -e "${BLUE}[2/6]${NC} Checking Docker Compose..."
if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE="docker-compose"
else
    echo -e "${RED}✗ Docker Compose not found${NC}"
    echo "Install: sudo apt install docker-compose-plugin"
    exit 1
fi
echo -e "${GREEN}✓${NC} Docker Compose OK"

echo -e "${BLUE}[3/6]${NC} Checking configuration..."
if [[ ! -f .env ]]; then
    echo -e "${YELLOW}!${NC} Creating .env from template..."
    cp .env.example .env
    echo -e "${YELLOW}!${NC} Please edit .env and set:"
    echo "  - SECRET_KEY (generate: python3 -c 'import secrets; print(secrets.token_hex(32))')"
    echo "  - ADMIN_EMAIL"
    echo "  - GEMINI_API_KEY or OPENAI_API_KEY"
    echo ""
    read -p "Press Enter after editing .env (or Ctrl+C to cancel)..."
fi
echo -e "${GREEN}✓${NC} Configuration OK"

echo -e "${BLUE}[4/6]${NC} Checking disk space..."
DISK_GB=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
if [[ $DISK_GB -lt 2 ]]; then
    echo -e "${RED}✗ Low disk space: ${DISK_GB}GB available${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Disk space OK (${DISK_GB}GB)"

echo -e "${BLUE}[5/6]${NC} Building and starting services..."
$COMPOSE down 2>/dev/null || true
$COMPOSE up -d --build

echo -e "${BLUE}[6/6]${NC} Waiting for services to start..."
sleep 10

# Check if running
RUNNING=$($COMPOSE ps --format json 2>/dev/null | grep -c '"State":"running"' || echo 0)
if [[ $RUNNING -ge 3 ]]; then
    echo -e "${GREEN}✓${NC} Services running ($RUNNING containers)"
else
    echo -e "${YELLOW}!${NC} Only $RUNNING containers running (expected 4)"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${GREEN}→${NC} Application: http://localhost:5000"
if [[ -n "$(hostname -I | awk '{print $1}')" ]]; then
    echo -e "  ${GREEN}→${NC} External:    http://$(hostname -I | awk '{print $1}'):5000"
fi
echo ""
echo -e "Useful commands:"
echo -e "  ${BLUE}View logs:${NC}    $COMPOSE logs -f app"
echo -e "  ${BLUE}Stop:${NC}         $COMPOSE down"
echo -e "  ${BLUE}Restart:${NC}      $COMPOSE restart"
echo ""
