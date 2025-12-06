# StudyBuddy Self-Healing Production Guide

## 🛡️ Self-Healing Architecture

StudyBuddy is designed as a **self-sustaining, production-grade application** that automatically monitors, detects issues, and recovers from failures without manual intervention.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Health Monitor Container                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  • Runs every 5 minutes                              │  │
│  │  • Tests all components (AI, DB, Worker, Upload)    │  │
│  │  • Restarts failed services automatically           │  │
│  │  • Sends email alerts on critical failures          │  │
│  │  • Daily health reports to admin                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          │
          ├──> Tests & Monitors
          │
┌─────────┴───────────────────────────────────────────────────┐
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │   App    │  │  Worker  │  │  MongoDB │  │ RabbitMQ  │  │
│  │Container │  │Container │  │Container │  │ Container │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────┘  │
│                                                               │
│  All containers have:                                        │
│  • restart: unless-stopped                                   │
│  • Health checks                                             │
│  • Automatic recovery                                        │
└───────────────────────────────────────────────────────────────┘
```

## 🔧 Self-Healing Features

### 1. Automatic Service Restart
- **Trigger**: Component fails health check 3 consecutive times
- **Action**: Docker container is automatically restarted
- **Cooldown**: 10 minutes between restarts to prevent restart loops
- **Components Monitored**:
  - MongoDB (database)
  - RabbitMQ (message queue)
  - App (Flask application)
  - Worker (background task processor)

### 2. Health Monitoring
Every 5 minutes, the system automatically tests:

#### ✅ AI Models
- Makes real API calls to OpenAI and Gemini
- Verifies models respond correctly
- Tests: "Say 'OK' if you can read this"
- Restarts app if AI fails

#### ✅ File Upload & Processing
- Creates actual test file with text
- Processes file through full pipeline
- Verifies text extraction works
- Stores in database
- Cleans up automatically
- Restarts worker if upload fails

#### ✅ RabbitMQ & Worker
- Checks connection to RabbitMQ
- Verifies all 6 queues exist
- Confirms worker is consuming messages
- Monitors message counts
- Restarts services if queue issues detected

#### ✅ Database Operations
- Tests MongoDB connection
- Performs write operation
- Performs read operation
- Verifies data integrity
- Restarts mongo if DB fails

#### ✅ Git Connectivity
- Checks if git repository is accessible
- Tests ability to fetch updates
- Verifies current branch and commit
- Checks for uncommitted changes
- Validates auto-update readiness
- *Note: Git issues don't trigger restart*

### 3. Email Notifications

#### Critical Alerts (Immediate)
Sent when a component fails:
```
Subject: 🚨 CRITICAL: [Component] Failure - StudyBuddy
- Component name and status
- Error details
- Time of failure
- Actions taken (restart)
- Recommended manual actions
```

**Rate Limited**: Max 1 alert per component per hour (prevents spam)

#### Daily Health Reports (8 AM)
Comprehensive status report including:
```
Subject: [✅/⚠️/❌] Daily Health Report - StudyBuddy
- Overall system status
- Component-by-component status
- File upload test results
- AI model status
- Worker activity
- Git update status
- Summary statistics
```

### 4. Docker Restart Policies
All containers configured with `restart: unless-stopped`:
- Automatically restart if they crash
- Restart on Docker daemon restart
- Restart on server reboot
- Won't restart if manually stopped

### 5. Health Check Endpoints

#### Simple Health Check
```bash
curl http://localhost:5000/health
# Returns: {"status": "healthy"}
```
**Use**: Load balancers, uptime monitoring

#### Detailed Health Check
```bash
curl http://localhost:5000/health/detailed
```
**Returns**: Comprehensive JSON with all component statuses
**Use**: Debugging, monitoring dashboards, admin review

## 🚀 Deployment for Maximum Reliability

### 1. Initial Setup
```bash
# Use the enhanced deployment script
sudo ./deploy-production.sh
```

This script:
- ✅ Pulls latest code from git
- ✅ Fixes all permissions
- ✅ Validates environment variables
- ✅ Checks AI model configuration
- ✅ Verifies worker starts correctly
- ✅ Runs initial health check

### 2. Systemd Integration (Auto-start on boot)
The deployment script creates a systemd service:

```bash
# Check service status
sudo systemctl status studybuddy

# View logs
sudo journalctl -u studybuddy -f

# Restart manually if needed
sudo systemctl restart studybuddy
```

### 3. Monitoring Logs

#### View Health Monitor Logs
```bash
docker logs studybuddy_health_monitor -f
```

#### View Worker Logs
```bash
docker logs studybuddy_worker -f
```

#### View App Logs
```bash
docker logs studybuddy_app -f
```

#### View All Logs
```bash
docker compose logs -f
```

## 📧 Email Configuration

### Required Environment Variables
```bash
# In your .env file:
ADMIN_EMAIL=your-admin@email.com
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### Gmail Setup (Recommended)
1. Enable 2-Factor Authentication
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Use app password in `MAIL_PASSWORD`

### Test Email Configuration
```bash
# Inside app container
docker exec -it studybuddy_app python -c "
from src.services.email_service import send_email
send_email(
    to_email='your@email.com',
    subject='Test Email',
    body='<h1>Test from StudyBuddy</h1>'
)
"
```

