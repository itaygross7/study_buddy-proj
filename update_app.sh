#!/bin/bash
# =============================================================================
# StudyBuddy App Update Script (Production)
# =============================================================================
# This script allows updating the app in production without full redeployment
# It performs a git pull and restarts the necessary services
#
# Usage:
#   ./update_app.sh
#
# Requirements:
#   - Git repository is already cloned and configured
#   - Proper permissions to pull from the repository
#   - systemctl access (for systemd service) OR docker access
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}StudyBuddy Production Update Script${NC}"
echo -e "${BLUE}==============================================================================${NC}"
echo ""

# Check if we're in a git repository
if [ ! -d "$SCRIPT_DIR/.git" ]; then
    echo -e "${RED}Error: Not a git repository!${NC}"
    echo "This script must be run from the StudyBuddy repository root."
    exit 1
fi

echo -e "${YELLOW}Current directory: $SCRIPT_DIR${NC}"
echo ""

# Step 1: Check git status
echo -e "${BLUE}Step 1: Checking git status...${NC}"
cd "$SCRIPT_DIR"

if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}Warning: You have uncommitted changes!${NC}"
    git status --short
    echo ""
    read -p "Do you want to stash these changes and continue? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Stashing local changes..."
        git stash
    else
        echo -e "${RED}Update cancelled.${NC}"
        exit 1
    fi
fi

# Step 2: Get current branch and commit
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
CURRENT_COMMIT=$(git rev-parse --short HEAD)

echo -e "${GREEN}Current branch: $CURRENT_BRANCH${NC}"
echo -e "${GREEN}Current commit: $CURRENT_COMMIT${NC}"
echo ""

# Step 2: Fetch latest changes
echo -e "${BLUE}Step 2: Fetching latest changes from remote...${NC}"
git fetch origin

# Check if there are updates available
UPDATES_AVAILABLE=$(git rev-list HEAD...origin/$CURRENT_BRANCH --count)

if [ "$UPDATES_AVAILABLE" -eq 0 ]; then
    echo -e "${GREEN}✓ Already up to date!${NC}"
    echo "No updates available."
    exit 0
fi

echo -e "${YELLOW}$UPDATES_AVAILABLE commit(s) available for update${NC}"
echo ""

# Step 3: Show what will be updated
echo -e "${BLUE}Step 3: Changes to be pulled:${NC}"
git log HEAD..origin/$CURRENT_BRANCH --oneline --decorate
echo ""

read -p "Continue with update? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Update cancelled.${NC}"
    exit 1
fi

# Step 4: Pull changes
echo -e "${BLUE}Step 4: Pulling latest changes...${NC}"
git pull origin "$CURRENT_BRANCH"

NEW_COMMIT=$(git rev-parse --short HEAD)
echo -e "${GREEN}✓ Updated from $CURRENT_COMMIT to $NEW_COMMIT${NC}"
echo ""

# Step 5: Check if dependencies changed
echo -e "${BLUE}Step 5: Checking for dependency changes...${NC}"
DEPS_CHANGED=0

if git diff --name-only "$CURRENT_COMMIT" "$NEW_COMMIT" | grep -q "requirements.txt\|Pipfile\|package.json"; then
    echo -e "${YELLOW}Dependencies have changed!${NC}"
    DEPS_CHANGED=1
    
    if [ -f "requirements.txt" ]; then
        echo "Updating Python dependencies..."
        pip install -r requirements.txt --quiet || echo -e "${YELLOW}Warning: Failed to update Python deps${NC}"
    fi
    
    if [ -f "Pipfile" ]; then
        echo "Updating Python dependencies with Pipenv..."
        pipenv install --deploy || echo -e "${YELLOW}Warning: Failed to update Pipenv deps${NC}"
    fi
    
    if [ -f "package.json" ]; then
        echo "Updating Node dependencies..."
        npm install --silent || echo -e "${YELLOW}Warning: Failed to update Node deps${NC}"
    fi
else
    echo -e "${GREEN}No dependency changes detected${NC}"
fi
echo ""

# Step 6: Detect deployment type and restart services
echo -e "${BLUE}Step 6: Restarting services...${NC}"

# Check if running with Docker
if docker ps --format '{{.Names}}' | grep -q "studybuddy"; then
    echo "Detected Docker deployment"
    echo "Restarting Docker containers..."
    
    if [ -f "docker-compose.yml" ]; then
        docker-compose restart app worker
        echo -e "${GREEN}✓ Docker containers restarted${NC}"
    else
        echo -e "${YELLOW}Warning: docker-compose.yml not found, skipping restart${NC}"
    fi

# Check if running with systemd
elif systemctl is-active --quiet studybuddy.service 2>/dev/null; then
    echo "Detected systemd service"
    echo "Restarting StudyBuddy service..."
    sudo systemctl restart studybuddy.service
    
    # Also restart worker if it exists
    if systemctl is-active --quiet studybuddy-worker.service 2>/dev/null; then
        sudo systemctl restart studybuddy-worker.service
    fi
    
    echo -e "${GREEN}✓ Systemd services restarted${NC}"

else
    echo -e "${YELLOW}Warning: Could not detect deployment type${NC}"
    echo "Please manually restart your application:"
    echo "  - For Docker: docker-compose restart app worker"
    echo "  - For systemd: sudo systemctl restart studybuddy"
    echo "  - For manual: restart your Flask app and worker processes"
fi

echo ""

# Step 7: Verify app is running
echo -e "${BLUE}Step 7: Verifying application...${NC}"
sleep 5  # Wait for services to start

# Try to check health endpoint
if command -v curl &> /dev/null; then
    if curl -s -f http://localhost:5000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Application is running and healthy!${NC}"
    else
        echo -e "${YELLOW}Warning: Health check failed. Check logs:${NC}"
        echo "  docker-compose logs app"
        echo "  OR"
        echo "  sudo journalctl -u studybuddy -n 50"
    fi
else
    echo -e "${YELLOW}curl not available, skipping health check${NC}"
fi

echo ""
echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}Update completed successfully!${NC}"
echo -e "${GREEN}==============================================================================${NC}"
echo ""
echo "Updated from commit $CURRENT_COMMIT to $NEW_COMMIT"
echo ""
echo "What to do next:"
echo "  1. Check logs: docker-compose logs -f app (or journalctl -u studybuddy -f)"
echo "  2. Test the app in your browser"
echo "  3. If issues occur, rollback: git reset --hard $CURRENT_COMMIT && ./update_app.sh"
echo ""
