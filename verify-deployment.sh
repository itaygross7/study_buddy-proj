#!/bin/bash
# Deployment Verification Script for StudyBuddy
# Run this after deploying to verify everything is working correctly

echo "🚀 StudyBuddy Deployment Verification"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running in project directory
if [ ! -f "app.py" ]; then
    echo -e "${RED}❌ Error: Run this script from the project root directory${NC}"
    exit 1
fi

# Function to check file existence and modification time
check_file() {
    local file=$1
    local description=$2
    
    if [ -f "$file" ]; then
        local mod_time=$(stat -c %y "$file" 2>/dev/null || stat -f "%Sm" "$file" 2>/dev/null)
        echo -e "${GREEN}✅ $description exists${NC}"
        echo "   Modified: $mod_time"
        return 0
    else
        echo -e "${RED}❌ $description NOT FOUND${NC}"
        return 1
    fi
}

echo "1. Checking Critical Files"
echo "--------------------------"
check_file "ui/static/css/styles.css" "Compiled CSS"
check_file "ui/static/css/input.css" "Source CSS"
check_file "DEPLOYMENT_INSTRUCTIONS.md" "Deployment Guide"
check_file ".env" "Environment Configuration"
echo ""

echo "2. Checking CSS File Size"
echo "-------------------------"
css_size=$(wc -c < "ui/static/css/styles.css" 2>/dev/null || echo "0")
if [ "$css_size" -gt 30000 ]; then
    echo -e "${GREEN}✅ CSS file size: $css_size bytes (looks good)${NC}"
else
    echo -e "${RED}❌ CSS file size: $css_size bytes (too small, may not be built)${NC}"
    echo -e "${YELLOW}   Run: npm run tailwind:build${NC}"
fi
echo ""

echo "3. Checking Node.js Dependencies"
echo "--------------------------------"
if [ -d "node_modules" ]; then
    echo -e "${GREEN}✅ node_modules directory exists${NC}"
else
    echo -e "${YELLOW}⚠️  node_modules NOT FOUND${NC}"
    echo -e "${YELLOW}   Run: npm install${NC}"
fi
echo ""

echo "4. Checking CSS Contains Mobile Fixes"
echo "-------------------------------------"
if grep -q "mobile-touch-target" "ui/static/css/styles.css"; then
    echo -e "${GREEN}✅ Mobile CSS classes found in compiled CSS${NC}"
else
    echo -e "${RED}❌ Mobile CSS classes NOT FOUND${NC}"
    echo -e "${YELLOW}   Run: npm run tailwind:build${NC}"
fi

if grep -q "webkit-appearance" "ui/static/css/styles.css"; then
    echo -e "${GREEN}✅ iOS Safari fixes found in compiled CSS${NC}"
else
    echo -e "${RED}❌ iOS Safari fixes NOT FOUND${NC}"
    echo -e "${YELLOW}   Run: npm run tailwind:build${NC}"
fi
echo ""

echo "5. Checking Environment Configuration"
echo "-------------------------------------"
if [ -f ".env" ]; then
    # Check for critical environment variables (without exposing values)
    if grep -q "GEMINI_API_KEY=" ".env" || grep -q "OPENAI_API_KEY=" ".env"; then
        echo -e "${GREEN}✅ AI API key configured${NC}"
    else
        echo -e "${YELLOW}⚠️  No AI API key found in .env${NC}"
        echo -e "${YELLOW}   Chat functionality requires GEMINI_API_KEY or OPENAI_API_KEY${NC}"
    fi
    
    if grep -q "SECRET_KEY=" ".env"; then
        echo -e "${GREEN}✅ Flask SECRET_KEY configured${NC}"
    else
        echo -e "${RED}❌ SECRET_KEY not configured${NC}"
    fi
    
    if grep -q "MONGO_URI=" ".env"; then
        echo -e "${GREEN}✅ MongoDB URI configured${NC}"
    else
        echo -e "${RED}❌ MONGO_URI not configured${NC}"
    fi
else
    echo -e "${RED}❌ .env file NOT FOUND${NC}"
    echo -e "${YELLOW}   Copy .env.example to .env and configure${NC}"
fi
echo ""

echo "6. Docker Status"
echo "----------------"
if command -v docker &> /dev/null; then
    if docker ps | grep -q "study"; then
        echo -e "${GREEN}✅ StudyBuddy containers are running${NC}"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "study"
    else
        echo -e "${YELLOW}⚠️  No StudyBuddy containers running${NC}"
        echo -e "${YELLOW}   Run: docker-compose up -d${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Docker not installed or not accessible${NC}"
fi
echo ""

echo "7. Testing HTTP Endpoint (if running)"
echo "-------------------------------------"
if curl -s http://localhost:5000/health 2>/dev/null | grep -q "ok"; then
    echo -e "${GREEN}✅ Application is responding on http://localhost:5000${NC}"
else
    echo -e "${YELLOW}⚠️  Application not responding on http://localhost:5000${NC}"
    echo -e "${YELLOW}   Make sure the application is running${NC}"
fi
echo ""

echo "======================================"
echo "📋 Summary"
echo "======================================"
echo ""
echo "Next Steps:"
echo "1. If CSS issues found: Run 'npm run tailwind:build'"
echo "2. If containers not running: Run 'docker-compose up -d'"
echo "3. If .env missing: Copy and configure '.env.example'"
echo "4. Test on iPhone 15 Safari:"
echo "   - Clear Safari cache"
echo "   - Test file upload"
echo "   - Test chat functionality"
echo ""
echo "📖 See DEPLOYMENT_INSTRUCTIONS.md for detailed instructions"
echo ""
