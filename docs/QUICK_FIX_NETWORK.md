# Quick Fix: Can't Access App from Another Computer

## The Problem
Your app is running, but you can't connect to it from a different computer on the same network.

## The Solution (3 Steps)

### Step 1: Run the Helper Script
```bash
./scripts/enable-network-access.sh
```

### Step 2: Get Your Server IP
```bash
hostname -I | awk '{print $1}'
```

### Step 3: Access from Another Computer
Open your browser and go to:
```
http://YOUR_SERVER_IP:5000
```

For example: `http://192.168.1.100:5000`

## Manual Fix (If Script Doesn't Work)

### For Ubuntu/Debian (UFW)
```bash
sudo ufw allow 5000/tcp
sudo ufw status
```

### For CentOS/RHEL/Fedora (firewalld)
```bash
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

## Still Not Working?

### Check if app is running:
```bash
docker compose ps
```

### Check if port is listening:
```bash
sudo netstat -tuln | grep 5000
```

### Test local access:
```bash
curl http://localhost:5000/health
```

### View logs:
```bash
docker compose logs -f app
```

## For Production Use

⚠️ **Port 5000 is not secure for production** (no HTTPS)

For production deployment with HTTPS:
```bash
./deploy-production.sh
```

This sets up:
- ✅ Automatic HTTPS with Let's Encrypt
- ✅ Standard ports 80/443
- ✅ Proper security headers
- ✅ Firewall configuration
- ✅ Tailscale for secure SSH

## Need More Help?

See the complete guide: [`docs/NETWORK_ACCESS.md`](./NETWORK_ACCESS.md)
