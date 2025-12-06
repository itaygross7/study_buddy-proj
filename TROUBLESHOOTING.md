# StudyBuddy Troubleshooting Guide

This guide helps you diagnose and fix common issues with StudyBuddy.

## Emergency Recovery

### Complete System Reset (When Everything Is Broken)

If you're experiencing multiple issues or the system is in an inconsistent state:

```bash
./deploy-hard-restart.sh
```

This script will:
- Fix all permissions (Git, Docker, files)
- Clean Docker state completely
- Rebuild all services from scratch
- Verify deployment health
- Configure auto-update flow

**Use this when:**
- Auto-update is failing with permission errors
- Docker commands require sudo unexpectedly
- Git operations are blocked
- Multiple deployment attempts have failed
- System is in an unknown state

---

## Quick Diagnosis Tool

Run the configuration checker to identify missing or invalid configurations:

```bash
python check_config.py
```

This will check all your environment variables and test API connections.

---

## Common Issues and Solutions

### 1. Google Sign-In Not Working ❌

**Symptoms:**
- "Google Sign-In not configured" error
- Redirect errors after clicking Google Sign-In button
- "Failed to get info from Google" error

**Solutions:**

#### A. Missing Credentials
1. Check if you have `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in your `.env` file:
   ```bash
   grep "GOOGLE_CLIENT" .env
   ```

2. If missing, get credentials from [Google Cloud Console](https://console.cloud.google.com/):
   - Go to "APIs & Services" > "Credentials"
   - Create OAuth 2.0 Client ID
   - Application type: Web application
   - Add to `.env`:
     ```bash
     GOOGLE_CLIENT_ID="your_client_id.apps.googleusercontent.com"
     GOOGLE_CLIENT_SECRET="your_secret"
     ```

#### B. Incorrect Redirect URI
1. Check your `BASE_URL` in `.env`:
   ```bash
   BASE_URL="https://yourdomain.com"  # Must match your actual domain
   ```

2. In Google Cloud Console, add authorized redirect URI:
   ```
   https://yourdomain.com/oauth/google/callback
   ```
   
   For development:
   ```
   http://localhost:5000/oauth/google/callback
   ```

3. Restart the application:
   ```bash
   docker compose restart app
   # or
   sudo systemctl restart studybuddy
   ```

#### C. Check Logs
View detailed error messages:
```bash
docker compose logs -f app | grep -i "oauth\|google"
```

---

### 2. Email Verification Not Working 📧

**Symptoms:**
- Verification emails not sent
- "Verification link invalid" error
- Emails sent but link doesn't work

**Solutions:**

#### A. SMTP Not Configured
1. Check email configuration:
   ```bash
   python check_config.py
   ```

2. For Gmail, set up App Password:
   - Go to Google Account > Security
   - Enable 2-Step Verification
   - Create App Password
   - Add to `.env`:
     ```bash
     MAIL_SERVER="smtp.gmail.com"
     MAIL_PORT=587
     MAIL_USE_TLS=true
     MAIL_USERNAME="your_email@gmail.com"
     MAIL_PASSWORD="your_app_password"  # 16-character app password
     MAIL_DEFAULT_SENDER="StudyBuddy <your_email@gmail.com>"
     ```

3. Restart:
   ```bash
   docker compose restart app
   ```

#### B. Wrong BASE_URL
Verification links use `BASE_URL` from `.env`:

```bash
# For production
BASE_URL="https://yourdomain.com"

# For development (localhost)
BASE_URL="http://localhost:5000"
```

**Important:** The BASE_URL must match where users access your site!

#### C. Check Email Logs
```bash
docker compose logs -f app | grep -i "email\|smtp\|verification"
```

#### D. Resend Verification Email
Users can request a new verification email from the login page:
1. Go to login page
2. Click "Resend verification email"
3. Enter email address

---

### 3. Cannot Access from Other Devices 🌐

**Symptoms:**
- Works on localhost but not from other computers
- "Connection refused" or timeout from other devices
- Mobile devices cannot connect

**Solutions:**

#### A. Check Flask Binding (Already Fixed)
The app is configured to listen on `0.0.0.0:5000`, which means all network interfaces.

Verify in logs:
```bash
docker compose logs app | grep "Starting StudyBuddy"
```

Should show: `Starting StudyBuddy server on 0.0.0.0:5000`

#### B. Check Firewall
Allow port 5000 (or your port):
```bash
# Ubuntu/Debian
sudo ufw allow 5000/tcp
sudo ufw status

# Check if port is listening
sudo netstat -tlnp | grep 5000
```

#### C. Find Your IP Address
```bash
# Get your local network IP
hostname -I | awk '{print $1}'

