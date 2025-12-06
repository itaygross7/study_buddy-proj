# StudyBuddy Health Monitoring

Automated health monitoring with email alerts for the StudyBuddy application.

## Quick Start

1. **Configure email settings in `.env`**:
   ```bash
   ADMIN_EMAIL="your-email@example.com"
   MAIL_SERVER="smtp.gmail.com"
   MAIL_PORT=587
   MAIL_USERNAME="your-email@gmail.com"
   MAIL_PASSWORD="your-app-password"
   ```

2. **Install the health monitor**:
   ```bash
   sudo ./scripts/setup_health_monitor.sh
   ```

3. **Check status**:
   ```bash
   sudo systemctl status studybuddy-health-monitor
   ```

## Features

- **Automated Monitoring**: Checks app health every 60 seconds (configurable)
- **Email Alerts**: Sends alerts when app becomes unhealthy
- **Recovery Notifications**: Notifies when app recovers
- **Alert Cooldown**: Prevents email spam (1 hour default between alerts)
- **Failure Threshold**: Only alerts after 3 consecutive failures (configurable)

## Configuration

Add these to your `.env` file:

```bash
# Required for email alerts
ADMIN_EMAIL="your-email@example.com"

# Optional - defaults shown
HEALTH_CHECK_URL="http://localhost:5000/health"
HEALTH_CHECK_INTERVAL="60"              # Check every 60 seconds
MAX_CONSECUTIVE_FAILURES="3"            # Alert after 3 failures
ALERT_COOLDOWN_SECONDS="3600"           # 1 hour between alerts
```

## Management Commands

```bash
# View status
sudo systemctl status studybuddy-health-monitor

# View logs
sudo journalctl -u studybuddy-health-monitor -f

# Restart
sudo systemctl restart studybuddy-health-monitor

# Stop
sudo systemctl stop studybuddy-health-monitor

# Disable
sudo systemctl disable studybuddy-health-monitor
```

## Manual Testing

Test the monitor without installing as a service:

```bash
# One-time check
python3 scripts/health_monitor.py --once

# Continuous monitoring (Ctrl+C to stop)
python3 scripts/health_monitor.py
```

## Troubleshooting

### No emails received

1. Check email configuration in `.env`
2. Verify ADMIN_EMAIL is set
3. Check service logs: `sudo journalctl -u studybuddy-health-monitor -n 50`
4. Test email manually by triggering an error in the app

### False alerts

Increase the failure threshold:
```bash
MAX_CONSECUTIVE_FAILURES="5"  # Require 5 failures before alerting
```

### Too many alerts

Increase the cooldown period:
```bash
ALERT_COOLDOWN_SECONDS="7200"  # 2 hours between alerts
```

## Email Templates

The monitor sends two types of emails:

1. **Alert Email** (when app becomes unhealthy):
   - Includes timestamp, error details, consecutive failure count
   - Provides recommended actions
   - HTML formatted with red theme

2. **Recovery Email** (when app recovers):
   - Includes recovery timestamp
   - HTML formatted with green theme

## Security Notes

- The service file runs as root by default - change the `User=` line to run as a non-root user
- Email credentials are stored in `.env` - protect this file with proper permissions
- The monitor only reads the health endpoint - no write access to the app
