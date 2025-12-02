# StudyBuddyAI Server Deployment Guide

Complete guide for deploying StudyBuddyAI on Ubuntu 22.04 with Docker, Caddy reverse proxy, and dynamic DNS.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Setup](#server-setup)
3. [Docker Installation](#docker-installation)
4. [Application Deployment](#application-deployment)
5. [Reverse Proxy Setup (Caddy)](#reverse-proxy-setup-caddy)
6. [Dynamic DNS Setup](#dynamic-dns-setup)
7. [Firewall Configuration](#firewall-configuration)
8. [SSL/HTTPS Configuration](#sslhttps-configuration)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Ubuntu 22.04 LTS server
- Domain name (e.g., `studybuddyai.my`)
- At least 2GB RAM, 20GB storage
- Root or sudo access
- AI API key (Google Gemini or OpenAI)

---

## Server Setup

### 1. Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Essential Tools

```bash
sudo apt install -y curl wget git nano ufw
```

### 3. Set Timezone (Optional)

```bash
sudo timedatectl set-timezone Asia/Jerusalem
```

---

## Docker Installation

### 1. Install Docker

```bash
# Download and run official Docker install script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (no sudo needed for docker commands)
sudo usermod -aG docker $USER

# Apply group changes
newgrp docker

# Verify installation
docker --version
docker compose version
```

### 2. Configure Docker DNS (Important for Ubuntu 22.04)

Ubuntu 22.04 uses `systemd-resolved` which can cause DNS issues in Docker. Fix this:

```bash
# Create Docker daemon configuration
sudo mkdir -p /etc/docker
sudo nano /etc/docker/daemon.json
```

Add:
```json
{
    "dns": ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
}
```

Restart Docker:
```bash
sudo systemctl restart docker
```

---

## Application Deployment

### 1. Clone Repository

```bash
cd /opt
sudo git clone https://github.com/itaygross7/study_buddy-proj.git studybuddy
sudo chown -R $USER:$USER /opt/studybuddy
cd /opt/studybuddy
```

### 2. Configure Environment

```bash
cp .env.example .env
nano .env
```

**Required settings:**
```bash
# Generate a secure secret key
SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"

# Your AI API key (at least one required)
GEMINI_API_KEY="your_gemini_api_key_here"

# Admin email (gets admin access automatically)
ADMIN_EMAIL="your_email@example.com"

# Domain configuration
DOMAIN="studybuddyai.my"
BASE_URL="https://studybuddyai.my"

# For production with HTTPS
SESSION_COOKIE_SECURE=true
```

### 3. Build and Start Services

```bash
# Build and start all services
docker compose up -d --build

# Check status
docker compose ps

# View logs
docker compose logs -f app
```

### 4. Verify Deployment

```bash
# Check health endpoint
curl http://localhost:5000/health

# Should return: {"status": "healthy"}
```

---

## Reverse Proxy Setup (Caddy)

Caddy provides automatic HTTPS with Let's Encrypt.

### 1. Install Caddy

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

### 2. Configure Caddy

```bash
sudo nano /etc/caddy/Caddyfile
```

Use the provided configuration from `infra/Caddyfile`:

```caddyfile
studybuddyai.my, www.studybuddyai.my {
    reverse_proxy localhost:5000 {
        health_uri /health
        health_interval 30s
        health_timeout 5s
        
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
    
    encode gzip
    
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        X-XSS-Protection "1; mode=block"
        Referrer-Policy strict-origin-when-cross-origin
        -Server
    }
    
    log {
        output file /var/log/caddy/studybuddyai.log {
            roll_size 10mb
            roll_keep 5
        }
    }
}
```

### 3. Start Caddy

```bash
# Create log directory
sudo mkdir -p /var/log/caddy

# Test configuration
sudo caddy validate --config /etc/caddy/Caddyfile

# Restart Caddy
sudo systemctl restart caddy
sudo systemctl enable caddy

# Check status
sudo systemctl status caddy
```

---

## Dynamic DNS Setup

For home servers with dynamic IP addresses.

### 1. Create DDNS Script

```bash
sudo nano /opt/studybuddy/scripts/update_dns.sh
```

```bash
#!/bin/bash
# Dynamic DNS Update Script for Hostinger
# Updates A and AAAA records when IP changes

API_KEY="YOUR_HOSTINGER_API_KEY"
ZONE_ID="YOUR_HOSTINGER_ZONE_ID"
DOMAIN="studybuddyai.my"
RECORD_NAME="@"

STATE_DIR="/var/lib/update_dns"
LOG_FILE="/var/log/update_dns.log"

mkdir -p "$STATE_DIR"
touch "$LOG_FILE"

LAST_IPV4_FILE="$STATE_DIR/last_ipv4"
LAST_IPV6_FILE="$STATE_DIR/last_ipv6"

log() {
    local level="$1"
    shift
    local msg="$*"
    local timestamp
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[$timestamp] [$level] $msg" | tee -a "$LOG_FILE"
}

get_public_ipv4() {
    curl -4 -s https://ipv4.icanhazip.com | tr -d '[:space:]'
}

get_public_ipv6() {
    curl -6 -s https://ipv6.icanhazip.com | tr -d '[:space:]'
}

update_record() {
    local type="$1"
    local value="$2"
    local name="$3"

    if [[ -z "$value" ]]; then
        log "WARN" "Missing value for $type record"
        return 1
    fi

    local response
    response=$(curl -sS -X PUT "https://api.hostinger.com/v1/dns-zones/${ZONE_ID}/records/${type}" \
        -H "Authorization: Bearer ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d "{
              \"name\": \"${name}\",
              \"value\": \"${value}\",
              \"ttl\": 300
            }")

    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log "ERROR" "Failed to update $type record (exit $exit_code)"
        log "ERROR" "Response: ${response}"
        return $exit_code
    fi

    log "INFO" "Updated $type record to $value"
    return 0
}

log "INFO" "===== DNS update start for ${DOMAIN} ====="

CURRENT_IPV4="$(get_public_ipv4)"
CURRENT_IPV6="$(get_public_ipv6)"

log "INFO" "Detected IPv4: ${CURRENT_IPV4:-none}"
log "INFO" "Detected IPv6: ${CURRENT_IPV6:-none}"

LAST_IPV4=""
LAST_IPV6=""

[[ -f "$LAST_IPV4_FILE" ]] && LAST_IPV4="$(cat "$LAST_IPV4_FILE" 2>/dev/null)"
[[ -f "$LAST_IPV6_FILE" ]] && LAST_IPV6="$(cat "$LAST_IPV6_FILE" 2>/dev/null)"

# Update IPv4 (A record)
if [[ -n "$CURRENT_IPV4" ]]; then
    if [[ "$CURRENT_IPV4" != "$LAST_IPV4" ]]; then
        log "INFO" "IPv4 changed: '${LAST_IPV4:-none}' -> '$CURRENT_IPV4'"
        if update_record "A" "$CURRENT_IPV4" "$RECORD_NAME"; then
            echo "$CURRENT_IPV4" > "$LAST_IPV4_FILE"
        fi
    else
        log "INFO" "IPv4 unchanged ($CURRENT_IPV4), no A update"
    fi
fi

# Update IPv6 (AAAA record)
if [[ -n "$CURRENT_IPV6" ]]; then
    if [[ "$CURRENT_IPV6" != "$LAST_IPV6" ]]; then
        log "INFO" "IPv6 changed: '${LAST_IPV6:-none}' -> '$CURRENT_IPV6'"
        if update_record "AAAA" "$CURRENT_IPV6" "$RECORD_NAME"; then
            echo "$CURRENT_IPV6" > "$LAST_IPV6_FILE"
        fi
    fi
fi

log "INFO" "===== DNS update finished for ${DOMAIN} ====="
exit 0
```

### 2. Setup Permissions and Cron

```bash
# Make executable
sudo chmod +x /opt/studybuddy/scripts/update_dns.sh

# Create state directory
sudo mkdir -p /var/lib/update_dns
sudo touch /var/log/update_dns.log

# Add to crontab (runs every 5 minutes)
sudo crontab -e
```

Add this line:
```
*/5 * * * * /opt/studybuddy/scripts/update_dns.sh
```

---

## Firewall Configuration

### 1. Configure UFW

```bash
# Enable UFW
sudo ufw enable

# Allow SSH (important - don't lock yourself out!)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Optional: Allow RabbitMQ management UI (only from local network)
# sudo ufw allow from 192.168.1.0/24 to any port 15672

# Check status
sudo ufw status verbose
```

### 2. Router Port Forwarding

Forward these ports to your server:
- **80** → Server IP (for ACME/Let's Encrypt challenge)
- **443** → Server IP (for HTTPS)

---

## SSL/HTTPS Configuration

Caddy handles SSL automatically! Just ensure:

1. Domain DNS points to your server IP
2. Ports 80 and 443 are open and forwarded
3. Caddy is running

Caddy will automatically:
- Obtain SSL certificate from Let's Encrypt
- Renew certificates before expiry
- Redirect HTTP to HTTPS

---

## Troubleshooting

### Docker Build Fails

**DNS Resolution Issues:**
```bash
# Check Docker DNS configuration
cat /etc/docker/daemon.json

# Restart Docker
sudo systemctl restart docker
```

**SSL Certificate Errors:**
```bash
# Update CA certificates in the container
docker compose build --no-cache
```

### Application Not Starting

**Check logs:**
```bash
docker compose logs -f app
docker compose logs -f worker
```

**Check container status:**
```bash
docker compose ps
docker compose exec app python -c "import flask; print('OK')"
```

### MongoDB Connection Issues

```bash
# Check MongoDB health
docker compose exec mongo mongosh --eval "db.adminCommand('ping')"

# View MongoDB logs
docker compose logs mongo
```

### RabbitMQ Connection Issues

```bash
# Check RabbitMQ health
docker compose exec rabbitmq rabbitmq-diagnostics -q ping

# Access management UI
# http://your-server:15672 (user: user, pass: password)
```

### Caddy/HTTPS Issues

```bash
# Check Caddy logs
sudo journalctl -u caddy -f

# Test configuration
sudo caddy validate --config /etc/caddy/Caddyfile

# Check certificate status
sudo caddy trust
```

### Common Docker Commands

```bash
# Restart specific service
docker compose restart app

# Rebuild without cache
docker compose build --no-cache

# Remove all containers and volumes (CAUTION: deletes data)
docker compose down -v

# View resource usage
docker stats

# Access container shell
docker compose exec app /bin/sh
```

---

## Maintenance

### Backup MongoDB

```bash
# Create backup
docker compose exec mongo mongodump --out /backup

# Copy backup to host
docker cp studybuddy_mongo:/backup ./backup-$(date +%Y%m%d)
```

### Update Application

```bash
cd /opt/studybuddy
git pull
docker compose up -d --build
```

### View Logs

```bash
# Application logs
docker compose logs -f app

# All logs
docker compose logs -f

# DNS update logs
tail -f /var/log/update_dns.log

# Caddy logs
sudo tail -f /var/log/caddy/studybuddyai.log
```

---

## Quick Reference

| Service | Port | URL |
|---------|------|-----|
| Flask App | 5000 | http://localhost:5000 |
| MongoDB | 27017 | mongodb://localhost:27017 |
| RabbitMQ | 5672 | amqp://localhost:5672 |
| RabbitMQ UI | 15672 | http://localhost:15672 |
| Caddy (HTTP) | 80 | Redirects to HTTPS |
| Caddy (HTTPS) | 443 | https://studybuddyai.my |

---

**Happy Deploying! 🦫**
