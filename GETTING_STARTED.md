# Getting Started with StudyBuddy

Welcome to StudyBuddy! This guide will help you get up and running quickly.

## 📋 Prerequisites

- Linux server (Ubuntu 22.04 recommended)
- Docker and Docker Compose (can be installed automatically)
- At least 2GB free disk space
- At least one AI API key (OpenAI or Gemini)

---

## 🚀 Quick Start (Choose Your Path)

### Path 1: Local Network Access (Recommended for Testing)

**Best for:** Testing at home, access from phone/tablet on same WiFi

```bash
# 1. Clone the repository
git clone https://github.com/itaygross7/study_buddy-proj.git
cd study_buddy-proj

# 2. Run the local network startup script
./start-local.sh

# 3. Access the app
# From server: http://localhost:5000
# From other devices: http://YOUR_IP:5000 (shown by script)
```

**What this does:**
- ✅ Creates `.env` from template
- ✅ Generates secure SECRET_KEY
- ✅ Starts all services (except Caddy - no HTTPS needed)
- ✅ Opens firewall port 5000
- ✅ Shows your IP address for network access

**Perfect for:**
- 🏠 Home testing
- 📱 Mobile device access
- 👨‍👩‍👧‍👦 Demo to friends/family
- 💻 Development

📖 **Full guide:** [Local Network Access](docs/LOCAL_NETWORK_ACCESS.md)

---

### Path 2: Production Deployment with HTTPS

**Best for:** Production servers with a domain name

```bash
# 1. Clone the repository
git clone https://github.com/itaygross7/study_buddy-proj.git
cd study_buddy-proj

# 2. Configure your domain and API keys
cp .env.example .env
nano .env  # Edit: DOMAIN, BASE_URL, API keys

# 3. Run production deployment
./deploy-production.sh
```

**What this does:**
- ✅ Installs Docker & Docker Compose
- ✅ Sets up HTTPS with Let's Encrypt
- ✅ Installs Tailscale for secure SSH
- ✅ Configures firewall
- ✅ Creates systemd service (auto-restart)
- ✅ Sets up auto-updates

**Requirements:**
- Domain name (e.g., studybuddyai.my)
- DNS pointing to your server
- Ports 80/443 accessible

📖 **Full guide:** [Production Deployment](docs/DEPLOYMENT.md)

---

### Path 3: Simple Test (No Configuration)

**Best for:** Quick testing, exploration

```bash
# 1. Clone the repository
git clone https://github.com/itaygross7/study_buddy-proj.git
cd study_buddy-proj

# 2. Run simple deployment
./deploy-simple.sh

# 3. Configure when prompted
# Add at least one AI API key to .env
```

**Note:** This starts all services including Caddy. If you see Caddy errors about SSL certificates, you should use Path 1 (local network) instead.

---

## ⚙️ Configuration

### Required Configuration

You need at least ONE AI provider configured:

#### Option A: Google Gemini (Recommended - Free Tier Available!)

```bash
# Get API key from: https://makersuite.google.com/app/apikey
# Add to .env:
GEMINI_API_KEY="AIza..."
SB_DEFAULT_PROVIDER="gemini"
```

#### Option B: OpenAI

```bash
# Get API key from: https://platform.openai.com/api-keys
# Add to .env:
OPENAI_API_KEY="sk-..."
```

### Optional Configuration

#### Email Verification (Recommended)

```bash
# For Gmail - get app password from Google Account settings
MAIL_SERVER="smtp.gmail.com"
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME="your_email@gmail.com"
MAIL_PASSWORD="your_16_char_app_password"
MAIL_DEFAULT_SENDER="StudyBuddy <your_email@gmail.com>"
```

📖 **Full guide:** [OAuth & Email Setup](docs/OAUTH_EMAIL_SETUP.md)

#### Google Sign-In (Recommended)

```bash
# Get credentials from: https://console.cloud.google.com/
# Add to .env:
GOOGLE_CLIENT_ID="your_client_id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="your_secret"
```

📖 **Full guide:** [OAuth & Email Setup](docs/OAUTH_EMAIL_SETUP.md)

---

## 🔍 Verify Installation

### Check Health

```bash
# Basic health check
curl http://localhost:5000/health

# Detailed health check (shows all components)
curl http://localhost:5000/health/detailed
```

### Check Services

```bash
# List running containers
docker compose ps

# View app logs
docker compose logs -f app

# View all logs
docker compose logs -f
```

### Test Access

1. **From the server:** Open browser to `http://localhost:5000`
2. **From another device:** Open browser to `http://YOUR_IP:5000`
3. **Production:** Open browser to `https://yourdomain.com`

---

## 📱 Accessing from Other Devices

### Find Your Server IP

```bash
# Get your local IP address
hostname -I | awk '{print $1}'
```

### Open Firewall (If Needed)