## 🔍 Troubleshooting Self-Healing

### Issue: Services keep restarting
**Cause**: Underlying issue not resolved by restart
**Solution**:
1. Check logs: `docker logs studybuddy_[service_name]`
2. Verify environment variables
3. Check system resources (disk space, memory)
4. Review recent changes

### Issue: No email alerts received
**Check**:
```bash
# Verify email config
docker exec studybuddy_health_monitor python -c "
from src.infrastructure.config import settings
print(f'Admin Email: {settings.ADMIN_EMAIL}')
print(f'Mail Server: {settings.MAIL_SERVER}')
"

# Test email manually
docker exec studybuddy_health_monitor python -c "
from health_monitor import send_critical_alert
send_critical_alert('test', 'This is a test alert')
"
```

### Issue: Health monitor not running
```bash
# Check if container is running
docker ps | grep health_monitor

# If not running, start it
docker compose up -d health_monitor

# Check logs for errors
docker logs studybuddy_health_monitor
```

### Issue: False positives (unnecessary restarts)
**Solution**: Adjust thresholds in `health_monitor.py`:
```python
MAX_CONSECUTIVE_FAILURES = 3  # Increase to 5 for more tolerance
RESTART_COOLDOWN_MINUTES = 10  # Increase to prevent rapid restarts
```

## 📊 Monitoring Dashboard (Optional)

### Prometheus + Grafana Setup
For production monitoring, consider:

1. **Prometheus**: Metrics collection
2. **Grafana**: Visualization
3. **AlertManager**: Advanced alerting

Example docker-compose addition:
```yaml
prometheus:
  image: prom/prometheus
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
```

## 🛡️ Security Best Practices

### 1. Email Security
- ✅ Use app passwords, not real passwords
- ✅ Restrict email sending to admin only
- ✅ Rate limit alerts (implemented)

### 2. Docker Socket Access
Health monitor has Docker socket access for restarts:
- ✅ Only used for service management
- ✅ No external access
- ✅ Limited to internal network

### 3. Health Endpoint Security
Consider adding authentication:
```python
@app.route('/health/detailed')
@require_admin  # Add this decorator
def detailed_health_check():
    ...
```

## 📈 Scaling Considerations

### Multiple Workers
```yaml
# In docker-compose.yml
worker:
  deploy:
    replicas: 3  # Run 3 worker instances
```

### Load Balancing
Use Nginx or Traefik in front of app:
```yaml
nginx:
  image: nginx
  ports:
    - "80:80"
  depends_on:
    - app
```

### Database Backup
Regular backups are critical:
```bash
# Add to cron
0 2 * * * docker exec studybuddy_mongo mongodump --out /backup
```

## 🎯 Best Practices for Administrators

### Daily Tasks
1. ✅ Check morning email for daily health report
2. ✅ Review any critical alerts received
3. ✅ Monitor disk space: `df -h`
4. ✅ Check Docker: `docker ps`

### Weekly Tasks
1. ✅ Review health monitor logs
2. ✅ Check for available updates: `git fetch`
3. ✅ Review resource usage: `docker stats`
4. ✅ Test manual failover

### Monthly Tasks
1. ✅ Update dependencies: `pip list --outdated`
2. ✅ Review and update .env configuration
3. ✅ Test backup restoration
4. ✅ Security audit

## 🆘 Emergency Procedures

### Complete System Failure
```bash
# 1. Stop everything
docker compose down

# 2. Check system resources
df -h
free -h
docker system df

# 3. Clean up if needed
docker system prune -a

# 4. Restart with hard reset
sudo ./deploy-hard-restart.sh
```

### Data Recovery
```bash
# Restore from MongoDB backup
docker exec studybuddy_mongo mongorestore /backup

# Check data integrity
docker exec studybuddy_mongo mongo --eval "db.documents.count()"
```

### Rollback Deployment
```bash
# Go to previous git commit
git log --oneline -10  # Find commit to rollback to
git checkout [commit-hash]
docker compose up -d --build
```

## 📞 Support & Maintenance

### Getting Help
1. Check logs first: `docker compose logs`
2. Review this documentation
3. Check GitHub issues
4. Email alerts should guide you to the problem

### Maintenance Mode
```bash
# Stop accepting new requests
docker compose stop app

# Perform maintenance
# ...

# Restart
docker compose start app
```

---

## ✅ Verification Checklist

After deployment, verify self-healing works:

- [ ] All containers are running: `docker ps`
- [ ] Health monitor is active: `docker logs studybuddy_health_monitor`
- [ ] Can access /health endpoint: `curl localhost:5000/health`
- [ ] Received test email (if configured)
- [ ] Systemd service enabled: `systemctl status studybuddy`
- [ ] Worker is processing: Check RabbitMQ admin at `http://localhost:15672`
- [ ] Git connectivity works: Check /health/detailed
- [ ] File upload test passes: Check health monitor logs

---

**Remember**: The system is designed to be self-sustaining. Trust the automation, but always verify critical changes!

📧 **Questions?** Check the health monitor logs first - they tell you everything!