# Or
ip addr show | grep "inet " | grep -v 127.0.0.1
```

#### D. Access from Another Device
Use your IP address:
```
http://192.168.1.xxx:5000  # Replace with your actual IP
```

#### E. Docker Network Issues
If using Docker Compose, ensure ports are mapped:
```bash
docker compose ps
# Should show: 0.0.0.0:5000->5000/tcp
```

If ports not mapped, check `docker-compose.yml`:
```yaml
app:
  ports:
    - "5000:5000"  # Host:Container
```

#### F. For Production (HTTPS)
Use the production deployment script:
```bash
./deploy-production.sh
```

This sets up:
- HTTPS with Let's Encrypt
- Proper domain configuration
- Firewall rules
- Accessible from anywhere

---

### 4. Avner Chat Only Says "Hi" 🦫

**Symptoms:**
- Avner only responds with greeting
- No actual answers to questions
- AI responses are generic

**Solutions:**

#### A. Check AI API Keys
```bash
python check_config.py
```

Look for:
```
OPENAI_API_KEY    ✅ SET    sk-...
GEMINI_API_KEY    ✅ SET    AIza...
```

At least ONE must be configured!

#### B. Configure OpenAI or Gemini
Get API keys:

**OpenAI:**
1. Visit https://platform.openai.com/api-keys
2. Create API key
3. Add to `.env`:
   ```bash
   OPENAI_API_KEY="sk-..."
   SB_OPENAI_MODEL="gpt-4o-mini"
   ```

**Gemini (Recommended - Free tier available):**
1. Visit https://makersuite.google.com/app/apikey
2. Create API key
3. Add to `.env`:
   ```bash
   GEMINI_API_KEY="AIza..."
   SB_GEMINI_MODEL="gemini-1.5-flash-latest"
   SB_DEFAULT_PROVIDER="gemini"
   ```

#### C. Restart Application
```bash
docker compose restart app
```

#### D. Test AI Connection
```bash
python check_config.py
```

This will test actual API connections and show if they work.

#### E. Check Logs for AI Errors
```bash
docker compose logs -f app | grep -i "ai\|avner\|openai\|gemini"
```

#### F. Gemini 404 Model Not Found Error

**Symptoms:**
- Error: `404 models/gemini-1.5-flash is not found for API version v1beta`
- Gemini health check fails during deployment
- AI features work with OpenAI but not with Gemini

**Cause:**
The environment variable `SB_GEMINI_MODEL` is set to an older model name without the `-latest` suffix.

**Solution:**
1. Edit your `.env` file:
   ```bash
   nano .env  # or vim, code, etc.
   ```

2. Update the Gemini model setting:
   ```bash
   # ❌ WRONG (old value - will cause 404):
   SB_GEMINI_MODEL="gemini-1.5-flash"
   
   # ✅ CORRECT (use -latest suffix):
   SB_GEMINI_MODEL="gemini-1.5-flash-latest"
   ```

3. Restart the application:
   ```bash
   docker compose restart app worker health_monitor
   ```

4. Verify the fix:
   ```bash
   docker compose logs app | grep -i "gemini"
   ```

**Note:** Google's Gemini API requires the `-latest` suffix for stable model versions. Always use `gemini-1.5-flash-latest` or `gemini-1.5-pro-latest`.

---

### 5. Landing Page Missing Features 🎨

**Symptoms:**
- Landing page looks basic
- Missing requested features
- Outdated content

**Solutions:**

The landing page is in `ui/templates/index.html`. Features shown include:
- Summarizer tool
- Flashcards generator
- Assessment quiz
- Homework helper
- Avner chat
- How it works section

To add new features:
1. Edit `ui/templates/index.html`
2. Add new tool cards in the Tools Grid section
3. Update feature descriptions

For styling changes:
```bash
npm run tailwind:build
```

---

### 6. Permission Issues / Auto-Update Failing 🔒

**Symptoms:**
- "Permission denied" errors when running scripts
- Docker commands require sudo unexpectedly
- Auto-update script fails with permission errors
- Git operations blocked or fail
- Can't write to log directories

**Solutions:**

#### A. Run the Hard Restart Script (Recommended)
This fixes all permission issues automatically:
```bash
./deploy-hard-restart.sh
```

This comprehensive script will:
- Fix Git repository ownership and permissions
- Fix Docker group membership
- Fix all file and script permissions
- Rebuild services cleanly
- Verify everything works

#### B. Manual Docker Permission Fix
If you only need to fix Docker permissions:
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Apply group changes
newgrp docker

# Verify it works
docker ps
```

If still having issues, logout and login again.

#### C. Fix Script Permissions
Make all shell scripts executable:
```bash
find . -type f -name "*.sh" -exec chmod +x {} \;
```

#### D. Fix Git Permissions
```bash
# Set safe directory
git config --global --add safe.directory $(pwd)

# Fix ownership
sudo chown -R $USER:$USER .

# Fix .git permissions
chmod -R u+rwX,go+rX,go-w .git
```

