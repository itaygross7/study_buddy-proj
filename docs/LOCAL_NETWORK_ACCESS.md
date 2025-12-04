# Local Network Access Guide

## Overview

This guide explains how to access StudyBuddy from other computers on your local network (e.g., accessing from your phone or another laptop on the same WiFi).

## Quick Start

### Method 1: Using the Local Configuration (Recommended)

```bash
# Start the app without Caddy (HTTPS/production features)
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build

# Find your server's IP address
hostname -I | awk '{print $1}'

# Access from any device on the same network
# Example: http://192.168.1.100:5000
```

### Method 2: Stop Caddy Service

If you've already started with the full docker-compose:

```bash
# Stop the Caddy service
docker compose stop caddy

# Access the app directly on port 5000
```

## Understanding the Problem

When you run `docker compose up -d`, it starts **all services** including:
- ✅ **app** - The main Flask application (port 5000)
- ✅ **mongo** - MongoDB database
- ✅ **rabbitmq** - Message broker
- ✅ **worker** - Background task processor
- ⚠️ **caddy** - Reverse proxy with HTTPS (requires a domain!)

The Caddy service is designed for **production deployment** with a proper domain name (e.g., studybuddyai.my). When Caddy tries to start without a valid domain, it attempts to obtain an SSL certificate from Let's Encrypt, which fails with the error:

```
Cannot issue for "https": Domain name needs at least one dot
```

For local network access, you don't need Caddy or HTTPS!

## Solution Options

### Option 1: Use Local Configuration (Best for Local Network)

The `docker-compose.local.yml` file disables Caddy and other production features:

```bash
# Start services
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build

# The app will be accessible on port 5000
# From the server: http://localhost:5000
# From other devices: http://YOUR_IP:5000
```

**Advantages:**
- ✅ No Caddy errors in logs
- ✅ Simpler setup for local development
- ✅ Fast startup (fewer services)
- ✅ No domain configuration needed

### Option 2: Stop Caddy Manually

If you've already started the full stack:

```bash
# Stop Caddy
docker compose stop caddy

# Optionally, stop healthcheck too
docker compose stop healthcheck
```

### Option 3: Configure Caddy for Local IP (Advanced)

You can configure Caddy to work with your local IP address (without HTTPS):

1. Edit your `.env` file:
   ```bash
   # Use your local IP instead of a domain
   DOMAIN="192.168.1.100"  # Replace with your actual IP
   BASE_URL="http://192.168.1.100:5000"
   ```

2. Create a local Caddyfile at `infra/Caddyfile.local`:
   ```
   # Local network configuration (no HTTPS)
   :80 {
       reverse_proxy app:5000
   }
   ```

3. Update docker-compose to use the local Caddyfile (not recommended - use Option 1 instead)

## Accessing Your App

### Step 1: Find Your Server's IP Address

```bash
# Method 1: hostname command
hostname -I | awk '{print $1}'

# Method 2: ip command
ip addr show | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}' | cut -d/ -f1

# Method 3: Check network settings
ifconfig | grep "inet " | grep -v 127.0.0.1
```

Example output: `192.168.1.100`

### Step 2: Open Firewall (If Necessary)

Most firewalls block port 5000 by default. Open it:

```bash
# Ubuntu/Debian (UFW)
sudo ufw allow 5000/tcp
sudo ufw status

# CentOS/RHEL/Fedora (firewalld)
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload

# Or use the helper script
./scripts/enable-network-access.sh
```

### Step 3: Access from Another Device

On any device connected to the same network:
1. Open a web browser
2. Navigate to: `http://YOUR_IP:5000`
3. Example: `http://192.168.1.100:5000`

## Troubleshooting

### "Connection Refused" or "Cannot Connect"

**Check 1: Is the app running?**
```bash
docker compose ps
# Should show 'app' with status 'Up'
```

**Check 2: Is the app listening?**
```bash
sudo netstat -tlnp | grep 5000
# Should show something like: tcp 0.0.0.0:5000 ... LISTEN
```

**Check 3: Test local access**
```bash
curl http://localhost:5000/health
# Should return: {"status":"healthy"}
```

