# 🚀 StudyBuddy Production Deployment Checklist

## Pre-Deployment (Do Once)

### 1. Server Setup
- [ ] Ubuntu/Debian server (20.04+ or 11+)
- [ ] At least 2GB RAM, 20GB disk space
- [ ] Root or sudo access
- [ ] Internet connectivity

### 2. Clone Repository
```bash
git clone https://github.com/itaygross7/study_buddy-proj.git
cd study_buddy-proj
```

### 3. Configure Environment (.env)
```bash
cp .env.example .env
nano .env  # or vim .env
```

**Required Variables:**
```bash
# Infrastructure
SECRET_KEY=<generate-random-32-chars>
MONGO_URI=mongodb://mongo:27017/studybuddy
RABBITMQ_URI=amqp://user:password@rabbitmq:5672/

# AI Models (AT LEAST ONE REQUIRED)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
SB_DEFAULT_PROVIDER=gemini  # or openai

# Email Alerts (REQUIRED FOR MONITORING)
ADMIN_EMAIL=your-admin@email.com
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Cloudflare Tunnel (for external access)
TUNNEL_TOKEN=eyJh...  # Get from Cloudflare dashboard
```

### 4. Generate Secret Key
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Email Setup (Gmail Example)
1. Go to https://myaccount.google.com/apppasswords
2. Enable 2-Factor Authentication first
3. Generate App Password
4. Use app password in MAIL_PASSWORD

---

## Initial Deployment

### Run Enhanced Deployment Script
```bash
sudo ./deploy-production.sh
```

**What it does:**
- ✅ Pulls latest code from git
- ✅ Fixes permissions
- ✅ Validates environment variables
- ✅ Checks AI model configuration
- ✅ Installs Docker if needed
- ✅ Configures firewall
- ✅ Starts all containers
- ✅ Verifies worker health
- ✅ Creates systemd service

### Expected Output
```
✓ Latest code pulled from git
✓ Environment variables validated
✓ OpenAI API configured (gpt-4o-mini)
✓ Gemini API configured (gemini-1.5-flash)
✓ All containers running
✓ Worker connected and ready
✓ PWA service worker enabled
```

---

## Verification (Critical!)

### 1. Check All Containers Running
```bash
docker ps
```

**Expected containers:**
- studybuddy_app
- studybuddy_worker
- studybuddy_health_monitor ⭐ NEW
- studybuddy_mongo
- studybuddy_rabbitmq
- studybuddy_tunnel

### 2. Test Health Endpoints
```bash
# Simple check
curl http://localhost:5000/health

# Detailed check
curl http://localhost:5000/health/detailed | jq '.'
```

**Expected overall_status:** `"healthy"`

### 3. Check Health Monitor
```bash
docker logs studybuddy_health_monitor --tail 50
```

**Look for:**
```
Starting StudyBuddy Health Monitoring Daemon
Health check interval: 5 minutes
=== Starting periodic health check ===
Health check complete: healthy
```

### 4. Check Worker is Consuming
```bash
docker logs studybuddy_worker --tail 20
```

**Look for:**
```
Worker successfully connected to MongoDB
Worker connected to RabbitMQ
Worker is waiting for messages
```

### 5. Test Email Notifications
```bash
docker exec -it studybuddy_health_monitor python3 << EOF
from health_monitor import send_daily_health_report
send_daily_health_report()
EOF
```

**Check your admin email inbox!**

### 6. Access RabbitMQ Admin (Optional)
```bash
# On server
ssh -L 15672:localhost:15672 user@server

# In browser
http://localhost:15672
# Login: user/password (from .env RABBITMQ_URI)
```

**Verify:**
- All 6 queues exist: file_processing, summarize, flashcards, assess, homework, avner_chat
- At least 1 consumer on each queue

### 7. Test File Upload
```bash
# The health monitor does this automatically every 5 minutes
# Check the logs:
docker logs studybuddy_health_monitor | grep "File upload test"
```

---

## Post-Deployment Configuration

### 1. Configure Cloudflare Tunnel
1. Go to Cloudflare Zero Trust Dashboard
2. Navigate to Access → Tunnels → Your Tunnel
3. Add Public Hostname:
   - **Subdomain**: www (or your choice)
   - **Domain**: yourdomain.com
   - **Service**: HTTP
   - **URL**: studybuddy_app:5000

### 2. Setup Tailscale (Optional - for secure SSH)
```bash
sudo tailscale up
```

### 3. Configure Auto-Start on Boot
```bash
# Already done by deploy-production.sh
sudo systemctl status studybuddy
sudo systemctl enable studybuddy
```

---

## Monitoring Setup

### Daily Email Reports
- **When**: Every day at 8:00 AM
- **To**: ADMIN_EMAIL from .env
- **Contains**: Full health status of all components

### Critical Alerts
- **When**: Component fails 3 times (15 minutes)
- **To**: ADMIN_EMAIL from .env
- **Rate Limited**: Max 1 per hour per component
- **Action Taken**: Automatic service restart

### View Logs Anytime
```bash
# All logs
docker compose logs -f

# Specific service
docker logs studybuddy_health_monitor -f
docker logs studybuddy_worker -f
docker logs studybuddy_app -f

# Last 100 lines
docker logs studybuddy_health_monitor --tail 100
```