#### E. Fix Log Directory
```bash
sudo mkdir -p /var/log/studybuddy
sudo chown $USER:$USER /var/log/studybuddy
sudo chmod 755 /var/log/studybuddy
```

#### F. Check Auto-Update Logs
If auto-update is failing:
```bash
# Check auto-update log
cat /var/log/studybuddy/auto-update.log

# Run auto-update manually with verbose output
./scripts/auto-update.sh
```

---

### 7. "Cannot Verify" Error After Email Click 🔗

**Symptoms:**
- Click verification link in email
- Get "Invalid verification link" error
- Email was received

**Possible Causes & Solutions:**

#### A. Link Already Used
Verification links work only once. If already verified:
1. Try logging in directly
2. Check if account is already active

#### B. BASE_URL Mismatch
The link in email uses `BASE_URL` from `.env`:

**Problem:** Email sent with old BASE_URL
**Solution:** 
1. Update `BASE_URL` in `.env`
2. Restart app
3. Request new verification email

#### C. Token Expired or Invalid
If token is malformed or too old:
1. Request new verification email from login page
2. Click "Resend verification email"

---

## Health Check Endpoints

Check application status:

```bash
# Basic health check
curl http://localhost:5000/health

# Detailed health check (shows all components)
curl http://localhost:5000/health/detailed

# Ready check
curl http://localhost:5000/health/ready
```

Detailed health check shows status of:
- MongoDB connection
- RabbitMQ connection
- AI service (API keys)
- Email service (SMTP)

---

## Viewing Logs

### Docker Compose Logs
```bash
# All logs
docker compose logs -f

# Just app logs
docker compose logs -f app

# Search for specific errors
docker compose logs app | grep -i error

# OAuth issues
docker compose logs app | grep -i "oauth\|google"

# Email issues
docker compose logs app | grep -i "email\|smtp"

# AI issues
docker compose logs app | grep -i "ai\|openai\|gemini\|avner"
```

### Systemd Logs (if using systemd service)
```bash
# View service logs
sudo journalctl -u studybuddy -f

# Last 100 lines
sudo journalctl -u studybuddy -n 100
```

---

## Configuration File Location

Your configuration is in `.env` file in the project root.

### Creating from Template
```bash
cp .env.example .env
nano .env  # or vim, code, etc.
```

### Required Settings
Minimum required for basic operation:
```bash
# Core
SECRET_KEY="generate-random-secret"  # Auto-generated by deploy script
DOMAIN="yourdomain.com"
BASE_URL="https://yourdomain.com"

# Database (Docker defaults work)
MONGO_URI="mongodb://mongo:27017/studybuddy"

# At least one AI provider
GEMINI_API_KEY="your_key"  # OR
OPENAI_API_KEY="your_key"
```

### Optional but Recommended
```bash
# Email verification
MAIL_USERNAME="your_email@gmail.com"
MAIL_PASSWORD="app_password"

# Google Sign-In
GOOGLE_CLIENT_ID="your_id"
GOOGLE_CLIENT_SECRET="your_secret"

# Admin
ADMIN_EMAIL="admin@example.com"
```

---

## Getting Help

1. **Run diagnostics first:**
   ```bash
   python check_config.py
   ```

2. **Check logs:**
   ```bash
   docker compose logs -f app
   ```

3. **Verify configuration:**
   ```bash
   cat .env | grep -v "^#" | grep -v "^$"
   ```

4. **Test health endpoints:**
   ```bash
   curl http://localhost:5000/health/detailed
   ```

5. **Check GitHub Issues:**
   https://github.com/itaygross7/study_buddy-proj/issues

---

## Quick Fixes Summary

| Issue | Quick Fix |
|-------|-----------|
| System in bad state / Multiple issues | Run `./deploy-hard-restart.sh` to fix everything |
| Permission errors | Run `./deploy-hard-restart.sh` or manually fix Docker group |
| Auto-update failing | Check `/var/log/studybuddy/auto-update.log`, run `./deploy-hard-restart.sh` |
| Google Sign-In | Check `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`, verify redirect URI in Google Console |
| Email verification | Configure SMTP in `.env`, ensure `BASE_URL` is correct |
| Network access | Check firewall: `sudo ufw allow 5000/tcp`, verify binding to `0.0.0.0` |
| Avner chat | Configure `OPENAI_API_KEY` or `GEMINI_API_KEY` in `.env` |
| Any issue | Run `python check_config.py` first! |

---

## Still Having Issues?

1. Run the configuration checker: `python check_config.py`
2. Check the detailed health endpoint: `curl http://localhost:5000/health/detailed`
3. Review logs: `docker compose logs -f app`
4. Check the documentation in `docs/` folder
5. Open an issue on GitHub with:
   - Output of `python check_config.py`
   - Relevant log snippets (remove sensitive data!)
   - Steps to reproduce the issue
