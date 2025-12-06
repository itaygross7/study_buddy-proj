#!/bin/bash
# Setup Health Monitor Service
#
# This script installs and enables the StudyBuddy health monitor service
# that will send email alerts when the application becomes unhealthy.
#
# Usage: sudo ./scripts/setup_health_monitor.sh

set -e

echo "Setting up StudyBuddy Health Monitor..."

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Check if .env file exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "Error: .env file not found at $PROJECT_ROOT/.env"
    echo "Please create .env with ADMIN_EMAIL and email configuration"
    exit 1
fi

# Install Python dependencies if needed
echo "Checking Python dependencies..."
pip3 install requests python-dotenv pydantic pydantic-settings python-json-logger >/dev/null 2>&1 || true

# Copy service file to systemd
echo "Installing systemd service..."
SERVICE_FILE="$PROJECT_ROOT/studybuddy-health-monitor.service"
SYSTEMD_SERVICE="/etc/systemd/system/studybuddy-health-monitor.service"

# Update paths in service file
sed "s|/root/study_buddy-proj|$PROJECT_ROOT|g" "$SERVICE_FILE" > "$SYSTEMD_SERVICE"

# Reload systemd
systemctl daemon-reload

# Enable and start service
echo "Enabling health monitor service..."
systemctl enable studybuddy-health-monitor.service

echo "Starting health monitor service..."
systemctl start studybuddy-health-monitor.service

# Show status
echo ""
echo "✓ Health monitor installed successfully!"
echo ""
echo "Service status:"
systemctl status studybuddy-health-monitor.service --no-pager || true
echo ""
echo "Useful commands:"
echo "  - Check status:  sudo systemctl status studybuddy-health-monitor"
echo "  - View logs:     sudo journalctl -u studybuddy-health-monitor -f"
echo "  - Restart:       sudo systemctl restart studybuddy-health-monitor"
echo "  - Stop:          sudo systemctl stop studybuddy-health-monitor"
echo "  - Disable:       sudo systemctl disable studybuddy-health-monitor"
echo ""
echo "Configuration (edit .env):"
echo "  - ADMIN_EMAIL: Email address for alerts"
echo "  - HEALTH_CHECK_URL: URL to monitor (default: http://localhost:5000/health)"
echo "  - HEALTH_CHECK_INTERVAL: Check interval in seconds (default: 60)"
echo "  - MAX_CONSECUTIVE_FAILURES: Failures before alert (default: 3)"
echo "  - ALERT_COOLDOWN_SECONDS: Time between alerts (default: 3600)"