```bash
# Automatic
./scripts/enable-network-access.sh

# Manual (Ubuntu/Debian)
sudo ufw allow 5000/tcp

# Manual (CentOS/RHEL/Fedora)
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

### Access from Another Device

1. Connect to same WiFi network
2. Open browser
3. Go to: `http://YOUR_IP:5000`

📖 **Troubleshooting:** [Local Network Access](docs/LOCAL_NETWORK_ACCESS.md)

---

## 🛠️ Common Operations

### Restart the Application

```bash
# Restart just the app
docker compose restart app

# Restart all services
docker compose restart

# Using helper script
./scripts/restart-app.sh
```

### Stop the Application

```bash
# Stop all services
docker compose down

# Stop but keep data
docker compose stop
```

### View Logs

```bash
# App logs
docker compose logs -f app

# All logs
docker compose logs -f

# Last 100 lines
docker compose logs --tail=100 app
```

### Update Configuration

```bash
# 1. Edit .env
nano .env

# 2. Restart app
docker compose restart app
```

---

## 🐛 Troubleshooting

### "Can't connect from another device"

**Solution:** Open firewall port 5000
```bash
./scripts/enable-network-access.sh
```

📖 [Network Troubleshooting](docs/NETWORK_ACCESS.md)

### "Caddy SSL certificate errors"

**Problem:** Caddy trying to get certificate without valid domain

**Solution:** Use local network mode instead
```bash
docker compose down
./start-local.sh
```

📖 [Local Network Access](docs/LOCAL_NETWORK_ACCESS.md)

### "Avner only says 'Hi'"

**Problem:** No AI API key configured

**Solution:** Configure at least one AI provider in `.env`
```bash
# Add to .env:
GEMINI_API_KEY="your_key"
# OR
OPENAI_API_KEY="your_key"

# Restart
docker compose restart app
```

### "Email verification not working"

**Problem:** SMTP not configured

**Solution:** Configure email in `.env`

📖 [OAuth & Email Setup](docs/OAUTH_EMAIL_SETUP.md)

### "Google Sign-In not working"

**Problem:** OAuth not configured

**Solution:** Set up OAuth credentials

📖 [OAuth & Email Setup](docs/OAUTH_EMAIL_SETUP.md)

### Check Configuration

```bash
# Run configuration checker
python check_config.py
```

### More Help

📖 **See:** [Troubleshooting Guide](TROUBLESHOOTING.md)

---

## 📚 Next Steps

### For Local Testing
1. ✅ App is running
2. Configure OAuth (optional): [OAuth & Email Setup](docs/OAUTH_EMAIL_SETUP.md)
3. Access from devices: [Local Network Access](docs/LOCAL_NETWORK_ACCESS.md)
4. Test features and have fun! 🎉

### For Production
1. ✅ App is running on HTTPS
2. Configure OAuth & Email: [OAuth & Email Setup](docs/OAUTH_EMAIL_SETUP.md)
3. Set up monitoring: [Health & Monitoring](docs/HEALTH_AND_MONITORING.md)
4. Configure auto-updates: See `deploy-production.sh` output
5. Go live! 🚀

---

## 📖 Additional Resources

### Documentation
- 📚 [Documentation Index](docs/INDEX.md) - Complete doc navigation
- 🔧 [Troubleshooting](TROUBLESHOOTING.md) - Fix common issues
- 📜 [Scripts Guide](SCRIPTS_GUIDE.md) - All available scripts
- 🏗️ [Architecture](docs/app_map.md) - System overview

### Guides
- 🌐 [Local Network Access](docs/LOCAL_NETWORK_ACCESS.md)
- 🚀 [Production Deployment](docs/DEPLOYMENT.md)
- 🔒 [OAuth & Email Setup](docs/OAUTH_EMAIL_SETUP.md)
- 🏥 [Health & Monitoring](docs/HEALTH_AND_MONITORING.md)

### Quick Reference
- 📋 [Command Reference](docs/QUICK_REFERENCE.md)
- 🆘 [Quick Network Fix](docs/QUICK_FIX_NETWORK.md)

---

## 💡 Tips

1. **Start simple:** Use `./start-local.sh` for testing
2. **Test locally first:** Make sure everything works before deploying to production
3. **Check logs:** If something doesn't work, check `docker compose logs -f app`
4. **Use the docs:** We have comprehensive guides for everything
5. **Run health checks:** Use `curl http://localhost:5000/health/detailed`

---

## 🎉 You're Ready!

Your StudyBuddy instance is now running. Open your browser and start exploring!

- 🏠 **Local access:** http://localhost:5000
- 🌐 **Network access:** http://YOUR_IP:5000
- 🚀 **Production:** https://yourdomain.com

Need help? Check [Troubleshooting](TROUBLESHOOTING.md) or [Documentation Index](docs/INDEX.md).
