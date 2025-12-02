# Deployment Scripts Usage Guide

This guide explains how to use the StudyBuddyAI deployment automation scripts.

## Overview

StudyBuddyAI includes two powerful scripts to automate and simplify deployment:

1. **`deploy.sh`** - Main deployment script that orchestrates everything
2. **`scripts/pre-deploy-check.sh`** - Comprehensive system checks script

## Main Deployment Script (`deploy.sh`)

### Basic Usage

```bash
# Simple deployment (recommended for first-time users)
./deploy.sh
```

This will:
1. Run all pre-deployment checks
2. Verify your `.env` configuration
3. Build Docker images
4. Start all services
5. Wait for services to be healthy
6. Display access information

### Command-Line Options

#### `--check-only`
Run system checks without deploying.

```bash
./deploy.sh --check-only
```

Use this to:
- Diagnose issues before deploying
- Verify your system is ready
- Check if ports are available
- Validate configuration

#### `--rebuild`
Force rebuild all Docker images without cache.

```bash
./deploy.sh --rebuild
```

Use this when:
- You've made code changes
- Dependencies have been updated
- Images are corrupted
- You want a clean build

#### `--clean`
Remove all existing containers and volumes (fresh start).

```bash
./deploy.sh --clean
```

**WARNING**: This will delete all data including:
- MongoDB database
- RabbitMQ messages
- All persistent data

Use this when:
- Starting fresh
- Troubleshooting persistent issues
- Switching configurations

The script will ask for confirmation before proceeding.

#### `--skip-checks`
Skip pre-deployment checks (not recommended).

```bash
./deploy.sh --skip-checks
```

Only use this if:
- You've already run checks manually
- You're certain your system is ready
- You're debugging a specific issue

#### `--help`
Display help information.

```bash
./deploy.sh --help
```

### Exit Codes

- `0` - Success
- `1` - Failure (checks failed or deployment error)

## Pre-Deployment Check Script

### Basic Usage

```bash
./scripts/pre-deploy-check.sh
```

### What It Checks

1. **Operating System**
   - Detects OS name and version
   - Shows kernel version

2. **Docker Installation**
   - Verifies Docker is installed
   - Checks Docker daemon is running
   - Tests Docker permissions

3. **Docker Compose**
   - Detects Docker Compose V2 or standalone
   - Verifies it's functional

4. **Port Availability**
   - 5000 (Flask App)
   - 27017 (MongoDB)
   - 5672 (RabbitMQ AMQP)
   - 15672 (RabbitMQ Management UI)

5. **Network Connectivity**
   - ICMP connectivity test
   - DNS resolution (google.com, github.com, pypi.org, hub.docker.com)
   - HTTPS connectivity test

6. **Environment Configuration**
   - `.env` file exists
   - Required variables are set (SECRET_KEY, ADMIN_EMAIL)
   - At least one AI API key is configured
   - Values are not placeholders

7. **System Resources**
   - Disk space (warns if < 5GB)
   - Available memory
   - CPU cores

8. **Docker Network**
   - Docker network subsystem operational
   - Existing networks

9. **Docker Images**
   - Existing StudyBuddy images
   - Base images availability

10. **Docker Cleanup**
    - Stopped containers
    - Dangling images
    - Disk usage

11. **Firewall**
    - UFW/firewalld status
    - Port recommendations

### Understanding Check Results

Each check produces one of three results:

- **[✓] Success** (Green) - Check passed
- **[!] Warning** (Yellow) - Non-critical issue
- **[✗] Failed** (Red) - Critical issue that must be fixed

### Summary Output

At the end, you'll see:
```
Passed:   17
Warnings: 1
Failed:   3
```

If `Failed` is 0, you're ready to deploy!

## Common Workflows

### First-Time Deployment

```bash
# 1. Clone and configure
git clone https://github.com/itaygross7/study_buddy-proj.git
cd study_buddy-proj
cp .env.example .env
nano .env

# 2. Run checks
./deploy.sh --check-only

# 3. Fix any issues reported

# 4. Deploy
./deploy.sh
```

### Update Existing Deployment

```bash
# 1. Pull latest code
cd study_buddy-proj
git pull

# 2. Rebuild and restart
./deploy.sh --rebuild
```

### Troubleshooting

