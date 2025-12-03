# Health Monitoring and Restart Guide

This guide explains the health monitoring, restart, and API testing tools available for StudyBuddy.

## Quick Reference

```bash
# Restart the application
./scripts/restart-app.sh

# Test all API endpoints
./scripts/test-api-endpoints.sh

# Start health monitoring
./scripts/health-monitor.sh

# Check Tailscale status
sudo tailscale status
```

## Health Check Endpoints

### Basic Health Check
```bash
curl http://localhost:5000/health
# Returns: {"status":"healthy"}
```

### Detailed Health Check
```bash
curl http://localhost:5000/health/detailed
```
Returns detailed status of all components:
- MongoDB connection
- RabbitMQ connection
- AI service configuration
- Email service configuration

### Liveness Probe
```bash
curl http://localhost:5000/health/live
# Returns: {"status":"alive"}
```
Simple check that the application process is running.

### Readiness Probe
```bash
curl http://localhost:5000/health/ready
# Returns: {"status":"ready"} or {"status":"not ready"}
```
Checks if the application is ready to serve requests (MongoDB connection).

## Restart Script

### Basic Usage

```bash
# Restart all services
./scripts/restart-app.sh

# Restart specific component
./scripts/restart-app.sh app
./scripts/restart-app.sh worker
./scripts/restart-app.sh mongo
./scripts/restart-app.sh rabbitmq
./scripts/restart-app.sh caddy

# Rebuild containers before restarting
./scripts/restart-app.sh --rebuild
./scripts/restart-app.sh -r app
```

### How It Works

The script automatically detects:
- If running via systemd service → Uses `systemctl restart`
- If running via docker compose → Uses `docker compose restart`

After restart, it performs a health check to verify the application is responding.

### Use Cases

- **After configuration changes**: Restart to apply new settings
- **Performance issues**: Quick restart to clear memory leaks
- **Component-specific issues**: Restart only the affected component
- **Manual maintenance**: Controlled restart during maintenance windows

## Health Monitor

### Starting the Monitor

```bash
# Start in foreground
./scripts/health-monitor.sh

# Start in background
nohup ./scripts/health-monitor.sh &

# Configure check interval and max failures
CHECK_INTERVAL=60 MAX_FAILURES=5 ./scripts/health-monitor.sh
```

### How It Works

1. **Checks application health** every 30 seconds (configurable)
2. **Counts failures** for each component
3. **Automatically restarts** components after max failures (default: 3)
4. **Logs all actions** to `/var/log/studybuddy-healthcheck.log`

### Components Monitored

- **Application**: Main Flask app via `/health` endpoint
- **MongoDB**: Container health and connectivity
- **RabbitMQ**: Container health and connectivity
- **Detailed health**: All component statuses via `/health/detailed`

### Configuration

Environment variables:
- `CHECK_INTERVAL`: Seconds between checks (default: 30)
- `MAX_FAILURES`: Failures before restart (default: 3)
- `LOG_FILE`: Log file location (default: `/var/log/studybuddy-healthcheck.log`)

### Running as Service

To run the health monitor automatically on boot:

```bash
# Create systemd service
sudo tee /etc/systemd/system/studybuddy-healthcheck.service > /dev/null << EOF
[Unit]
Description=StudyBuddy Health Check Monitor
After=studybuddy.service
Requires=studybuddy.service

[Service]
Type=simple
ExecStart=/home/runner/work/study_buddy-proj/study_buddy-proj/scripts/health-monitor.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable studybuddy-healthcheck
sudo systemctl start studybuddy-healthcheck

# Check status
sudo systemctl status studybuddy-healthcheck

# View logs
sudo journalctl -u studybuddy-healthcheck -f
```

## API Endpoint Testing

### Running Tests

```bash
# Run all endpoint tests
./scripts/test-api-endpoints.sh

# Run with verbose output
VERBOSE=true ./scripts/test-api-endpoints.sh

# Test different URL
BASE_URL=https://yourdomain.com ./scripts/test-api-endpoints.sh
```

### What It Tests

The script tests all major endpoints:

**Health Checks:**
- `/health` - Basic health check
- `/health/live` - Liveness probe
- `/health/ready` - Readiness probe
- `/health/detailed` - Detailed component health

**UI Routes:**
- `/` - Home page
- `/auth/login` - Login page
- `/auth/signup` - Signup page

**API Routes:**
- `/api/avner/*` - Avner chat endpoints
- `/webhook/*` - Webhook endpoints
- Error handling (404 responses)

### Output

```
===============================================
  StudyBuddy API Endpoint Tests
  Base URL: http://localhost:5000
===============================================

[INFO] Testing Health Check Endpoints...
[✓] Basic health check - /health (HTTP 200)
[✓] Liveness probe - /health/live (HTTP 200)
[✓] Readiness probe - /health/ready (HTTP 200)
[✓] Detailed health check - /health/detailed (HTTP 200)

...

===============================================
  Test Summary
===============================================
Total Tests:  15
Passed:       15
Failed:       0

[✓] All tests passed!
```