**Check 4: Is firewall blocking?**
```bash
# Ubuntu/Debian
sudo ufw status
# Check if 5000/tcp is listed

# Test from another device
ping YOUR_IP  # Should respond
```

**Check 5: Are you on the same network?**
- Both devices must be connected to the same WiFi/network
- Some guest WiFi networks block device-to-device communication

### Caddy Logs Show Errors

If you see errors like:
```
Cannot issue for "https": Domain name needs at least one dot
```

**Solution:** You're running Caddy without a proper domain. Use the local configuration:
```bash
# Stop everything
docker compose down

# Restart with local config
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

### Cannot Access from Mobile Device

**Common causes:**
1. **Different networks** - Mobile on cellular, computer on WiFi
   - Solution: Connect mobile to same WiFi as server

2. **AP Isolation enabled** - Router blocks device-to-device communication
   - Solution: Disable AP Isolation in router settings
   - Or: Use USB tethering / hotspot from computer

3. **Firewall blocking** - Port 5000 not open
   - Solution: Run `./scripts/enable-network-access.sh`

## Comparison: Local vs Production

### Local Network Access (Port 5000)
- ✅ Easy setup, no domain needed
- ✅ Fast, direct access to app
- ✅ Good for development and testing
- ⚠️ HTTP only (no encryption)
- ⚠️ Requires firewall rules
- ❌ Not suitable for public internet

**When to use:**
- Testing on your home network
- Development environment
- Accessing from your phone/tablet on same WiFi
- Friends and family demo on local network

### Production with Caddy (Ports 80/443)
- ✅ Automatic HTTPS with Let's Encrypt
- ✅ Encrypted traffic (secure)
- ✅ Standard web ports (80/443)
- ✅ Professional deployment
- ⚠️ Requires a domain name
- ⚠️ DNS must point to your server
- ❌ More complex setup

**When to use:**
- Production deployment
- Public-facing website
- Custom domain (e.g., studybuddyai.com)
- Internet access from anywhere

## Quick Reference

### Start with local config (no Caddy)
```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

### Start with production config (with Caddy)
```bash
# Ensure DOMAIN is set in .env
docker compose up -d --build
```

### Switch from production to local
```bash
docker compose down
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

### Switch from local to production
```bash
docker compose down
# Set DOMAIN in .env to your actual domain
docker compose up -d --build
```

### View logs
```bash
# All services
docker compose logs -f

# Just the app
docker compose logs -f app

# Check for Caddy errors (if running production)
docker compose logs caddy | grep -i error
```

### Stop services
```bash
# Stop all
docker compose down

# Stop just Caddy
docker compose stop caddy
```

## Security Notes

### Local Network (HTTP)
- ⚠️ **Not encrypted** - Traffic sent in plain text
- ⚠️ **Vulnerable on public WiFi** - Others can see your data
- ✅ **Safe on home network** - As long as network is trusted
- ✅ **Fine for development** - Not handling sensitive production data

**Best practices:**
- Use only on trusted networks (home, office)
- Don't use on public WiFi (coffee shop, airport)
- Don't transmit sensitive data over HTTP
- Use production setup (HTTPS) for real deployments

### Production (HTTPS)
- ✅ **End-to-end encryption** - Data protected in transit
- ✅ **Certificate validation** - Prevents man-in-the-middle attacks
- ✅ **Secure cookies** - Session tokens protected
- ✅ **Industry standard** - Required for production use

## Need More Help?

- **Network access issues:** See [NETWORK_ACCESS.md](NETWORK_ACCESS.md) or run `./scripts/enable-network-access.sh`
- **Production deployment:** See [`DEPLOYMENT.md`](./DEPLOYMENT.md) or run `./deploy-production.sh`
- **Quick network fix:** See [`QUICK_FIX_NETWORK.md`](./QUICK_FIX_NETWORK.md)
- **General troubleshooting:** See [`../TROUBLESHOOTING.md`](../TROUBLESHOOTING.md)
- **Configuration issues:** Run `python check_config.py`
