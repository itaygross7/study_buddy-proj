#!/bin/bash
# =============================================================================
# Setup Dynamic DNS Updater for StudyBuddyAI
# =============================================================================
# This script helps you configure the update_dns.sh script for your domain
# and sets up the cron job to run it automatically
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_error() { echo -e "${RED}[✗]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $*"; }

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Dynamic DNS Setup for StudyBuddyAI${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Check if update_dns.sh exists
if [[ ! -f "scripts/update_dns.sh" ]]; then
    log_error "scripts/update_dns.sh not found"
    exit 1
fi

log_info "This script will help you set up automatic DNS updates for dynamic IP"
echo ""

# Get domain from .env if exists
DOMAIN=""
if [[ -f .env ]]; then
    DOMAIN=$(grep "^DOMAIN=" .env 2>/dev/null | cut -d= -f2 | tr -d '"' | tr -d "'")
fi

# Ask for domain
if [[ -n "$DOMAIN" ]]; then
    log_info "Found domain in .env: $DOMAIN"
    read -p "Use this domain? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        read -p "Enter your domain: " DOMAIN
    fi
else
    read -p "Enter your domain (e.g., studybuddyai.my): " DOMAIN
fi

# Ask for API credentials
echo ""
log_info "You need API credentials from your DNS provider (e.g., Hostinger)"
read -p "Enter API KEY: " API_KEY
read -p "Enter ZONE ID: " ZONE_ID

# Update the script
log_info "Configuring update_dns.sh..."

sed -i "s|API_KEY=\"YOUR_HOSTINGER_API_KEY\"|API_KEY=\"$API_KEY\"|g" scripts/update_dns.sh
sed -i "s|ZONE_ID=\"YOUR_HOSTINGER_ZONE_ID\"|ZONE_ID=\"$ZONE_ID\"|g" scripts/update_dns.sh
sed -i "s|DOMAIN=\"studybuddyai.my\"|DOMAIN=\"$DOMAIN\"|g" scripts/update_dns.sh

log_success "update_dns.sh configured"

# Make it executable
chmod +x scripts/update_dns.sh

# Test it
echo ""
log_info "Testing DNS update script..."
if bash scripts/update_dns.sh; then
    log_success "DNS update script works!"
else
    log_warning "DNS update script test failed - check configuration"
fi

# Setup cron job
echo ""
log_info "Setting up cron job..."

SCRIPT_PATH="$(pwd)/scripts/update_dns.sh"
CRON_ENTRY="*/5 * * * * $SCRIPT_PATH"

# Check if cron entry already exists
if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
    log_warning "Cron job already exists"
else
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    log_success "Cron job added (runs every 5 minutes)"
fi

echo ""
log_success "Dynamic DNS setup complete!"
echo ""
log_info "The script will run every 5 minutes to update DNS if IP changes"
log_info "Check logs: tail -f /var/log/update_dns.log"
echo ""
log_info "Current cron jobs:"
crontab -l | grep update_dns || echo "(none)"
echo ""
