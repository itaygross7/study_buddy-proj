# Hard Restart Deploy Script Guide

## Overview

The `deploy-hard-restart.sh` script is a comprehensive emergency recovery tool designed to fix all permission issues and reset your StudyBuddy deployment to a clean, working state.

## When to Use This Script

Use this script when you're experiencing:

- ❌ Auto-update failing with permission errors
- ❌ Docker commands suddenly requiring sudo
- ❌ Git permission errors blocking updates
- ❌ Multiple failed deployment attempts
- ❌ System in an inconsistent or unknown state
- ❌ "Permission denied" errors on scripts
- ❌ Docker group membership issues

## What It Does

The script performs a complete system reset in the following order:

### 1. Pre-flight Checks
- Verifies you're in a Git repository
- Confirms sudo access
- Checks for `.env` file (creates from `.env.example` if needed)

### 2. Git Permission Fixes
- Sets correct repository ownership to current user
- Fixes `.git` directory permissions
- Makes all `.sh` scripts executable
- Configures Git safe directory
- Ensures scripts directory is accessible

### 3. Docker Permission Fixes
- Verifies Docker is installed
- Starts Docker daemon if needed
- Adds user to docker group
- Tests Docker access without sudo
- Handles both `docker-compose` and `docker compose`

### 4. File & Directory Permission Fixes
- Creates and configures log directories
- Fixes auto-update script permissions
- Fixes restart script permissions
- Ensures data directories have correct ownership

### 5. Docker State Cleanup
- Stops all StudyBuddy containers
- Removes old containers
- Prunes dangling images
- Optionally cleans build cache (interactive)
- **Note: Docker volumes (data) are preserved**

### 6. Systemd Service Handling
- Checks for systemd service
- Optionally stops and disables it (to avoid conflicts)
- Reloads systemd daemon

### 7. Service Rebuild
- Pulls latest base images
- Builds services from scratch (no cache)
- Starts all services
- Waits for services to be ready

### 8. Deployment Verification
- Checks container status
- Tests health endpoints
- Verifies application is responding
- Shows detailed health information

### 9. Auto-Update Configuration
- Optionally sets up cron job for automatic updates
- Schedules daily updates at 3 AM
- Configures logging

## Usage

### Basic Usage

Simply run the script from the repository root:

```bash
cd /path/to/study_buddy-proj
./deploy-hard-restart.sh
```

### What to Expect

The script will:

1. **Show a banner** with script information
2. **Check prerequisites** and prompt for sudo password if needed
3. **Fix all permissions** with detailed output
4. **Clean Docker state** - will ask for confirmation before destructive operations
5. **Rebuild services** - this takes a few minutes
6. **Verify deployment** - runs health checks
7. **Show summary** with access URLs and useful commands

### Interactive Prompts

The script will ask for confirmation before:

- Creating `.env` from `.env.example` (if needed)
- Cleaning Docker state (stopping containers, removing images)
- Pruning Docker system resources
- Stopping systemd service (if exists)
- Setting up auto-update cron job

You can safely answer "No" to optional prompts.

## Output and Logging

### Console Output

The script uses color-coded output:

- 🔵 **BLUE [INFO]**: Information messages
- ✅ **GREEN [✓]**: Success messages
- ⚠️ **YELLOW [!]**: Warnings
- ❌ **RED [✗]**: Errors
- 🔧 **CYAN [FIX]**: Fix operations
- 💜 **MAGENTA**: Section headers

### Log Files

A detailed log is saved to:
```
/tmp/studybuddy-hard-restart-YYYYMMDD-HHMMSS.log
```

This log contains:
- All console output
- Command outputs
- Timestamps
- Error details

Keep this log file for troubleshooting if issues persist.

## After Running the Script

### Verify Deployment

1. **Check the web application**:
   ```bash
   curl http://localhost:5000/health
   ```

2. **Access in browser**:
   - Open `http://localhost:5000`
   - Test login and basic functionality

3. **Check logs**:
   ```bash
   docker compose logs -f app
   ```

### Docker Group Changes

If you couldn't run `docker ps` before, you might need to:

**Option 1: Use newgrp (immediate)**
```bash
newgrp docker
```

**Option 2: Logout and login** (permanent)
```bash
# Logout from your session and login again
```

