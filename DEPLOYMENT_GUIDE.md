# 🚀 Ultimate Production Deployment Script

## Overview

The `deploy-production.sh` script is your **complete DevOps team in one script**. It handles everything from code updates to security hardening, monitoring, and automatic rollback - all with professional-grade reliability and comprehensive logging.

## 🌟 Features

### Core Deployment
- ✅ **Automated Git Updates** - Pulls latest code with smart conflict resolution
- ✅ **Zero-Downtime Deployment** - Graceful container transitions
- ✅ **Docker Orchestration** - Automatic build, pull, and container management
- ✅ **Environment Validation** - Comprehensive checks before deployment

### Backup & Recovery
- 📦 **Automatic Backups** - Creates full backup before each deployment
- 🔄 **Smart Rollback** - Automatic rollback on failure with MongoDB restore
- 💾 **MongoDB Backup** - Database snapshots with compression
- 📜 **Git State Tracking** - Commit tracking for precise rollbacks
- 🗂️ **Retention Policy** - Keeps last 5 backups automatically

### Health & Monitoring
- 🏥 **Comprehensive Health Checks** - Tests all services and endpoints
- 📊 **Real-time Monitoring** - Container resource usage tracking
- 🔍 **Detailed Diagnostics** - Multi-level health verification
- ⏱️ **Retry Logic** - Smart waiting with configurable timeouts
- 📧 **Email Notifications** - Alerts on deployment status

### Security
- 🔒 **Firewall Configuration** - UFW setup in Zero Trust mode
- 🛡️ **Fail2ban Integration** - SSH brute-force protection
- 🔐 **Secure Permissions** - Automatic file permission hardening
- 🚪 **Minimal Attack Surface** - Only required ports exposed

### Performance
- ⚡ **Docker Optimization** - Tuned logging, storage, and limits
- 🚀 **System Tuning** - Network and resource optimization
- 🧹 **Automatic Cleanup** - Removes unused Docker resources
- 📈 **Resource Limits** - Proper container constraints

### Reliability
- 🔁 **Systemd Integration** - Auto-restart on failure
- 🩺 **Health Monitoring Service** - Continuous system monitoring
- 📝 **Comprehensive Logging** - Detailed logs for every operation
- 🎯 **Error Handling** - Graceful failure recovery

### Developer Experience
- 🎨 **Beautiful UI** - Color-coded output and progress bars
- 📊 **Deployment Reports** - Detailed post-deployment summaries
- 🔔 **Status Notifications** - Real-time deployment updates
- 📄 **Documentation** - Clear error messages and next steps

## 📋 Prerequisites

- **Operating System**: Ubuntu 20.04+ or Debian 11+
- **Permissions**: Must be run with `sudo`
- **Disk Space**: At least 5GB free
- **Memory**: 2GB+ recommended
- **Network**: Internet connection for pulling updates

## 🚀 Quick Start

### First Time Setup

```bash
# Clone the repository
git clone https://github.com/itaygross7/study_buddy-proj.git
cd study_buddy-proj

# Configure environment
cp .env.example .env
nano .env  # Edit with your configuration

# Run deployment
sudo ./deploy-production.sh
```

### Regular Deployments

```bash
cd /path/to/study_buddy-proj
sudo ./deploy-production.sh
```

That's it! The script handles everything else.

## 📁 Directory Structure

After deployment, you'll have:

```
study_buddy-proj/
├── backups/              # Automatic backups
│   ├── backup_20231206_123456/
│   ├── backup_20231207_091234/
│   └── ...
├── logs/                 # Deployment logs
│   ├── deploy_20231206_123456.log
│   ├── deployment_report_20231206_123456.txt
│   └── ...
├── deploy-production.sh  # This ultimate script
└── ... (application files)
```

## 🔧 Configuration

### Required Environment Variables

Edit `.env` with these required variables:

```bash
# Infrastructure
MONGO_URI=mongodb://mongo:27017/studybuddy
RABBITMQ_URI=amqp://guest:guest@rabbitmq:5672
SECRET_KEY=your-super-secret-key-change-this

# AI Services (at least one required)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AI...

# Optional: Email Notifications
ADMIN_EMAIL=admin@example.com
MAIL_USERNAME=smtp@example.com
MAIL_PASSWORD=your-mail-password
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587

# Optional: Cloudflare Tunnel
TUNNEL_TOKEN=your-cloudflare-tunnel-token
```

### Optional Configuration

```bash
# Flask Configuration
FLASK_ENV=production
DEBUG=False

# AI Model Selection
SB_DEFAULT_PROVIDER=gemini
SB_OPENAI_MODEL=gpt-4o-mini
SB_GEMINI_MODEL=gemini-1.5-flash-latest
```

