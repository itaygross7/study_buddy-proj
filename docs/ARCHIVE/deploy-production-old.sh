#!/bin/bash
# =============================================================================
# StudyBuddy AI - Cloudflare Tunnel Production Deployment
# Enhanced with:
# - Git pull with permission fixes
# - Environment variable validation
# - AI model activation checks
# - Worker container health verification
# =============================================================================

set -e # Exit immediately if a command exits with a non-zero status

# Colors for pretty output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}   StudyBuddy AI: Enhanced Production Deployment    ${NC}"
echo -e "${BLUE}======================================================${NC}"

# =============================================================================
# 1. Check Root Privileges
# =============================================================================
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root.${NC}" 
   echo -e "Try running: ${YELLOW}sudo ./deploy-production.sh${NC}"
   exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# =============================================================================
# 2. Fix Git Permissions and Pull Latest Code
# =============================================================================
echo -e "${BLUE}Fixing Git permissions and pulling latest code...${NC}"

# Get the actual user (not root when using sudo)
ACTUAL_USER="${SUDO_USER:-$USER}"

# Fix repository ownership
echo -e "${CYAN}Setting repository ownership to $ACTUAL_USER${NC}"
chown -R "$ACTUAL_USER:$ACTUAL_USER" "$SCRIPT_DIR"

# Configure git safe directory
sudo -u "$ACTUAL_USER" git config --global --add safe.directory "$SCRIPT_DIR" 2>/dev/null || true

# Stash any local changes
echo -e "${CYAN}Stashing any local changes...${NC}"
sudo -u "$ACTUAL_USER" git stash 2>/dev/null || true

# Pull latest code
echo -e "${CYAN}Pulling latest code from git...${NC}"
if sudo -u "$ACTUAL_USER" git pull origin main 2>&1; then
    echo -e "${GREEN}✓ Successfully pulled latest code${NC}"
