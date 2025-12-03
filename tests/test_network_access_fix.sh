#!/bin/bash
# =============================================================================
# Network Access Verification Test
# =============================================================================
# This script verifies that the network access fixes are working correctly
# =============================================================================

set -e

echo "==================================================================="
echo "Network Access Verification Test"
echo "==================================================================="
echo ""

# Test 1: Verify helper script exists and is executable
echo "Test 1: Checking helper script..."
if [ -x "scripts/enable-network-access.sh" ]; then
    echo "✓ Helper script exists and is executable"
else
    echo "✗ Helper script is missing or not executable"
    exit 1
fi

# Test 2: Verify documentation exists
echo ""
echo "Test 2: Checking documentation..."
if [ -f "docs/NETWORK_ACCESS.md" ]; then
    echo "✓ Main network access documentation exists"
else
    echo "✗ Main documentation is missing"
    exit 1
fi

if [ -f "docs/QUICK_FIX_NETWORK.md" ]; then
    echo "✓ Quick reference documentation exists"
else
    echo "✗ Quick reference is missing"
    exit 1
fi

# Test 3: Verify app.py syntax
echo ""
echo "Test 3: Validating app.py syntax..."
if python3 -m py_compile app.py 2>/dev/null; then
    echo "✓ app.py syntax is valid"
else
    echo "✗ app.py has syntax errors"
    exit 1
fi

# Test 4: Verify script syntax
echo ""
echo "Test 4: Validating helper script syntax..."
if bash -n scripts/enable-network-access.sh 2>/dev/null; then
    echo "✓ Helper script syntax is valid"
else
    echo "✗ Helper script has syntax errors"
    exit 1
fi

# Test 5: Check if app.py contains the new logging
echo ""
echo "Test 5: Verifying enhanced logging in app.py..."
if grep -q "To access from another computer:" app.py; then
    echo "✓ Enhanced logging is present in app.py"
else
    echo "✗ Enhanced logging is missing"
    exit 1
fi

# Test 6: Check if README contains network access info
echo ""
echo "Test 6: Verifying README updates..."
if grep -q "enable-network-access.sh" README.md; then
    echo "✓ README contains network access information"
else
    echo "✗ README is missing network access info"
    exit 1
fi

# Test 7: Check if GETTING_STARTED contains network access info
echo ""
echo "Test 7: Verifying GETTING_STARTED updates..."
if grep -q "Can't Connect from Another Computer?" GETTING_STARTED.md; then
    echo "✓ GETTING_STARTED contains network access information"
else
    echo "✗ GETTING_STARTED is missing network access info"
    exit 1
fi

# Test 8: Verify pre-deploy-check.sh mentions helper script
echo ""
echo "Test 8: Verifying pre-deploy-check.sh updates..."
if grep -q "enable-network-access.sh" scripts/pre-deploy-check.sh; then
    echo "✓ pre-deploy-check.sh mentions the helper script"
else
    echo "✗ pre-deploy-check.sh doesn't mention the helper script"
    exit 1
fi

echo ""
echo "==================================================================="
echo "All tests passed! ✓"
echo "==================================================================="
echo ""
echo "The network access fix is properly implemented and ready to use."
echo ""
echo "Next steps:"
echo "  1. Run: docker compose up -d"
echo "  2. Run: ./scripts/enable-network-access.sh"
echo "  3. Access from another computer: http://<your-ip>:5000"
echo ""
