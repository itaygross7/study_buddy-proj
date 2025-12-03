# Network Access Guide

## Problem: Can't Access App from Another Computer

If your StudyBuddy app is running but you can't connect to it from a different computer, this guide will help you fix it.

## Understanding the Setup

StudyBuddy can run in two modes:

### 1. **Development Mode** (Direct Access on Port 5000)
- App runs directly on port 5000
- No HTTPS (HTTP only)
- Good for local testing and development
- Requires port 5000 to be accessible

### 2. **Production Mode** (Via Caddy on Ports 80/443)
- App runs behind Caddy reverse proxy
- Automatic HTTPS with Let's Encrypt
- Accessible on standard web ports (80/443)
- More secure and professional

## Quick Fix: Enable Port 5000 Access

If you're running in development mode and can't access the app from another computer, your firewall is likely blocking port 5000.

### Option 1: Using the Helper Script (Easiest)

```bash
# Run the network access script
./scripts/enable-network-access.sh
```

This script will:
- Check if the firewall is active
- Open port 5000 for TCP connections
- Verify the configuration
- Show you how to access the app

### Option 2: Manual Configuration

#### For UFW (Ubuntu/Debian)

```bash
# Check if UFW is active
sudo ufw status

# Allow port 5000
sudo ufw allow 5000/tcp comment 'StudyBuddy Development'

# Verify the rule was added
sudo ufw status numbered
```

#### For firewalld (CentOS/RHEL/Fedora)

```bash
# Check if firewalld is running
sudo firewall-cmd --state

# Allow port 5000
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload

# Verify the rule was added
sudo firewall-cmd --list-ports
```

#### For iptables (Advanced)

```bash
# Allow port 5000
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT

# Save the rules (Ubuntu/Debian)
sudo netfilter-persistent save

# Or for CentOS/RHEL
sudo service iptables save
```

## Accessing Your App

After opening the port, you can access your app from any computer on the same network:

### Find Your Server's IP Address

```bash
# Get your local IP address
hostname -I | awk '{print $1}'

# Or use ip command
ip addr show | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | cut -d/ -f1
```

### Access the App

From another computer on the same network, open your browser and go to:

```
http://YOUR_SERVER_IP:5000
```

For example:
- `http://192.168.1.100:5000`
- `http://10.0.0.50:5000`

## Troubleshooting

### Still Can't Connect?

1. **Verify the app is running:**
   ```bash
   docker compose ps
   curl http://localhost:5000/health
   ```

2. **Check if the port is listening:**
   ```bash
   sudo netstat -tuln | grep 5000
   # Or
   sudo ss -tuln | grep 5000
   ```
   
   You should see something like:
   ```
   tcp        0      0 0.0.0.0:5000            0.0.0.0:*               LISTEN
   ```

3. **Test from the server itself:**
   ```bash
   curl http://localhost:5000/health
   ```
   
   If this works but external access doesn't, it's definitely a firewall issue.

4. **Check Docker port mapping:**
   ```bash
   docker compose ps
   docker port studybuddy_app
   ```
   
   Should show: `5000/tcp -> 0.0.0.0:5000`

5. **Verify firewall rules:**
   ```bash
   sudo ufw status verbose
   # Or
   sudo firewall-cmd --list-all
   ```

6. **Check if another application is using port 5000:**
   ```bash
   sudo lsof -i :5000
   ```

### Accessing from the Internet (Not Local Network)

If you want to access your app from the internet (not just local network):

1. **Use Production Mode** (Recommended):
   ```bash
   ./deploy-production.sh
   ```
   This sets up HTTPS, proper security, and uses standard ports 80/443.

2. **Configure Port Forwarding** on your router:
   - Forward external port 80 → internal IP port 5000
   - Forward external port 443 → internal IP port 5000 (if using HTTPS)
   - Or use Caddy for proper HTTPS setup

3. **Use a VPN/Tunnel** (Most Secure):
   - Tailscale (recommended - built into production deployment)
   - WireGuard
   - OpenVPN

## Security Considerations

### Development Mode (Port 5000)

⚠️ **Warning:** Direct access on port 5000 is NOT secure for production use!

- No HTTPS encryption
- No SSL certificate
- Traffic is not encrypted
- Passwords and data are sent in plain text

**Only use port 5000 for:**
- Local development
- Testing on a trusted network
- Internal network access

### Production Mode (Recommended)

✅ **For production, always use:**

```bash
./deploy-production.sh
```

This provides:
- Automatic HTTPS with Let's Encrypt
- Encrypted traffic
- Standard ports (80/443)
- Proper security headers
- Tailscale for secure SSH access
- Firewall properly configured

## Summary

| Scenario | Solution |
|----------|----------|
| Testing locally | Access via `http://localhost:5000` |
| Access from same network | Open port 5000 in firewall, access via `http://SERVER_IP:5000` |
| Production deployment | Use `./deploy-production.sh` for HTTPS on ports 80/443 |
| Secure remote access | Use Tailscale (included in production deployment) |

## Quick Command Reference

```bash
# Check if firewall is blocking
sudo ufw status

# Open port 5000 for development
sudo ufw allow 5000/tcp

# Check if app is running
docker compose ps

# View app logs
docker compose logs -f app

# Get server IP
hostname -I | awk '{print $1}'

# Test from server
curl http://localhost:5000/health

# Restart app
docker compose restart app
```

## Need More Help?

1. Check the main [README.md](../README.md)
2. Review [DEPLOYMENT.md](./DEPLOYMENT.md) for production setup
3. Run the pre-deployment check: `./scripts/pre-deploy-check.sh`
4. Open an issue on GitHub
