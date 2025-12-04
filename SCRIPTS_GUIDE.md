# StudyBuddy Scripts Guide

This guide documents all scripts in the project and their current status.

## 📋 Quick Reference

### Current & Recommended Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| **start-local.sh** ⭐ | Start for local network access | Testing on home network, access from phone/tablet |
| **deploy-production.sh** ⭐ | Full production deployment | Production servers with domain and HTTPS |
| **deploy-simple.sh** ⭐ | Simple one-click deployment | Quick testing, development |
| **scripts/enable-network-access.sh** | Fix firewall for network access | When other devices can't connect |

### Utility Scripts (Keep)

| Script | Purpose | Status |
|--------|---------|--------|
| setup_env.sh | Environment setup | ✅ Active |
| scripts/restart-app.sh | Restart application | ✅ Active |
| scripts/health-monitor.sh | Health monitoring | ✅ Active |
| scripts/test-api-endpoints.sh | API testing | ✅ Active |
| scripts/auto-update.sh | Auto-update system | ✅ Active |
| scripts/setup-dns-updater.sh | DNS updater setup | ✅ Active |
| scripts/update_dns.sh | Update dynamic DNS | ✅ Active |
| scripts/pre-deploy-check.sh | Pre-deployment validation | ✅ Active |

### Deprecated/Redundant Scripts

| Script | Status | Replacement |
|--------|--------|-------------|
| deploy.sh | ⚠️ Complex/outdated | Use **deploy-simple.sh** or **deploy-production.sh** |
| deploy-auto-fix.sh | ⚠️ Redundant | Use **deploy-simple.sh** instead |
| deploy-check-only.sh | ⚠️ Rarely used | Use **deploy-simple.sh** or check manually |

---

## 🚀 Deployment Scripts (Root Directory)

### ⭐ start-local.sh (NEW - Recommended)

**Purpose:** Start StudyBuddy for local network access without Caddy/HTTPS

**When to use:**
- Testing on home/office network
- Access from phones, tablets, other computers
- Development without domain configuration

**What it does:**
- Starts all services except Caddy (no HTTPS)
- Opens firewall port 5000 automatically
- Shows IP address for network access
- Fast startup, minimal configuration

**Usage:**
```bash
./start-local.sh
```

**Access:**
- From server: `http://localhost:5000`
- From network: `http://YOUR_IP:5000`

---

### ⭐ deploy-production.sh (Recommended)

**Purpose:** Complete production deployment with HTTPS, Tailscale, and auto-updates

**When to use:**
- Production servers with domain name
- Public-facing deployments
- When you need HTTPS/SSL

**What it does:**
- Installs Docker & Docker Compose
- Sets up Tailscale for secure SSH
- Configures HTTPS with Let's Encrypt
- Creates systemd service
- Sets up auto-updates
- Configures firewall properly

**Usage:**
```bash
# Edit .env first with your domain
nano .env

# Run deployment
./deploy-production.sh
```

**Requirements:**
- Domain name (e.g., studybuddyai.my)
- DNS pointing to server
- Ports 80/443 accessible

---

### ⭐ deploy-simple.sh (Recommended)

**Purpose:** Quick one-click deployment for testing/development

**When to use:**
- Quick testing
- Development environment
- When you want to get started fast

**What it does:**
- Minimal checks
- Creates .env from template
- Builds and starts all services
- Shows access information

**Usage:**
```bash
./deploy-simple.sh
```

**Note:** This starts ALL services including Caddy. For local network access without Caddy errors, use **start-local.sh** instead.

---

### ⚠️ deploy.sh (Outdated - Not Recommended)

**Status:** Complex, outdated, many edge cases

**Issues:**
- 40KB file, overly complex
- Tries to fix too many things automatically
- Hard to maintain
- Confusing for users

**Replacement:**
- For simple deployment → Use **deploy-simple.sh**
- For production → Use **deploy-production.sh**
- For local network → Use **start-local.sh**

**Recommendation:** Consider deprecating or simplifying significantly

---

### ⚠️ deploy-auto-fix.sh (Redundant)

**Status:** Redundant with deploy-simple.sh

**Issues:**
- Similar functionality to deploy-simple.sh
- Confusing to have multiple deploy scripts
- Not clear when to use this vs others

**Replacement:** Use **deploy-simple.sh**

**Recommendation:** Remove or merge with deploy-simple.sh

---

### ⚠️ deploy-check-only.sh (Rarely Used)

**Status:** Useful but rarely needed

**Purpose:** Check if deployment is possible without actually deploying

**When to use:** Rarely - most users just want to deploy

**Recommendation:** Keep for now, but document as advanced usage

