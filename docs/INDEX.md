# 📚 StudyBuddy Documentation Index

Welcome to the StudyBuddy documentation! This index will help you find exactly what you need.

## 🚀 Quick Start - Start Here!

| I want to... | Read this | Run this |
|--------------|-----------|----------|
| **Access app from my phone/tablet** | [Local Network Access](#-local-network--testing) | `./start-local.sh` |
| **Deploy to production with HTTPS** | [Production Deployment](#-production-deployment) | `./deploy-production.sh` |
| **Quickly test the app** | [Getting Started](../GETTING_STARTED.md) | `./deploy-simple.sh` |
| **Fix connection issues** | [Troubleshooting](#-troubleshooting) | `./scripts/enable-network-access.sh` |

---

## 📖 Documentation by Category

### 🏠 Essential Guides (Start Here)

**[README.md](../README.md)** - Main overview
- What is StudyBuddy
- Feature overview
- Tech stack
- Quick links

**[GETTING_STARTED.md](../GETTING_STARTED.md)** - Your first steps
- Installation
- Basic configuration
- First deployment
- Common use cases

**[TROUBLESHOOTING.md](../TROUBLESHOOTING.md)** - Fix common problems
- Connection issues
- Configuration problems
- OAuth/email issues
- AI service problems

**[SCRIPTS_GUIDE.md](../SCRIPTS_GUIDE.md)** - Which script to use
- All available scripts
- When to use each one
- Current vs deprecated

---

### 🌐 Local Network & Testing

**[LOCAL_NETWORK_ACCESS.md](LOCAL_NETWORK_ACCESS.md)** - ⭐ NEW! Access from other devices
- How to access from phone/tablet
- Understanding Caddy/HTTPS issues
- Local vs production setup
- Firewall configuration
- Troubleshooting connection issues

**[NETWORK_ACCESS.md](NETWORK_ACCESS.md)** - Network troubleshooting
- Development vs production modes
- Firewall configuration (UFW, firewalld, iptables)
- Finding your IP address
- Security considerations

**[QUICK_FIX_NETWORK.md](QUICK_FIX_NETWORK.md)** - Quick network fixes
- 3-step quick fix
- Manual firewall commands
- Testing connectivity

---

### 🚀 Production Deployment

**[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide
- Production deployment with `deploy-production.sh`
- HTTPS setup with Let's Encrypt
- Tailscale configuration
- Systemd service setup
- Auto-updates configuration

**[OAUTH_EMAIL_SETUP.md](OAUTH_EMAIL_SETUP.md)** - OAuth & Email configuration
- Google Sign-In setup
- Apple Sign-In setup
- Email verification setup
- SMTP configuration (Gmail)
- Troubleshooting OAuth issues

---

### 🏗️ Architecture & Monitoring

**[HEALTH_AND_MONITORING.md](HEALTH_AND_MONITORING.md)** - Health check system
- Health check endpoints
- Monitoring setup
- Health monitor script
- Container health checks

**[MONITORING_ARCHITECTURE.md](MONITORING_ARCHITECTURE.md)** - Monitoring architecture
- System design
- Component overview
- Integration points

**[app_map.md](app_map.md)** - Application structure
- Directory structure
- Component overview
- File organization

---

### 🔧 Reference & Commands

**[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Command reference
- Docker commands
- Debugging commands
- Log viewing
- Service management

---

## 🎯 Documentation by Use Case

### "I want to test StudyBuddy on my local network"

1. Read: [LOCAL_NETWORK_ACCESS.md](LOCAL_NETWORK_ACCESS.md)
2. Run: `./start-local.sh`
3. Access from phone: `http://YOUR_IP:5000`
4. If issues: [QUICK_FIX_NETWORK.md](QUICK_FIX_NETWORK.md)

### "I want to deploy StudyBuddy to production"

1. Read: [DEPLOYMENT.md](DEPLOYMENT.md)
2. Configure: Edit `.env` with your domain and API keys
3. Run: `./deploy-production.sh`
4. Setup OAuth: [OAUTH_EMAIL_SETUP.md](OAUTH_EMAIL_SETUP.md)
5. If issues: [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)

### "I'm getting Caddy/HTTPS errors"

**Problem:** Caddy trying to get SSL certificate for "https" domain

**Solution:** You're trying to use HTTPS without a domain. Choose one:
- **Option 1 (Recommended):** Use local setup → [LOCAL_NETWORK_ACCESS.md](LOCAL_NETWORK_ACCESS.md)
- **Option 2:** Set proper domain in `.env` → [DEPLOYMENT.md](DEPLOYMENT.md)

### "I can't access from another device"

1. Check: [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - "Cannot Access from Other Devices"
2. Run: `./scripts/enable-network-access.sh`
3. Read: [NETWORK_ACCESS.md](NETWORK_ACCESS.md)
4. Or use: [LOCAL_NETWORK_ACCESS.md](LOCAL_NETWORK_ACCESS.md) for complete guide

### "I want to configure OAuth/Email"

1. Read: [OAUTH_EMAIL_SETUP.md](OAUTH_EMAIL_SETUP.md)
2. For troubleshooting: [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - OAuth/Email sections

### "I need to understand the system architecture"

1. Start: [app_map.md](app_map.md) - High-level structure
2. Health: [HEALTH_AND_MONITORING.md](HEALTH_AND_MONITORING.md)
3. Monitoring: [MONITORING_ARCHITECTURE.md](MONITORING_ARCHITECTURE.md)

---

## 🗂️ All Documentation Files

### Root Directory
- 📄 [README.md](../README.md) - Main overview
- 📄 [GETTING_STARTED.md](../GETTING_STARTED.md) - Quick start
- 📄 [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - Problem solving
- 📄 [SCRIPTS_GUIDE.md](../SCRIPTS_GUIDE.md) - Script reference
- 📄 [CLEANUP_PLAN.md](../CLEANUP_PLAN.md) - Project organization plan

### docs/ Directory (Current Files)
- 📄 [INDEX.md](INDEX.md) - This file!
- 📄 [LOCAL_NETWORK_ACCESS.md](LOCAL_NETWORK_ACCESS.md) - ⭐ NEW! Local network guide
- 📄 [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment
- 📄 [OAUTH_EMAIL_SETUP.md](OAUTH_EMAIL_SETUP.md) - OAuth & email
- 📄 [NETWORK_ACCESS.md](NETWORK_ACCESS.md) - Network troubleshooting
- 📄 [QUICK_FIX_NETWORK.md](QUICK_FIX_NETWORK.md) - Quick fixes
- 📄 [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Command reference
- 📄 [HEALTH_AND_MONITORING.md](HEALTH_AND_MONITORING.md) - Health checks
- 📄 [MONITORING_ARCHITECTURE.md](MONITORING_ARCHITECTURE.md) - Monitoring
- 📄 [app_map.md](app_map.md) - App structure

### Deprecated/Archived (Not Recommended)
- ⚠️ DEPLOYMENT_OLD.md - Outdated, use DEPLOYMENT.md
- ⚠️ DEPLOYMENT_IMPLEMENTATION.md - Internal notes
- ⚠️ DEPLOYMENT_SCRIPTS.md - Use SCRIPTS_GUIDE.md
- ⚠️ NEW_FEATURES.md - Outdated
- ⚠️ Various internal checklists and notes

---

## 🔍 Search by Topic

### Configuration
- Basic setup → [GETTING_STARTED.md](../GETTING_STARTED.md)
- OAuth/Email → [OAUTH_EMAIL_SETUP.md](OAUTH_EMAIL_SETUP.md)
- Network → [LOCAL_NETWORK_ACCESS.md](LOCAL_NETWORK_ACCESS.md)

### Deployment
- Local/Testing → [LOCAL_NETWORK_ACCESS.md](LOCAL_NETWORK_ACCESS.md) + `./start-local.sh`
- Production → [DEPLOYMENT.md](DEPLOYMENT.md) + `./deploy-production.sh`
- Simple → [GETTING_STARTED.md](../GETTING_STARTED.md) + `./deploy-simple.sh`

### Troubleshooting
- Network issues → [NETWORK_ACCESS.md](NETWORK_ACCESS.md)
- General issues → [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
- Quick fixes → [QUICK_FIX_NETWORK.md](QUICK_FIX_NETWORK.md)

### Scripts
- Which to use → [SCRIPTS_GUIDE.md](../SCRIPTS_GUIDE.md)
- Network access → `./scripts/enable-network-access.sh`
- Testing → `./scripts/test-api-endpoints.sh`

### Monitoring
- Health checks → [HEALTH_AND_MONITORING.md](HEALTH_AND_MONITORING.md)
- Architecture → [MONITORING_ARCHITECTURE.md](MONITORING_ARCHITECTURE.md)

---

## 📞 Getting Help

### Step 1: Check Documentation
Start with this index to find relevant guides.

### Step 2: Run Diagnostics
```bash
# Check configuration
python check_config.py

# Check health
curl http://localhost:5000/health/detailed

# View logs
docker compose logs -f app
```

### Step 3: Check Troubleshooting
See [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) for common issues.

### Step 4: GitHub Issues
If still stuck, check [GitHub Issues](https://github.com/itaygross7/study_buddy-proj/issues)

---

## 🎉 Quick Wins

### Fastest way to get started (5 minutes)
```bash
git clone https://github.com/itaygross7/study_buddy-proj.git
cd study_buddy-proj
./start-local.sh
# Access at http://localhost:5000
```

### Access from your phone (2 minutes)
```bash
./start-local.sh
# Shows your IP - access from phone at http://YOUR_IP:5000
```

### Deploy to production (15 minutes)
```bash
# Edit .env with your domain and API keys
nano .env

# Deploy
./deploy-production.sh
```

---

## 📝 Documentation Updates

This documentation index was created as part of project cleanup.
See [CLEANUP_PLAN.md](../CLEANUP_PLAN.md) for the complete organization plan.

**Last Updated:** December 2024
**Current Version:** Cleanup Phase 1