**Option 3: Use the existing session**
The script will continue to work with sudo if needed.

### Test Auto-Update

If you enabled auto-update during the script:

```bash
# Test it manually
./scripts/auto-update.sh

# Check the cron job
crontab -l | grep auto-update
```

## Common Scenarios

### Scenario 1: Auto-Update Keeps Failing

**Problem**: Running `./scripts/auto-update.sh` gives permission errors

**Solution**:
```bash
./deploy-hard-restart.sh
# Answer "Yes" when asked to set up auto-update cron
```

**Result**: All permissions fixed, auto-update working

---

### Scenario 2: Docker Commands Need Sudo

**Problem**: `docker ps` gives "permission denied" but `sudo docker ps` works

**Solution**:
```bash
./deploy-hard-restart.sh
# After script completes, run:
newgrp docker
```

**Result**: Can run docker commands without sudo

---

### Scenario 3: Git Won't Pull Updates

**Problem**: `git pull` gives "dubious ownership" or permission errors

**Solution**:
```bash
./deploy-hard-restart.sh
```

**Result**: Repository ownership fixed, git operations working

---

### Scenario 4: Everything Is Broken

**Problem**: Multiple issues, nothing works, system is a mess

**Solution**:
```bash
./deploy-hard-restart.sh
# Follow all prompts
# Answer "Yes" to cleanup operations
```

**Result**: Clean slate, everything rebuilt and working

---

## What Gets Preserved

The script is designed to be **safe for production**:

✅ **Preserved**:
- Docker volumes (MongoDB data, RabbitMQ data)
- `.env` file
- Git repository contents
- User data

❌ **Removed/Rebuilt**:
- Docker containers
- Docker images (rebuilt from scratch)
- Build cache (optional)
- Dangling resources

## Troubleshooting the Script Itself

### Script Won't Run

```bash
# Make it executable
chmod +x deploy-hard-restart.sh

# Check syntax
bash -n deploy-hard-restart.sh
```

### Sudo Password Issues

```bash
# Test sudo access
sudo -v

# Refresh sudo timeout
sudo -v && ./deploy-hard-restart.sh
```

### Docker Installation Issues

If Docker isn't installed:

```bash
# Install Docker first
curl -fsSL https://get.docker.com | sudo sh

# Then run the script
./deploy-hard-restart.sh
```

### Script Fails Midway

1. **Check the log file** mentioned in the error
2. **Read the error message** carefully
3. **Try running again** - the script is idempotent
4. **Run specific fixes manually** if needed

## Manual Alternatives

If you prefer to run fixes manually:

### Fix Git Permissions
```bash
sudo chown -R $USER:$USER .
chmod -R u+rwX,go+rX,go-w .git
git config --global --add safe.directory $(pwd)
```

### Fix Docker Permissions
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Fix Scripts
```bash
find . -type f -name "*.sh" -exec chmod +x {} \;
```

### Clean Docker
```bash
docker compose down
docker system prune -f
```

### Rebuild
```bash
docker compose build --no-cache
docker compose up -d
```

## Getting Help

If the script doesn't solve your issues:

1. **Check the log file** generated by the script
2. **Review the TROUBLESHOOTING.md** guide
3. **Run diagnostics**:
   ```bash
   python check_config.py
   ```
4. **Check service logs**:
   ```bash
   docker compose logs -f app
   ```
5. **Open a GitHub issue** with:
   - The log file content (remove sensitive data!)
   - Output of `docker compose ps`
   - Description of remaining issues

## Related Documentation

- [SCRIPTS_GUIDE.md](../SCRIPTS_GUIDE.md) - Overview of all scripts
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - General troubleshooting
- [DEPLOYMENT_INSTRUCTIONS.md](../DEPLOYMENT_INSTRUCTIONS.md) - Deployment guide
- [AUTO_DEPLOYMENT.md](AUTO_DEPLOYMENT.md) - Auto-update setup

## Script Source

The script is located at: `deploy-hard-restart.sh` in the repository root.

You can view the source to understand exactly what it does - it's heavily commented and designed to be readable.

---

**Remember**: This script is designed to be your "reset button" when things go wrong. It's safe to run, even on production systems, because it preserves your data while fixing system issues.
