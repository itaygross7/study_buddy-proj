#!/bin/bash
# =============================================================================
# StudyBuddy API Endpoint Tester
# =============================================================================
# Tests all API endpoints to ensure they are functioning correctly
# =============================================================================

# Configuration
BASE_URL="${BASE_URL:-http://localhost:5000}"
VERBOSE="${VERBOSE:-false}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_error() { echo -e "${RED}[✗]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $*"; }

test_endpoint() {
    local method=$1
    local endpoint=$2
    local expected_status=$3
    local description=$4
    local data=$5
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [ "$VERBOSE" = "true" ]; then
        log_info "Testing: $description"
    fi
    
    # Make request
    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "${BASE_URL}${endpoint}" 2>&1)
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "${BASE_URL}${endpoint}" 2>&1)
    fi
    
    # Extract status code (last line)
    status_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')
    
    # Check status code
    if [ "$status_code" = "$expected_status" ]; then
        log_success "$description - $endpoint (HTTP $status_code)"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        log_error "$description - $endpoint (Expected $expected_status, got $status_code)"
        if [ "$VERBOSE" = "true" ] && [ -n "$body" ]; then
            echo "  Response: $body"
        fi
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

echo ""
echo "==============================================="
echo "  StudyBuddy API Endpoint Tests"
echo "  Base URL: $BASE_URL"
echo "==============================================="
echo ""

# Health Checks
log_info "Testing Health Check Endpoints..."
test_endpoint "GET" "/health" "200" "Basic health check"
test_endpoint "GET" "/health/live" "200" "Liveness probe"
test_endpoint "GET" "/health/ready" "200" "Readiness probe"
test_endpoint "GET" "/health/detailed" "200" "Detailed health check"

# Main Routes
log_info "Testing Main UI Routes..."
test_endpoint "GET" "/" "200" "Home page"

# Auth Routes (public endpoints)
log_info "Testing Auth Routes..."
test_endpoint "GET" "/auth/login" "200" "Login page"
test_endpoint "GET" "/auth/signup" "200" "Signup page"

# API Routes (should require auth or return proper errors)
log_info "Testing API Routes..."
test_endpoint "POST" "/api/avner/ask" "400" "Avner ask (no data)"
test_endpoint "GET" "/api/avner/tips" "200" "Avner tips"
test_endpoint "GET" "/api/avner/app-help" "200" "Avner app help"

# Webhook Routes
log_info "Testing Webhook Routes..."
test_endpoint "GET" "/webhook/health" "200" "Webhook health"

# Test invalid endpoints (should return 404)
log_info "Testing Error Handling..."
test_endpoint "GET" "/nonexistent" "404" "Non-existent page"
test_endpoint "GET" "/api/nonexistent" "404" "Non-existent API endpoint"

# Summary
echo ""
echo "==============================================="
echo "  Test Summary"
echo "==============================================="
echo -e "Total Tests:  ${BLUE}$TOTAL_TESTS${NC}"
echo -e "Passed:       ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed:       ${RED}$FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    log_success "All tests passed!"
    exit 0
else
    log_error "Some tests failed!"
    exit 1
fi