---

### ✅ setup_env.sh (Keep)

**Purpose:** Interactive environment setup helper

**Status:** Active and useful

**When to use:**
- First-time setup
- When adding new environment variables
- Interactive configuration

---

## 📁 Utility Scripts (scripts/ directory)

### ✅ enable-network-access.sh (Keep)

**Purpose:** Fix firewall to allow network access on port 5000

**When to use:**
- Can't access app from other devices
- After deployment, network access fails

**What it does:**
- Detects firewall type (UFW, firewalld, iptables)
- Opens port 5000
- Verifies configuration
- Shows access instructions

**Usage:**
```bash
./scripts/enable-network-access.sh
```

---

### ✅ restart-app.sh (Keep)

**Purpose:** Safely restart the application

**Usage:**
```bash
./scripts/restart-app.sh
```

---

### ✅ health-monitor.sh (Keep)

**Purpose:** Continuous health monitoring

**What it does:**
- Checks app health periodically
- Sends alerts on failures
- Can auto-restart on failure

**Usage:** Runs automatically in Docker or can be run manually

---

### ✅ test-api-endpoints.sh (Keep)

**Purpose:** Test all API endpoints

**When to use:**
- After deployment
- Testing changes
- Debugging issues

**Usage:**
```bash
./scripts/test-api-endpoints.sh
```

---

### ✅ auto-update.sh (Keep)

**Purpose:** Automatic updates from GitHub

**When to use:** Set up by deploy-production.sh for auto-updates

---

### ✅ setup-dns-updater.sh (Keep)

**Purpose:** Set up dynamic DNS updates

**When to use:** If using dynamic IP address for production

---

### ✅ update_dns.sh (Keep)

**Purpose:** Update DNS records

**Usage:** Called by DNS updater, rarely manual

---

### ✅ pre-deploy-check.sh (Keep)

**Purpose:** Pre-deployment validation

**What it does:**
- Checks system requirements
- Validates configuration
- Warns about issues

**Usage:**
```bash
./scripts/pre-deploy-check.sh
```

---

## 🧹 Cleanup Recommendations

### High Priority - Remove/Consolidate

1. **deploy.sh** - Too complex, hard to maintain
   - Option A: Remove entirely, update docs to use deploy-simple.sh or deploy-production.sh
   - Option B: Simplify drastically to match deploy-simple.sh

2. **deploy-auto-fix.sh** - Redundant with deploy-simple.sh
   - Action: Remove and redirect users to deploy-simple.sh

3. **deploy-check-only.sh** - Rarely used
   - Option A: Remove if usage is minimal
   - Option B: Keep but mark as advanced/optional

### Medium Priority - Improve Documentation

4. Update README.md to clearly show:
   - **Local network → start-local.sh**
   - **Production → deploy-production.sh**
   - **Quick test → deploy-simple.sh**

5. Add deprecation notices to outdated scripts

### Low Priority - Nice to Have

6. Add consistent help flags to all scripts:
   ```bash
   ./script.sh --help
   ```

7. Add consistent logging/output format

8. Consider single entry point:
   ```bash
   ./studybuddy.sh local    # Local network
   ./studybuddy.sh prod     # Production
   ./studybuddy.sh simple   # Simple deploy
   ```

---

## 📖 For Users: Which Script Should I Use?

### I want to access from my phone on the same WiFi
```bash
./start-local.sh
```

### I want to deploy to a production server with HTTPS
```bash
# Edit .env first
./deploy-production.sh
```

### I just want to quickly test the app
```bash
./deploy-simple.sh
```

### I can't access from another device
```bash
./scripts/enable-network-access.sh
```

### I want to restart the app
```bash
./scripts/restart-app.sh
# or
docker compose restart app
```

---

## 🔄 Migration Path

### If you've been using deploy.sh:

**Switch to:**
- For development/testing → **start-local.sh** or **deploy-simple.sh**
- For production → **deploy-production.sh**

### If you've been using deploy-auto-fix.sh:

**Switch to:**
- **deploy-simple.sh**

---

## 📝 Summary

### Keep & Maintain
- ✅ start-local.sh (NEW)
- ✅ deploy-production.sh
- ✅ deploy-simple.sh
- ✅ All scripts in scripts/ directory

### Consider Removing
- ⚠️ deploy.sh (too complex)
- ⚠️ deploy-auto-fix.sh (redundant)
- ⚠️ deploy-check-only.sh (rarely used)

### Action Items
1. Update README to promote new start-local.sh
2. Add deprecation warnings to old scripts
3. Update all documentation to reference correct scripts
4. Consider cleanup in future version
