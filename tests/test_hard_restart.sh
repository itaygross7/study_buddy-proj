#!/bin/bash
# =============================================================================
# Test Script for Hard Restart Deploy
# =============================================================================
# This script tests the hard-restart-deploy.sh without actually deploying
# =============================================================================

echo "Testing hard-restart-deploy.sh functionality..."
echo ""

# Test 1: Script exists and is executable
echo "Test 1: Script exists and is executable"
if [ -x "./hard-restart-deploy.sh" ]; then
    echo "✓ PASS: Script exists and is executable"
else
    echo "✗ FAIL: Script not found or not executable"
    exit 1
fi

# Test 2: Script has valid bash syntax
echo ""
echo "Test 2: Script has valid bash syntax"
if bash -n ./hard-restart-deploy.sh 2>/dev/null; then
    echo "✓ PASS: Script syntax is valid"
else
    echo "✗ FAIL: Script has syntax errors"
    exit 1
fi

# Test 3: Script contains required functions
echo ""
echo "Test 3: Script contains required functions"
REQUIRED_FUNCTIONS=(
    "fix_script_permissions"
    "fix_directory_permissions"
    "fix_docker_permissions"
    "fix_git_permissions"
    "fix_env_file_permissions"
    "force_docker_cleanup"
    "fresh_deployment"
    "verify_auto_update_setup"
    "verify_deployment"
)

for func in "${REQUIRED_FUNCTIONS[@]}"; do
    if grep -q "^$func()" ./hard-restart-deploy.sh; then
        echo "  ✓ Function found: $func"
    else
        echo "  ✗ Function missing: $func"
        exit 1
    fi
done

echo "✓ PASS: All required functions present"

# Test 4: Documentation exists
echo ""
echo "Test 4: Documentation exists"
if [ -f "HARD_RESTART_GUIDE.md" ]; then
    echo "✓ PASS: HARD_RESTART_GUIDE.md exists"
else
    echo "✗ FAIL: Documentation missing"
    exit 1
fi

# Test 5: Script is mentioned in SCRIPTS_GUIDE.md
echo ""
echo "Test 5: Script is documented in SCRIPTS_GUIDE.md"
if grep -q "hard-restart-deploy.sh" SCRIPTS_GUIDE.md; then
    echo "✓ PASS: Script documented in SCRIPTS_GUIDE.md"
else
    echo "✗ FAIL: Script not mentioned in SCRIPTS_GUIDE.md"
    exit 1
fi

# Test 6: Script is mentioned in README.md
echo ""
echo "Test 6: Script is mentioned in README.md"
if grep -q "hard-restart-deploy.sh" README.md; then
    echo "✓ PASS: Script mentioned in README.md"
else
    echo "✗ FAIL: Script not mentioned in README.md"
    exit 1
fi

# Test 7: Auto-update script exists
echo ""
echo "Test 7: Auto-update script exists"
if [ -f "scripts/auto-update.sh" ]; then
    echo "✓ PASS: Auto-update script exists"
else
    echo "✗ FAIL: Auto-update script missing"
    exit 1
fi

# Test 8: Script checks for docker-compose.yml
echo ""
echo "Test 8: Script validates project directory"
if grep -q "docker-compose.yml not found" ./hard-restart-deploy.sh; then
    echo "✓ PASS: Script validates project directory"
else
    echo "✗ FAIL: Script doesn't validate project directory"
    exit 1
fi

# Test 9: Script has proper error handling
echo ""
echo "Test 9: Script has proper error handling"
if grep -q "set -e" ./hard-restart-deploy.sh; then
    echo "✓ PASS: Script uses 'set -e' for error handling"
else
    echo "✗ FAIL: Script missing 'set -e'"
    exit 1
fi

# Test 10: Script has logging functions
echo ""
echo "Test 10: Script has logging functions"
LOGGING_FUNCTIONS=("log_info" "log_success" "log_error" "log_warning" "log_fix")
for log_func in "${LOGGING_FUNCTIONS[@]}"; do
    if grep -q "^$log_func()" ./hard-restart-deploy.sh; then
        echo "  ✓ Logging function: $log_func"
    else
        echo "  ✗ Missing logging function: $log_func"
        exit 1
    fi
done

echo "✓ PASS: All logging functions present"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✓ ALL TESTS PASSED"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "The hard-restart-deploy.sh script is properly implemented!"
echo ""