```bash
# 1. Run diagnostics
./scripts/pre-deploy-check.sh

# 2. Check logs
docker compose logs -f app

# 3. If needed, fresh start
./deploy.sh --clean
```

### Clean Reinstall

```bash
# 1. Stop and remove everything
./deploy.sh --clean

# 2. Optionally, remove configuration
rm .env

# 3. Reconfigure
cp .env.example .env
nano .env

# 4. Deploy fresh
./deploy.sh
```

## Interpreting Output

### Deploy Script Output

The deployment script provides detailed progress:

```
═══════════════════════════════════════════════════════════════
  Pre-Deployment Checks
═══════════════════════════════════════════════════════════════
[INFO] Running pre-deployment checks...
[✓] All pre-deployment checks passed

═══════════════════════════════════════════════════════════════
  Environment Setup
═══════════════════════════════════════════════════════════════
[✓] .env file exists
[INFO] Using: docker compose

═══════════════════════════════════════════════════════════════
  Building and Starting Services
═══════════════════════════════════════════════════════════════
[INFO] Building Docker images...
[INFO] Starting services...
[✓] Services started

═══════════════════════════════════════════════════════════════
  Waiting for Services
═══════════════════════════════════════════════════════════════
[INFO] Waiting for services to be healthy...
[✓] All services are healthy

═══════════════════════════════════════════════════════════════
  Deployment Complete!
═══════════════════════════════════════════════════════════════

✓ StudyBuddyAI is now running!

Access Points:
  → Application:       http://localhost:5000
  → External Access:   http://192.168.1.100:5000
  → RabbitMQ Manager:  http://localhost:15672

Useful Commands:
  View logs:         docker compose logs -f app
  Check status:      docker compose ps
  Stop services:     docker compose down
```

### Check Script Output

The check script shows detailed information for each check:

```
═══════════════════════════════════════════════════════════════
  Docker Installation Check
═══════════════════════════════════════════════════════════════
[INFO] Found: Docker version 28.0.4, build b8034c0
[✓] Docker daemon is running
```

## Tips and Best Practices

### Before Deploying

1. **Always run checks first**
   ```bash
   ./deploy.sh --check-only
   ```

2. **Generate a secure SECRET_KEY**
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

3. **Verify your .env file**
   - No placeholder values
   - Valid API keys
   - Correct email address

### During Deployment

1. **Watch the output** - The script tells you what's happening
2. **Be patient** - Initial builds take 2-5 minutes
3. **Don't interrupt** - Let the script complete

### After Deployment

1. **Check service status**
   ```bash
   docker compose ps
   ```

2. **View application logs**
   ```bash
   docker compose logs -f app
   ```

3. **Test the application**
   ```bash
   curl http://localhost:5000/health
   ```

### Regular Maintenance

1. **Check disk space regularly**
   ```bash
   docker system df
   ```

2. **Clean up unused resources**
   ```bash
   docker system prune
   ```

3. **Update regularly**
   ```bash
   git pull && ./deploy.sh --rebuild
   ```

## Troubleshooting

### Script Won't Execute

```bash
# Make it executable
chmod +x deploy.sh
chmod +x scripts/pre-deploy-check.sh
```

### Checks Fail

1. Read the error messages carefully
2. Fix the reported issues
3. Run checks again
4. Repeat until all pass

### Deployment Hangs

1. Press Ctrl+C to stop
2. Check Docker daemon: `docker info`
3. Check disk space: `df -h`
4. Try again with `--rebuild`

### Services Won't Start

1. Check logs: `docker compose logs -f`
2. Verify .env configuration
3. Check port conflicts: `sudo lsof -i :5000`
4. Try fresh start: `./deploy.sh --clean`

## Advanced Usage

### Running in CI/CD

```bash
# Automated deployment (skip interactive prompts)
./deploy.sh --skip-checks
```

### Custom Docker Compose

```bash
# Use custom compose file
export COMPOSE_FILE=docker-compose.prod.yml
./deploy.sh
```

### Debugging

```bash
# Enable bash debugging
bash -x ./deploy.sh
```

## Getting Help

- Check this guide
- Run `./deploy.sh --help`
- Review logs: `docker compose logs -f`
- See DEPLOYMENT.md for detailed deployment guide
- Check README.md for general information

---

**Questions? Issues?**  
Open an issue at: https://github.com/itaygross7/study_buddy-proj/issues
