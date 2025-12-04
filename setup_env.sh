#!/bin/bash
# =============================================================================
# Interactive .env Configuration Helper
# =============================================================================
# This script helps you create a valid .env file with all required settings

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}  StudyBuddy Configuration Helper 🦫${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Check if .env already exists
if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Warning: .env file already exists!${NC}"
    echo ""
    read -p "Do you want to backup and recreate it? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting without changes."
        exit 0
    fi
    
    # Backup existing .env
    backup_file="$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$ENV_FILE" "$backup_file"
    echo -e "${GREEN}✓${NC} Backed up existing .env to: $backup_file"
    echo ""
fi

# Copy from example
if [ ! -f "$ENV_EXAMPLE" ]; then
    echo -e "${RED}Error: .env.example not found!${NC}"
    exit 1
fi

cp "$ENV_EXAMPLE" "$ENV_FILE"
echo -e "${GREEN}✓${NC} Created .env from .env.example"
echo ""

# Function to update .env file
update_env() {
    local key=$1
    local value=$2
    
    # Escape special characters for sed
    value=$(echo "$value" | sed 's/[\/&]/\\&/g')
    
    # Update the value in .env
    sed -i "s|^${key}=.*|${key}=\"${value}\"|" "$ENV_FILE"
}

# ============================================================================
# 1. AI Provider Configuration (REQUIRED)
# ============================================================================
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}1. AI Provider Configuration (REQUIRED)${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "StudyBuddy requires at least one AI provider."
echo ""
echo "Options:"
echo "  1) Google Gemini (Recommended - Free tier available)"
echo "  2) OpenAI (Requires payment/credits)"
echo "  3) Both"
echo ""

read -p "Which AI provider(s)? (1/2/3): " ai_choice

if [ "$ai_choice" = "1" ] || [ "$ai_choice" = "3" ]; then
    echo ""
    echo "Get your Gemini API key from: https://makersuite.google.com/app/apikey"
    read -p "Enter your Gemini API key: " gemini_key
    if [ -n "$gemini_key" ]; then
        update_env "GEMINI_API_KEY" "$gemini_key"
        echo -e "${GREEN}✓${NC} Gemini API key configured"
    fi
fi

if [ "$ai_choice" = "2" ] || [ "$ai_choice" = "3" ]; then
    echo ""
    echo "Get your OpenAI API key from: https://platform.openai.com/api-keys"
    read -p "Enter your OpenAI API key: " openai_key
    if [ -n "$openai_key" ]; then
        update_env "OPENAI_API_KEY" "$openai_key"
        echo -e "${GREEN}✓${NC} OpenAI API key configured"
    fi
fi

# ============================================================================
# 2. Domain Configuration
# ============================================================================
echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}2. Domain Configuration${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "This is where users will access StudyBuddy."
echo ""
echo "Examples:"
echo "  - Production: https://studybuddy.example.com"
echo "  - Development: http://localhost:5000"
echo "  - Local network: http://192.168.1.100:5000"
echo ""

read -p "Enter your BASE_URL [http://localhost:5000]: " base_url
base_url=${base_url:-http://localhost:5000}
update_env "BASE_URL" "$base_url"

# Extract domain from BASE_URL
domain=$(echo "$base_url" | sed -E 's|https?://([^:/]+).*|\1|')
update_env "DOMAIN" "$domain"
echo -e "${GREEN}✓${NC} Domain configured: $domain"

# ============================================================================
# 3. Email Configuration (Optional but recommended)
# ============================================================================
echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}3. Email Configuration (Optional)${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "Email is used for:"
echo "  - Account verification"
echo "  - Password reset"
echo "  - Admin notifications"
echo ""

read -p "Configure email now? (y/n) [n]: " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Gmail Setup (recommended):"
    echo "  1. Enable 2-Step Verification: https://myaccount.google.com/security"
    echo "  2. Generate App Password: https://myaccount.google.com/apppasswords"
    echo "  3. Use the 16-character app password below"
    echo ""
    
    read -p "Enter your Gmail address: " mail_username
    if [ -n "$mail_username" ]; then
        update_env "MAIL_USERNAME" "$mail_username"
        update_env "MAIL_DEFAULT_SENDER" "StudyBuddy <$mail_username>"
        
        read -p "Enter your Gmail App Password (16 chars): " mail_password
        if [ -n "$mail_password" ]; then
            update_env "MAIL_PASSWORD" "$mail_password"
            echo -e "${GREEN}✓${NC} Email configured"
        fi
    fi
else
    echo "Skipping email configuration. You can configure it later in .env"
fi

# ============================================================================
# 4. Google Sign-In (Optional)
# ============================================================================
echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}4. Google Sign-In (Optional)${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "Allows users to sign in with their Google account."
echo ""
echo "Setup:"
echo "  1. Go to: https://console.cloud.google.com/"
echo "  2. Create OAuth 2.0 credentials"
echo "  3. Add redirect URI: ${base_url}/oauth/google/callback"
echo ""

read -p "Configure Google Sign-In now? (y/n) [n]: " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    read -p "Enter Google Client ID: " google_id
    if [ -n "$google_id" ]; then
        update_env "GOOGLE_CLIENT_ID" "$google_id"
        
        read -p "Enter Google Client Secret: " google_secret
        if [ -n "$google_secret" ]; then
            update_env "GOOGLE_CLIENT_SECRET" "$google_secret"
            echo -e "${GREEN}✓${NC} Google Sign-In configured"
        fi
    fi
else
    echo "Skipping Google Sign-In. You can configure it later in .env"
fi

# ============================================================================
# 5. Admin Email (Optional but recommended)
# ============================================================================
echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}5. Admin Account${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "The admin email gets automatic admin privileges."
echo ""

read -p "Enter admin email [skip]: " admin_email
if [ -n "$admin_email" ]; then
    update_env "ADMIN_EMAIL" "$admin_email"
    echo -e "${GREEN}✓${NC} Admin email configured"
fi

# ============================================================================
# 6. Generate Secret Key
# ============================================================================
echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}6. Security${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Check if python3 is available
if command -v python3 &> /dev/null; then
    secret_key=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
    update_env "SECRET_KEY" "$secret_key"
    echo -e "${GREEN}✓${NC} Generated secure SECRET_KEY"
else
    echo -e "${YELLOW}⚠${NC} Could not generate SECRET_KEY (python3 not found)"
    echo "   Please edit .env and set a secure SECRET_KEY manually"
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Configuration Complete! ✓${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "Your .env file has been created with the following configuration:"
echo ""

# Validate configuration
if command -v python3 &> /dev/null; then
    if python3 "$SCRIPT_DIR/check_config.py"; then
        echo ""
        echo -e "${GREEN}✓ Configuration is valid!${NC}"
        echo ""
        echo "Next steps:"
        echo "  1. Start the application: docker compose up -d --build"
        echo "  2. View logs: docker compose logs -f app"
        echo "  3. Access at: ${base_url}"
    else
        echo ""
        echo -e "${YELLOW}⚠ Configuration has some issues (see above)${NC}"
        echo ""
        echo "You can:"
        echo "  1. Edit .env manually to fix issues"
        echo "  2. Re-run this script: ./setup_env.sh"
        echo "  3. Check config: python3 check_config.py"
    fi
else
    echo "Configuration file created at: $ENV_FILE"
    echo ""
    echo "Next steps:"
    echo "  1. Review .env file"
    echo "  2. Start the application: docker compose up -d --build"
    echo "  3. Access at: ${base_url}"
fi

echo ""
echo "For troubleshooting, see: TROUBLESHOOTING.md"
echo ""
