# Auto-Deployment Setup Guide

This guide shows you how to enable automatic deployment for StudyBuddy. When you push code to the `main` branch, it will automatically deploy to your production server.

## Setup Methods

### Method 1: Webhook (Recommended) ⚡

This is the fastest method - deployments happen in seconds!

#### Step 1: Generate Webhook Secret
```bash
openssl rand -hex 32
```
Copy the output.

#### Step 2: Configure GitHub Secrets
1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions
3. Add these secrets:
   - `WEBHOOK_URL`: Your server URL (e.g., `https://studybuddyai.my`)
   - `WEBHOOK_SECRET`: The secret you generated above

#### Step 3: Configure Server
1. SSH into your server
2. Edit your `.env` file:
   ```bash
   nano .env
   ```
3. Add the webhook secret:
   ```bash
   WEBHOOK_SECRET="your_secret_here"
   ```
4. Restart the application:
   ```bash
   docker compose restart app
   ```

#### Step 4: Test
Push a commit to `main` branch and check GitHub Actions!

---

### Method 2: SSH Deployment 🔑

If webhooks don't work (firewall issues, etc.), use SSH deployment.

#### Step 1: Generate SSH Key
On your **local machine** (not the server):
```bash
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_deploy_key
```

#### Step 2: Add Public Key to Server
```bash
# Copy the public key
cat ~/.ssh/github_deploy_key.pub

# SSH to your server
ssh user@your-server.com

# Add key to authorized_keys
mkdir -p ~/.ssh
nano ~/.ssh/authorized_keys
# Paste the public key, save and exit
```

#### Step 3: Configure GitHub Secrets
1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions
3. Add these secrets:
   - `SSH_HOST`: Your server IP or domain
   - `SSH_USER`: Your SSH username (e.g., `root` or `ubuntu`)
   - `SSH_KEY`: Contents of `~/.ssh/github_deploy_key` (the PRIVATE key)
   - `SSH_PORT`: SSH port (default: 22)
   - `DEPLOY_PATH`: Path where StudyBuddy is installed (e.g., `/opt/studybuddy`)

#### Step 4: Test
Push a commit to `main` branch and check GitHub Actions!

---

## Verify Setup

### Check GitHub Actions
1. Go to your repository on GitHub
2. Click "Actions" tab
3. You should see workflow runs on each push to main

### Check Server Logs
```bash
# View auto-update logs
tail -f /var/log/studybuddy-update.log

# View application logs
docker compose logs -f app
```

### Manual Trigger
You can manually trigger deployment:
1. Go to Actions tab on GitHub
2. Select "Auto-Deploy to Production"
3. Click "Run workflow"

---

## Troubleshooting

### Webhook not working?
- Check firewall allows incoming connections
- Verify `WEBHOOK_SECRET` matches in GitHub and server `.env`
- Check webhook endpoint: `curl https://your-domain.com/webhook/health`

### SSH deployment not working?
- Verify SSH key has no passphrase
- Check server allows key-based authentication
- Verify `DEPLOY_PATH` is correct

### Deployment succeeds but app not updating?
- Check if `auto-update.sh` has execute permissions:
  ```bash
  chmod +x scripts/auto-update.sh
  ```
- Check log file: `cat /var/log/studybuddy-update.log`

---

## Security Notes

- Never commit secrets to git!
- Use strong webhook secrets (32+ characters)
- Limit SSH key permissions (use dedicated deploy user)
- Keep `.env` file secure on server
- Review auto-update logs regularly

---

## What Gets Deployed?

The auto-deployment:
1. Pulls latest code from `main` branch
2. Preserves your `.env` configuration
3. Rebuilds containers if needed (Dockerfile/requirements changed)
4. Restarts the application
5. Verifies health after deployment
6. Logs everything to `/var/log/studybuddy-update.log`

**Your data is safe** - MongoDB and RabbitMQ data persists across updates!