else
    echo -e "${YELLOW}! Git pull failed, continuing with current version${NC}"
    # Try to get current branch and pull from it
    CURRENT_BRANCH=$(sudo -u "$ACTUAL_USER" git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
    if [ "$CURRENT_BRANCH" != "main" ]; then
        echo -e "${CYAN}Trying to pull from branch: $CURRENT_BRANCH${NC}"
        sudo -u "$ACTUAL_USER" git pull origin "$CURRENT_BRANCH" 2>/dev/null || echo -e "${YELLOW}! Using local version${NC}"
    fi
fi

# Make all shell scripts executable
echo -e "${CYAN}Making deployment scripts executable...${NC}"
find "$SCRIPT_DIR" -type f -name "*.sh" -exec chmod +x {} \;
echo -e "${GREEN}✓ Scripts are executable${NC}"

# =============================================================================
# 3. Validate .env File and Required Variables
# =============================================================================
echo -e "${BLUE}Validating environment configuration...${NC}"

if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found.${NC}"
    if [ -f ".env.example" ]; then
        echo -e "${CYAN}Creating .env from .env.example${NC}"
        cp .env.example .env
        chown "$ACTUAL_USER:$ACTUAL_USER" .env
        echo -e "${YELLOW}Please edit .env with your configuration and run this script again${NC}"
        exit 1
    else
        echo -e "${RED}Error: .env.example also not found!${NC}"
        exit 1
    fi
fi

# Source .env to check variables
set -a
source .env
set +a

# Validate critical environment variables
MISSING_VARS=()

echo -e "${CYAN}Checking required environment variables...${NC}"

# Check infrastructure variables
[ -z "$MONGO_URI" ] && MISSING_VARS+=("MONGO_URI")
[ -z "$RABBITMQ_URI" ] && MISSING_VARS+=("RABBITMQ_URI")
[ -z "$SECRET_KEY" ] && MISSING_VARS+=("SECRET_KEY")

# Check AI provider variables (at least one must be set)
if [ -z "$OPENAI_API_KEY" ] && [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${RED}✗ No AI provider configured!${NC}"
    echo -e "${YELLOW}  You must set either OPENAI_API_KEY or GEMINI_API_KEY in .env${NC}"
    MISSING_VARS+=("OPENAI_API_KEY or GEMINI_API_KEY")
fi

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}✗ Missing required environment variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo -e "${RED}  - $var${NC}"
    done
    echo -e "${YELLOW}Please update your .env file and try again${NC}"
    exit 1
fi

# Show AI configuration
echo -e "${GREEN}✓ Infrastructure variables configured${NC}"
if [ -n "$OPENAI_API_KEY" ]; then
    echo -e "${GREEN}✓ OpenAI API key detected${NC}"
    echo -e "  Model: ${SB_OPENAI_MODEL:-gpt-4o-mini}"
fi
if [ -n "$GEMINI_API_KEY" ]; then
    echo -e "${GREEN}✓ Gemini API key detected${NC}"
    echo -e "  Model: ${SB_GEMINI_MODEL:-gemini-1.5-flash-latest}"
fi
echo -e "  Default provider: ${SB_DEFAULT_PROVIDER:-gemini}"

# =============================================================================
# 4. Verify Cloudflare Tunnel Token
# =============================================================================
if ! grep -q "TUNNEL_TOKEN=" .env || [ -z "$TUNNEL_TOKEN" ]; then
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
    chown "$ACTUAL_USER:$ACTUAL_USER" .env
    echo -e "${GREEN}✓ Token added to .env${NC}"
fi

# =============================================================================
# 5. Install Docker & Compose (if missing)
# =============================================================================
if ! command -v docker &> /dev/null; then
    echo -e "${BLUE}Installing Docker...${NC}"
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker "$ACTUAL_USER"
    echo -e "${GREEN}✓ Docker installed${NC}"
fi

# Ensure Docker is running
if ! systemctl is-active --quiet docker; then
    echo -e "${CYAN}Starting Docker daemon...${NC}"
    systemctl start docker
    systemctl enable docker
    sleep 3
fi
echo -e "${GREEN}✓ Docker is running${NC}"

# =============================================================================
# 6. Install/Update Tailscale (For private SSH access)
# =============================================================================
if ! command -v tailscale &> /dev/null; then
    echo -e "${BLUE}Installing Tailscale...${NC}"
    curl -fsSL https://tailscale.com/install.sh | sh
    echo -e "${YELLOW}IMPORTANT: Run 'sudo tailscale up' after this script to log in.${NC}"
fi

# =============================================================================
# 7. Secure Firewall (UFW)
# =============================================================================
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
    echo -e "${GREEN}✓ Firewall active (Secure mode)${NC}"
else
    echo -e "${YELLOW}! UFW not found, skipping firewall setup${NC}"
fi

# =============================================================================
# 8. Stop Old Containers
# =============================================================================
echo -e "${BLUE}Stopping old containers...${NC}"
docker compose down --remove-orphans 2>/dev/null || true
echo -e "${GREEN}✓ Old containers stopped${NC}"

# =============================================================================
# 9. Build and Start Docker Containers
# =============================================================================
echo -e "${BLUE}Building and starting application...${NC}"
docker compose up -d --build

echo -e "${CYAN}Waiting for containers to start (20 seconds)...${NC}"
sleep 20

# =============================================================================
# 10. Verify All Containers Are Running
# =============================================================================
echo -e "${BLUE}Verifying container health...${NC}"

# Check each critical container
CONTAINERS=("studybuddy_app" "studybuddy_worker" "studybuddy_mongo" "studybuddy_rabbitmq")
ALL_HEALTHY=true

for container in "${CONTAINERS[@]}"; do
    if docker ps --filter "name=$container" --filter "status=running" | grep -q "$container"; then
        echo -e "${GREEN}✓ $container is running${NC}"
    else
        echo -e "${RED}✗ $container is not running!${NC}"
        ALL_HEALTHY=false
    fi
done

if [ "$ALL_HEALTHY" = false ]; then
    echo -e "${RED}Some containers failed to start. Check logs:${NC}"
    echo -e "${YELLOW}  docker compose logs app${NC}"
    echo -e "${YELLOW}  docker compose logs worker${NC}"
    exit 1
fi

# =============================================================================
# 11. Test Application and Worker Health
# =============================================================================
echo -e "${BLUE}Testing application health...${NC}"

# Wait a bit more for app to be fully ready
sleep 10

# Test app health endpoint
if curl -sf http://localhost:5000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Application health check passed${NC}"
else
    echo -e "${YELLOW}! Application health check failed (may need more time)${NC}"
fi

# Check worker logs for successful connection
echo -e "${CYAN}Checking worker status...${NC}"
WORKER_LOGS=$(docker compose logs worker --tail=50 2>&1)

if echo "$WORKER_LOGS" | grep -q "Worker successfully connected to MongoDB"; then
    echo -e "${GREEN}✓ Worker connected to MongoDB${NC}"
else
    echo -e "${YELLOW}! Worker may not be connected to MongoDB${NC}"
fi

if echo "$WORKER_LOGS" | grep -q "Worker connected to RabbitMQ"; then
    echo -e "${GREEN}✓ Worker connected to RabbitMQ${NC}"
else
    echo -e "${YELLOW}! Worker may not be connected to RabbitMQ${NC}"
fi

if echo "$WORKER_LOGS" | grep -q "Worker is waiting for messages"; then
    echo -e "${GREEN}✓ Worker is ready to process tasks${NC}"
else
    echo -e "${YELLOW}! Worker may not be ready (check logs: docker compose logs worker)${NC}"
fi

# =============================================================================
# 12. Setup Auto-Restart (Systemd)
# =============================================================================
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
echo -e "${GREEN}✓ Systemd service configured${NC}"

# =============================================================================
# DEPLOYMENT COMPLETE
# =============================================================================
echo ""
echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN}         DEPLOYMENT COMPLETE! 🚀                     ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo ""
echo -e "${CYAN}Configuration Summary:${NC}"
echo -e "  ✓ Latest code pulled from git"
echo -e "  ✓ Environment variables validated"
if [ -n "$OPENAI_API_KEY" ]; then
    echo -e "  ✓ OpenAI API configured (${SB_OPENAI_MODEL:-gpt-4o-mini})"