## 📊 Deployment Steps

The script performs these steps automatically:

1. **Pre-flight Checks** - Validates system requirements
2. **Dependency Installation** - Installs/updates Docker, tools
3. **Backup Creation** - Full system backup including database
4. **Code Update** - Pulls latest from Git
5. **Environment Validation** - Checks all configuration
6. **Security Hardening** - Firewall, fail2ban, permissions
7. **Build & Deploy** - Docker build and container orchestration
8. **Health Checks** - Comprehensive service verification
9. **Systemd Configuration** - Auto-restart setup
10. **Performance Optimization** - System and Docker tuning
11. **Monitoring Setup** - Health monitoring service
12. **Post-Deployment Verification** - Final checks and reporting

## 🔄 Automatic Rollback

If deployment fails, the script automatically:

1. Stops failed containers
2. Restores previous .env configuration
3. Rolls back Git to previous commit
4. Restores MongoDB from backup
5. Starts containers with previous version
6. Verifies rollback success
7. Sends notification

## 📧 Email Notifications

When email is configured, you receive notifications for:

- ✅ Deployment started
- ✅ Deployment completed successfully
- ❌ Deployment failed (with error details)
- ↩️ Automatic rollback performed
- ⚠️ Health check warnings

## 🏥 Health Monitoring

The script sets up continuous health monitoring:

### Monitored Services
- Application (Flask app)
- Worker (Celery worker)
- MongoDB database
- RabbitMQ message broker
- Cloudflare Tunnel

### Health Endpoints
- `http://localhost:5000/health` - Quick health check
- `http://localhost:5000/health/detailed` - Comprehensive diagnostics

### Automatic Actions
- Container restart on failures
- Email alerts on critical issues
- Resource usage tracking
- Automatic recovery attempts

## 📝 Logs & Reports

### Deployment Logs
Located in `logs/deploy_YYYYMMDD_HHMMSS.log`

Contains:
- Timestamp for each operation
- Detailed command output
- Error messages and stack traces
- Health check results

### Deployment Reports
Located in `logs/deployment_report_YYYYMMDD_HHMMSS.txt`

Includes:
- System information
- Container status
- Git information
- Configuration summary
- Health check results
- Next steps

## 🐛 Troubleshooting

### Deployment Failed

1. **Check the deployment log:**
   ```bash
   cat logs/deploy_$(date +%Y%m%d)_*.log
   ```

2. **View container logs:**
   ```bash
   docker compose logs app
   docker compose logs worker
   ```

3. **Manual rollback (if auto-rollback failed):**
   ```bash
   cd backups/backup_YYYYMMDD_HHMMSS
   cp .env ../../.env
   git reset --hard $(cat commit.txt)
   docker compose up -d
   ```

### Health Check Failures

```bash
# Check detailed health
curl http://localhost:5000/health/detailed | jq

# Check specific container
docker logs studybuddy_app --tail=100

# Restart specific service
docker compose restart app
```

### Email Notifications Not Working

1. Verify email configuration in `.env`
2. Test email manually:
   ```bash
   python3 << EOF
   from src.services.email_service import send_email
   send_email('your@email.com', 'Test', 'Test message')
   EOF
   ```

## 🔒 Security Best Practices

The script implements:

- **Zero Trust Networking** - Only required ports open
- **Firewall Rules** - UFW configured automatically
- **Fail2ban** - SSH brute-force protection
- **Secure Permissions** - .env and sensitive files protected
- **Log Rotation** - Prevents log files from filling disk
- **Container Isolation** - Network segmentation
- **Secret Management** - Environment variable isolation

## 🚀 Advanced Usage

### Manual Backup

```bash
# Run only backup step
cd /path/to/study_buddy-proj
sudo -u $USER ./scripts/backup.sh
```

### Force Rebuild

```bash
# Rebuild containers from scratch
docker compose down
docker compose build --no-cache
docker compose up -d
```

### View Real-time Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f app
docker compose logs -f worker
```

### Resource Monitoring

```bash
# Container stats
docker stats

# System resources
htop
df -h
free -h
```

## 📚 Additional Resources

- **Main Documentation**: [README.md](../README.md)
- **Getting Started**: [GETTING_STARTED.md](../GETTING_STARTED.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
- **Admin Guide**: [ADMIN_GUIDE.md](../ADMIN_GUIDE.md)

## 🆘 Support

If you encounter issues:

1. Check the deployment log file
2. Review container logs
3. Verify .env configuration
4. Check system resources
5. Open an issue on GitHub

## 📜 License

This script is part of the StudyBuddy AI project.
See [LICENSE](../LICENSE) for details.

---

**Made with ❤️ by the StudyBuddy team**

*Your complete DevOps team in one script* 🚀