### Integration with CI/CD

Add to your deployment pipeline:

```bash
# After deployment
./scripts/test-api-endpoints.sh || exit 1
```

## Docker Health Check Container

The health check container is automatically started with docker compose and continuously monitors the application.

### View Health Check Logs

```bash
# View health check container logs
docker compose logs -f healthcheck

# Check health check status
docker compose ps healthcheck
```

### Configuration in docker-compose.yml

The health check container:
- Runs Alpine Linux with curl and bash
- Mounts the health-monitor.sh script
- Starts after the app is healthy
- Restarts automatically if it crashes

## Tailscale Verification

### Check Tailscale Status

```bash
# View Tailscale status
sudo tailscale status

# Get your Tailscale IP
sudo tailscale ip -4

# Test connectivity
sudo tailscale ping <device-name>
```

### Verify Firewall Rules

```bash
# Check UFW status
sudo ufw status verbose

# Should show:
# - SSH allowed on tailscale0 interface only
# - HTTPS (80, 443) allowed from anywhere
```

### Test SSH via Tailscale

```bash
# From another device on your Tailscale network
ssh user@<tailscale-ip>

# Should work ✓

# From public internet (should fail)
ssh user@<public-ip>  # Connection refused ✗
```

## Troubleshooting

### Health Checks Failing

1. **Check application logs:**
   ```bash
   docker compose logs -f app
   ```

2. **Test endpoints manually:**
   ```bash
   curl -v http://localhost:5000/health
   curl -v http://localhost:5000/health/detailed
   ```

3. **Check component status:**
   ```bash
   docker compose ps
   ```

### Health Monitor Not Restarting

1. **Check monitor logs:**
   ```bash
   cat /var/log/studybuddy-healthcheck.log
   ```

2. **Verify permissions:**
   ```bash
   # Monitor needs sudo for restarts
   sudo -v
   ```

3. **Test restart manually:**
   ```bash
   ./scripts/restart-app.sh
   ```

### API Tests Failing

1. **Check which endpoints are failing:**
   ```bash
   VERBOSE=true ./scripts/test-api-endpoints.sh
   ```

2. **Test specific endpoint:**
   ```bash
   curl -v http://localhost:5000/api/avner/tips
   ```

3. **Check application errors:**
   ```bash
   docker compose logs app | grep ERROR
   ```

### Tailscale Issues

1. **Restart Tailscale:**
   ```bash
   sudo tailscale down
   sudo tailscale up
   ```

2. **Check authentication:**
   ```bash
   sudo tailscale status
   # Should show "Logged in" status
   ```

3. **Verify firewall:**
   ```bash
   sudo ufw status
   # Check SSH rule is on tailscale interface
   ```

## Best Practices

### Production Deployment

1. **Enable health monitoring service:**
   ```bash
   sudo systemctl enable studybuddy-healthcheck
   ```

2. **Run API tests after deployment:**
   ```bash
   ./scripts/test-api-endpoints.sh
   ```

3. **Monitor health check logs:**
   ```bash
   sudo journalctl -u studybuddy-healthcheck -f
   ```

### Maintenance Windows

1. **Before maintenance:**
   ```bash
   # Stop health monitor to prevent auto-restart
   sudo systemctl stop studybuddy-healthcheck
   ```

2. **Perform maintenance:**
   ```bash
   ./scripts/restart-app.sh --rebuild
   ```

3. **After maintenance:**
   ```bash
   # Test endpoints
   ./scripts/test-api-endpoints.sh
   
   # Resume monitoring
   sudo systemctl start studybuddy-healthcheck
   ```

### Monitoring

Set up alerts for health check failures:

```bash
# Watch for errors in health logs
tail -f /var/log/studybuddy-healthcheck.log | grep ERROR
```

Consider integrating with monitoring tools:
- Prometheus metrics from health endpoints
- Grafana dashboards for visualization
- Alert manager for notifications

## Summary

You now have:
- ✅ **4 health check endpoints** (basic, detailed, live, ready)
- ✅ **Restart script** (manual or automated)
- ✅ **Health monitor** (continuous monitoring and auto-restart)
- ✅ **API endpoint tests** (verify all routes work)
- ✅ **Tailscale verification** (secure access confirmed)
- ✅ **Docker health container** (built-in monitoring)

All tools work together to ensure your StudyBuddy deployment is:
- **Reliable**: Auto-restart on failure
- **Monitored**: Continuous health checks
- **Testable**: Easy endpoint verification
- **Secure**: Tailscale-only SSH access