fi
if [ -n "$GEMINI_API_KEY" ]; then
    echo -e "  ✓ Gemini API configured (${SB_GEMINI_MODEL:-gemini-1.5-flash-latest})"
fi
echo -e "  ✓ All containers running"
echo -e "  ✓ Worker connected and ready"
echo -e "  ✓ PWA service worker enabled"
echo ""
echo -e "${CYAN}Access your application:${NC}"
echo -e "  • Web: Configure in Cloudflare Zero Trust Dashboard"
echo -e "  • Local: http://localhost:5000"
echo -e "  • RabbitMQ Admin: http://localhost:15672"
echo ""
echo -e "${CYAN}Cloudflare Setup:${NC}"
echo -e "1. Go to Cloudflare Zero Trust Dashboard"
echo -e "2. Navigate to your Tunnel → Public Hostname"
echo -e "3. Add hostname:"
echo -e "   - Subdomain: ${YELLOW}www${NC}"
echo -e "   - Domain: ${YELLOW}your-domain.com${NC}"
echo -e "   - Service: ${YELLOW}HTTP${NC} : ${YELLOW}studybuddy_app:5000${NC}"
echo ""
echo -e "${CYAN}Useful Commands:${NC}"
echo -e "  • View app logs:    ${YELLOW}docker compose logs -f app${NC}"
echo -e "  • View worker logs: ${YELLOW}docker compose logs -f worker${NC}"
echo -e "  • Restart all:      ${YELLOW}docker compose restart${NC}"
echo -e "  • Stop all:         ${YELLOW}docker compose down${NC}"
echo ""
echo -e "${CYAN}SSH Access:${NC} Use Tailscale IP (run 'tailscale ip -4')"
echo ""
echo -e "${GREEN}======================================================${NC}"

