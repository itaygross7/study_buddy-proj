# Update App Script - Production Updates Without Redeployment

The `update_app.sh` script allows you to update your StudyBuddy installation in production without full redeployment. It performs a git pull and restarts services automatically.

## Features

✅ Pull latest changes from git repository  
✅ Check for dependency updates  
✅ Automatically detect deployment type (Docker or systemd)  
✅ Restart services automatically  
✅ Verify application health after update  
✅ Safe rollback instructions if issues occur

## Prerequisites

- Git repository already cloned and configured
- Proper permissions to pull from the repository (SSH key or HTTPS credentials)
- Access to restart services:
  - For Docker: docker and docker-compose access
  - For systemd: sudo access to systemctl

## Usage

### Basic Update

```bash
cd /path/to/study_buddy-proj
./update_app.sh
```

The script will:
1. Check git status for uncommitted changes
2. Fetch latest changes from remote
3. Show you what will be updated
4. Ask for confirmation
5. Pull the changes
6. Update dependencies if needed
7. Restart services
8. Verify the app is running

### Interactive Prompts

The script will ask for confirmation at key steps:

```
Do you want to stash these changes and continue? (y/n)
```
- If you have uncommitted local changes, choose `y` to stash them or `n` to cancel

```
Continue with update? (y/n)
```
- After showing you the changes to be pulled, confirm to proceed

## Deployment Types

### Docker Deployment

If your app runs in Docker, the script automatically detects it and runs:
```bash
docker-compose restart app worker
```

### Systemd Deployment

If your app runs as a systemd service, the script runs:
```bash
sudo systemctl restart studybuddy.service
sudo systemctl restart studybuddy-worker.service  # if exists
```

### Manual Deployment

If neither Docker nor systemd is detected, the script will show instructions for manual restart.

## What Gets Updated

- ✅ Application code (Python files)
- ✅ Templates (HTML files)
- ✅ Static files (CSS, JS, images)
- ✅ Configuration files
- ✅ Python dependencies (if requirements.txt or Pipfile changed)
- ✅ Node dependencies (if package.json changed)

## Safety Features

### Uncommitted Changes

If you have uncommitted local changes, the script:
- Shows you what files changed
- Offers to stash them
- Allows you to cancel the update

### Confirmation Required

The script requires explicit confirmation before:
- Pulling changes (after showing what will change)
- Continuing with update

### Health Check

After restart, the script:
- Waits 5 seconds for services to start
- Checks the `/health` endpoint
- Reports if the app is healthy or not

### Rollback Instructions

If something goes wrong, the script provides rollback commands at the end:

```bash
git reset --hard PREVIOUS_COMMIT_SHA && ./update_app.sh
```

## Example Session

```bash
$ ./update_app.sh
==============================================================================
StudyBuddy Production Update Script
==============================================================================

Current directory: /home/studybuddy/study_buddy-proj

Step 1: Checking git status...
✓ Working directory is clean

Current branch: main
Current commit: abc1234

Step 2: Fetching latest changes from remote...
2 commit(s) available for update

Step 3: Changes to be pulled:
def5678 Fix OAuth redirect URI issue
ghi9012 Add background images to UI

Continue with update? (y/n) y

Step 4: Pulling latest changes...
✓ Updated from abc1234 to ghi9012

Step 5: Checking for dependency changes...
No dependency changes detected

Step 6: Restarting services...
Detected Docker deployment
Restarting Docker containers...
✓ Docker containers restarted

Step 7: Verifying application...
✓ Application is running and healthy!

==============================================================================
Update completed successfully!
==============================================================================

Updated from commit abc1234 to ghi9012

What to do next:
  1. Check logs: docker-compose logs -f app (or journalctl -u studybuddy -f)
  2. Test the app in your browser
  3. If issues occur, rollback: git reset --hard abc1234 && ./update_app.sh
```

## Troubleshooting

### Permission Denied

```bash
chmod +x update_app.sh
```

### Git Pull Fails

**Authentication Issues:**
```bash
# For HTTPS:
git remote set-url origin https://YOUR_TOKEN@github.com/user/repo.git

# For SSH:
ssh-add ~/.ssh/id_rsa
```

**Merge Conflicts:**

The script will detect conflicts. You'll need to resolve manually:
```bash
git status  # See conflicted files
# Edit files to resolve conflicts
git add .
git commit
```

### Services Don't Restart

**Docker:**
```bash
# Check Docker is running
docker ps

# Manual restart
docker-compose restart app worker
```

**Systemd:**
```bash
# Check service status
sudo systemctl status studybuddy

# Manual restart
sudo systemctl restart studybuddy
```

### Health Check Fails

If the health check fails after update:

1. **Check logs:**
   ```bash
   # Docker:
   docker-compose logs app --tail=100
   
   # Systemd:
   sudo journalctl -u studybuddy -n 100
   ```

2. **Common issues:**
   - Database connection issues
   - Missing environment variables
   - Dependency conflicts

3. **Rollback if needed:**
   ```bash
   git reset --hard PREVIOUS_COMMIT
   ./update_app.sh
   ```

### Dependency Update Fails

If Python or Node dependencies fail to update:

**Python:**
```bash
# Try manual update
pip install -r requirements.txt
# OR
pipenv install --deploy
```

**Node:**
```bash
npm install
```

## Best Practices

### 1. Test in Staging First

Always test updates in a staging environment before production.

### 2. Backup Before Update

```bash
# Backup database
docker exec mongodb mongodump --out=/backup

# Backup .env file
cp .env .env.backup
```

### 3. Monitor After Update

Watch logs for a few minutes after update:
```bash
# Docker:
docker-compose logs -f app

# Systemd:
sudo journalctl -u studybuddy -f
```

### 4. Schedule Updates During Low Traffic

Update during low-usage periods to minimize impact.

### 5. Keep .env Updated

After update, check if new environment variables are needed:
```bash
diff .env.example .env
```

## Advanced Usage

### Update Without Confirmation

```bash
yes y | ./update_app.sh
```
⚠️ **Warning:** Not recommended for production!

### Update Specific Branch

```bash
git checkout develop
./update_app.sh
```

### Dry Run

To see what would be updated without actually updating:
```bash
git fetch origin
git log HEAD..origin/main --oneline
```

## Automation

### Cron Job

You can schedule automatic updates (not recommended without testing):

```bash
# Edit crontab
crontab -e

# Add line to update daily at 3 AM
0 3 * * * cd /home/studybuddy/study_buddy-proj && ./update_app.sh >> /var/log/studybuddy-update.log 2>&1
```

⚠️ **Not recommended for production** - manual updates with verification are safer.

### GitHub Webhook

For automatic updates via GitHub webhook, see the main [DEPLOYMENT_SUMMARY.md](../DEPLOYMENT_SUMMARY.md) for webhook configuration.

## Support

For issues with the update script:

1. Check the main [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
2. Review application logs
3. Verify git and service configurations
4. Try manual update steps

## See Also

- [DEPLOYMENT_SUMMARY.md](../DEPLOYMENT_SUMMARY.md) - Full deployment guide
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - Common issues
- [START_HERE.md](../START_HERE.md) - Getting started guide
