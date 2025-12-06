# Hard Restart Deploy Script Guide

## Overview

The `hard-restart-deploy.sh` script is designed to completely reset and redeploy the StudyBuddy application with comprehensive permission fixes. This script is essential for fixing the auto-update flow and ensuring all permissions are correctly configured.

## Purpose

This script addresses the following issues:

1. **Permission Problems**: Fixes all script, directory, and file permissions
2. **Docker Access**: Ensures proper Docker permissions and user group membership
3. **Auto-Update Flow**: Configures everything needed for the auto-update mechanism to work
4. **Clean Slate**: Forces a complete Docker cleanup and fresh deployment
5. **Systemd Integration**: Fixes systemd service permissions if applicable

## When to Use

Run this script when you encounter:

- Permission denied errors when running scripts
- Docker permission issues ("permission denied while trying to connect to the Docker daemon")
- Auto-update script failures
- Deployment issues after system updates or user changes
- When you need a guaranteed fresh start

## Usage

### Basic Usage

```bash
# Run as regular user (recommended)
./hard-restart-deploy.sh

# Or run with bash explicitly
bash hard-restart-deploy.sh
```

### With Sudo (if needed)

```bash
# If you have permission issues, run with sudo
sudo ./hard-restart-deploy.sh
```

The script automatically detects whether it's running as root or a regular user and adjusts accordingly.

## What It Does

### 1. Permission Fixes

#### Script Permissions
- Makes all `.sh` files executable (`chmod +x`)
- Fixes scripts in both root directory and `scripts/` subdirectory
- Ensures auto-update.sh can be executed

#### Directory Permissions
- Sets correct ownership (to your user, not root)
- Ensures read/write/execute permissions where needed
- Creates missing directories (like `logs/`)
- Fixes permissions on key directories: scripts, src, ui, services, templates, static

#### Docker Permissions
- Adds user to `docker` group if not already added
- Fixes Docker socket permissions (`/var/run/docker.sock`)
- Starts Docker daemon if not running
- Enables Docker to start on boot

#### Git Repository Permissions
- Marks directory as safe for git operations
- Fixes `.git` directory permissions
- Ensures git commands work without sudo

#### Environment File Security
- Creates `.env` from `.env.example` if missing
- Sets secure permissions (600) on `.env` file
- Ensures only the owner can read the file

#### Log File Permissions
- Creates `logs/` directory if missing
- Sets appropriate permissions on log files
- Fixes ownership issues

### 2. Docker Cleanup

- Stops all StudyBuddy containers
- Removes containers completely
- Cleans up dangling images and volumes
- Prepares for fresh deployment

### 3. Fresh Deployment

- Pulls latest Docker images
- Builds images from scratch (no cache)
- Starts all services
- Waits for services to stabilize
- Verifies containers are running

### 4. Verification

- Checks auto-update script is executable
- Tests application health endpoint
- Verifies Docker containers are running
- Reports deployment status

## Output

The script provides colored output for easy reading:

- **Blue [INFO]**: Informational messages
- **Green [✓]**: Success messages
- **Red [✗]**: Error messages
- **Yellow [!]**: Warning messages
- **Cyan [FIX]**: Actions being taken to fix issues

### Example Output

```
╔══════════════════════════════════════════════════════════════╗
║ HARD RESTART DEPLOY - Full Permission Fix                   ║
╚══════════════════════════════════════════════════════════════╝

[INFO] Running as user: youruser

╔══════════════════════════════════════════════════════════════╗
║ Fixing Script Permissions
╚══════════════════════════════════════════════════════════════╝
[✓] Fixed: deploy.sh
[✓] Fixed: scripts/auto-update.sh
...

╔══════════════════════════════════════════════════════════════╗
║  ✓ HARD RESTART COMPLETE!                                   ║
╚══════════════════════════════════════════════════════════════╝
```

## Success Indicators

After successful completion, you should see:

1. ✓ All script permissions fixed
2. ✓ Directory permissions fixed
3. ✓ Docker permissions OK
4. ✓ Git repository permissions fixed
5. ✓ Environment file secured
6. ✓ Docker cleanup complete
7. ✓ Deployment successful (3+ containers running)
8. ✓ Application is healthy

## Post-Deployment

After the script completes, you can:

### Access the Application

- **Web App**: http://localhost:5000
- **RabbitMQ UI**: http://localhost:15672
- **External Access**: http://YOUR_SERVER_IP:5000

### Manage the Application

```bash
# View logs
docker compose logs -f app

# Check status
docker compose ps

# Restart app only
./scripts/restart-app.sh app

# Run auto-update
./scripts/auto-update.sh

# Run hard restart again
./hard-restart-deploy.sh
```

## Troubleshooting

### Permission Denied

If you get "permission denied" even after running the script:

```bash
# Run with sudo
sudo ./hard-restart-deploy.sh

# Then log out and back in to apply group changes
exit
# SSH back in
```

### Docker Daemon Not Running

```bash
# Start Docker manually
sudo systemctl start docker
sudo systemctl enable docker

# Then run the script again
./hard-restart-deploy.sh
```

### Build Failures

If Docker build fails:

```bash
# Check Docker disk space
docker system df

# Clean up if needed
docker system prune -a --volumes

# Run script again
./hard-restart-deploy.sh
```

### Health Check Fails

If the health check fails but containers are running:

```bash
# Wait longer (app might still be starting)
sleep 30
curl http://localhost:5000/health

# Check logs for errors
docker compose logs -f app
```

## Auto-Update Integration

This script ensures the auto-update flow works correctly:

1. **Script Permissions**: Makes auto-update.sh executable
2. **Git Access**: Ensures git commands work without sudo
3. **Docker Access**: Ensures Docker commands work without sudo
4. **File Ownership**: Ensures all files are owned by the correct user

### Testing Auto-Update

After running the hard restart script, test auto-update:

```bash
# Run auto-update manually
./scripts/auto-update.sh

# Check auto-update logs
cat /var/log/studybuddy-update.log
```

### GitHub Actions Integration

The auto-update script can be triggered by:

1. **Webhook**: GitHub Actions sends webhook to your server
2. **SSH**: GitHub Actions connects via SSH and runs the script

Both methods now work correctly after running the hard restart script.

## Security Notes

The script:

- Secures `.env` file with 600 permissions (owner read/write only)
- Does not expose secrets in output
- Uses sudo only when necessary
- Maintains secure Docker socket permissions
- Follows principle of least privilege

## Maintenance

Run this script:

- After major system updates
- When changing server users
- When Docker permissions are broken
- Before important deployments
- If auto-update stops working

## Integration with Other Scripts

This script complements:

- `deploy.sh`: Ultra-robust deployment with auto-fix
- `deploy-auto-fix.sh`: Smart deployment with issue detection
- `scripts/auto-update.sh`: Automated git pull and restart
- `scripts/restart-app.sh`: Quick restart without rebuild
- `update_app.sh`: Update with dependency management

Use `hard-restart-deploy.sh` when you need the most comprehensive reset and permission fix.

## Support

If you encounter issues:

1. Check the script output for error messages
2. Verify you're in the project directory
3. Ensure Docker is installed
4. Check system resources (disk space, memory)
5. Review logs: `docker compose logs -f`

## Version History

- **v1.0**: Initial release with comprehensive permission fixes and auto-update support