---

## Testing Checklist

### Test Each Feature
- [ ] Open http://localhost:5000 (or your domain)
- [ ] Register new user
- [ ] Create a course
- [ ] Upload a file (PDF, DOCX, or TXT)
- [ ] Wait 30 seconds, check if processed
- [ ] Generate summary
- [ ] Generate flashcards
- [ ] Take a quiz
- [ ] Ask Avner a question
- [ ] Check mobile: Open on phone, install as PWA

### Test Auto-Healing
```bash
# Simulate worker failure
docker stop studybuddy_worker

# Wait 15 minutes (3 checks × 5 min)
# Check if worker restarted automatically:
docker ps | grep worker

# Check health monitor logs:
docker logs studybuddy_health_monitor --tail 50

# Check email for critical alert
```

---

## Maintenance

### Daily (Automated)
- ✅ Health monitor checks every 5 minutes
- ✅ Auto-restart on failures
- ✅ Daily email report at 8 AM

### Weekly (Manual - 5 minutes)
```bash
# 1. Check disk space
df -h

# 2. Check Docker resources
docker system df

# 3. Review health status
curl http://localhost:5000/health/detailed | jq '.summary'

# 4. Check for updates
cd /path/to/study_buddy-proj
git fetch
git log --oneline HEAD..origin/main  # See new commits
```

### Monthly (Manual - 15 minutes)
```bash
# 1. Update system packages
sudo apt update && sudo apt upgrade

# 2. Clean Docker
docker system prune -a

# 3. Backup database
docker exec studybuddy_mongo mongodump --out /backup
# Copy backup to safe location

# 4. Review logs for patterns
docker logs studybuddy_health_monitor --since 720h | grep -i error

# 5. Update application if needed
git pull origin main
docker compose up -d --build
```

---

## Troubleshooting

### Problem: Health monitor not sending emails
```bash
# Check email config
docker exec studybuddy_health_monitor python3 -c "
from src.infrastructure.config import settings
print(f'Admin Email: {settings.ADMIN_EMAIL}')
print(f'Mail Server: {settings.MAIL_SERVER}')
"

# Test email manually
docker exec studybuddy_health_monitor python3 -c "
from health_monitor import send_critical_alert
send_critical_alert('test', 'This is a test alert')
"
```

### Problem: Services keep restarting
```bash
# Check what's failing
docker logs studybuddy_health_monitor | grep "attempting restart"

# Check specific service logs
docker logs studybuddy_[service_name]

# Increase failure threshold temporarily
# Edit health_monitor.py:
# MAX_CONSECUTIVE_FAILURES = 5  # Was 3
```

### Problem: Worker not processing tasks
```bash
# Check worker logs
docker logs studybuddy_worker --tail 100

# Check RabbitMQ connection
docker exec studybuddy_worker python3 -c "
import pika
from src.infrastructure.config import settings
conn = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URI))
print('Connected to RabbitMQ successfully')
conn.close()
"

# Restart worker manually
docker restart studybuddy_worker
```

### Problem: AI not working
```bash
# Check AI config
curl http://localhost:5000/health/detailed | jq '.components.ai_models'

# Test AI directly
docker exec studybuddy_app python3 -c "
from src.services.ai_client import AIClient
client = AIClient()
response = client.generate_text('Test', '', provider_override='gemini')
print(f'Response: {response}')
"
```

---

## Emergency Procedures

### Complete System Restart
```bash
# If everything is broken
sudo ./deploy-hard-restart.sh
```

### Rollback to Previous Version
```bash
git log --oneline -10  # Find commit
git checkout [commit-hash]
docker compose up -d --build
```

### Restore from Backup
```bash
# Stop app temporarily
docker compose stop app worker

# Restore database
docker exec studybuddy_mongo mongorestore /backup

# Restart
docker compose start app worker
```

---

## Success Indicators

### System is Healthy When:
✅ All 6 containers running (`docker ps`)
✅ Health endpoint returns "healthy"
✅ Receiving daily email reports
✅ Worker processing tasks (check RabbitMQ admin)
✅ Can upload files and get results
✅ Avner chat responds
✅ No critical alerts for 24+ hours

### System Needs Attention When:
⚠️ Receiving frequent critical alerts
⚠️ Containers restarting often
⚠️ Disk usage > 80%
⚠️ Health status "degraded" for > 1 hour

---

## Support

### Resources
- **Admin Guide**: Read `ADMIN_GUIDE.md` for detailed information
- **PWA Setup**: Read `PWA_IMPLEMENTATION.md` for mobile details
- **Logs**: All logs saved in Docker containers
- **Health Checks**: http://localhost:5000/health/detailed

### Getting Help
1. Check logs first (they tell you everything!)
2. Review ADMIN_GUIDE.md
3. Check email alerts for specific errors
4. Review this deployment checklist

---

## 🎉 Deployment Complete!

Your StudyBuddy application is now:
- ✅ Production-ready
- ✅ Self-healing
- ✅ Monitored 24/7
- ✅ Auto-recovering from failures
- ✅ Sending you daily updates

**The system will take care of itself. Trust the automation!**

📧 Check your email for the first daily health report tomorrow at 8 AM.
