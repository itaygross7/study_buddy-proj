#!/bin/bash
# =============================================================================
# Interactive .env Configuration Helper (Cloudflare Edition)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}  StudyBuddy Configuration Helper 🦫${NC}"
echo -e "${BLUE}=========================================${NC}"

# Create .env if missing
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        echo -e "${GREEN}✓ Created .env from example${NC}"
    else
        touch "$ENV_FILE"
        echo -e "${GREEN}✓ Created empty .env${NC}"
    fi
fi

# Function to update .env file
update_env() {
    local key=$1
    local value=$2
    # If key exists, replace it. If not, append it.
    if grep -q "^${key}=" "$ENV_FILE"; then
        sed -i "s|^${key}=.*|${key}=\"${value}\"|" "$ENV_FILE"
    else
        echo "${key}=\"${value}\"" >> "$ENV_FILE"
    fi
}

# ============================================================================
# 1. Cloudflare Tunnel (CRITICAL)
# ============================================================================
echo ""
echo -e "${BLUE}1. Cloudflare Tunnel Configuration${NC}"
echo "You need the token from the Cloudflare Zero Trust Dashboard."
echo "If you don't have this, the site will not be accessible."
echo ""
read -p "Paste your TUNNEL_TOKEN: " tunnel_token

if [ -n "$tunnel_token" ]; then
    update_env "TUNNEL_TOKEN" "$tunnel_token"
    echo -e "${GREEN}✓ Token saved${NC}"
else
    echo -e "${RED}⚠️  Token skipped (App will not go online)${NC}"
fi

# ============================================================================
# 2. AI Providers
# ============================================================================
echo ""
echo -e "${BLUE}2. AI Providers${NC}"
echo "We need at least one AI key."

read -p "Enter Gemini API Key (Enter to skip): " gemini_key
if [ -n "$gemini_key" ]; then
    update_env "GEMINI_API_KEY" "$gemini_key"
    echo -e "${GREEN}✓ Gemini saved${NC}"
fi

read -p "Enter OpenAI API Key (Enter to skip): " openai_key
if [ -n "$openai_key" ]; then
    update_env "OPENAI_API_KEY" "$openai_key"
    echo -e "${GREEN}✓ OpenAI saved${NC}"
fi

# ============================================================================
# 3. Domain Settings
# ============================================================================
echo ""
echo -e "${BLUE}3. Domain Configuration${NC}"
echo "Enter the domain you configured in Cloudflare (e.g., studybuddyai.my)"
read -p "Domain: " domain_input

if [ -n "$domain_input" ]; then
    update_env "DOMAIN" "$domain_input"
    update_env "BASE_URL" "https://$domain_input"
    echo -e "${GREEN}✓ Domain saved${NC}"
fi

# ============================================================================
# 4. Security
# ============================================================================
echo ""
echo -e "${BLUE}4. Security${NC}"
# Check if python3 is available to generate key
if command -v python3 &> /dev/null; then
    current_key=$(grep "^SECRET_KEY=" "$ENV_FILE" | cut -d'"' -f2)
    if [[ -z "$current_key" || "$current_key" == "change-this" ]]; then
        secret_key=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
        update_env "SECRET_KEY" "$secret_key"
        echo -e "${GREEN}✓ Generated new secure SECRET_KEY${NC}"
    else
        echo -e "${GREEN}✓ SECRET_KEY already set${NC}"
    fi
fi

echo ""
echo -e "${BLUE}Configuration Complete!${NC}"
echo "Run 'python3 check_config.py' to verify everything is valid."
