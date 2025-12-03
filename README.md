# StudyBuddyAI 🦫

**[studybuddyai.my](https://studybuddyai.my) - לומדים יחד עם אבנר**

StudyBuddyAI is a comprehensive web application designed to help students with their learning journey using generative AI. Meet Avner, your friendly capybara study buddy who's always ready to help!

## ✨ Features

### Learning Tools
- **📝 Interactive Summarizer**: Condense long texts or documents into key points
- **🃏 Flashcards Generator**: Automatically create Q&A flashcards from study materials
- **✅ Assess-Me Quiz Builder**: Generate quizzes to test your knowledge
- **📚 Homework Helper**: Get step-by-step explanations for difficult problems
- **🦫 Ask Avner**: Chat with Avner for tips, help, and questions about your material

### Platform Features
- **👤 User Authentication**: Secure login/signup with email verification
- **👑 Admin Dashboard**: Full control over users, settings, and system configuration
- **📧 Email Notifications**: Verification emails and admin alerts
- **📱 Responsive Design**: Beautiful cozy UI that works on desktop and mobile
- **📄 PDF Export**: Save flashcards and summaries for offline use

## 🛠️ Tech Stack

- **Backend**: Python 3.11, Flask, Flask-Login
- **Frontend**: HTMX, TailwindCSS
- **AI Integration**: OpenAI (GPT series), Google (Gemini Pro)
- **Database**: MongoDB
- **Task Queue**: RabbitMQ
- **Containerization**: Docker & Docker Compose
- **Security**: bcrypt password hashing, CSRF protection, secure sessions

---

## 🚀 Quick Start (Ubuntu 22.04 / Ubuntu 20.04+ / Linux)

### Production Deployment (Recommended for Production Servers)

**Complete production setup with HTTPS, Tailscale, and auto-updates!**

```bash
# Clone the repository
git clone https://github.com/itaygross7/study_buddy-proj.git
cd study_buddy-proj

# Configure your environment
cp .env.example .env
nano .env  # Add your domain, API keys, etc.

# Run the production deployment script
./deploy-production.sh
```

**The production script automatically:**
- ✅ Installs Docker and Docker Compose if missing
- ✅ Installs and configures Tailscale for secure access
- ✅ Sets up HTTPS with Let's Encrypt (automatic certificates)
- ✅ Configures firewall (SSH only via Tailscale, HTTPS public)
- ✅ Creates systemd service for auto-restart on failure
- ✅ Sets up auto-update system (manual, cron, or webhook)
- ✅ Generates secure SECRET_KEY automatically
- ✅ Builds and starts all services
- ✅ Validates HTTPS is working

**Perfect for:**
- Production servers with a domain name
- Secure deployments (SSH via Tailscale only)
- Hands-off maintenance (auto-restart, auto-updates)

See `docs/DEPLOYMENT.md` and `docs/OAUTH_EMAIL_SETUP.md` for details.

---

### Quick Development Deployment

**For testing or development without HTTPS:**

```bash
# Clone the repository
git clone https://github.com/itaygross7/study_buddy-proj.git
cd study_buddy-proj

# Run as root (or regular user with sudo access)
./deploy.sh
```

**The dev script automatically:**
- ✅ Detects and installs Docker if missing
- ✅ Detects and installs Docker Compose if missing
- ✅ Fixes Docker daemon if not running
- ✅ Clears port conflicts automatically
- ✅ Fixes network and DNS issues
- ✅ Generates secure SECRET_KEY automatically
- ✅ Cleans up disk space if needed
- ✅ Creates .env from template
- ✅ Builds and starts all services
- ✅ Validates deployment is working

**Can be run as:**
- Root: `./deploy.sh` (full system access, installs missing dependencies)
- User: `./deploy.sh` (uses sudo when needed)

**Tested on**: Ubuntu 22.04 LTS (also works on Ubuntu 20.04+, Debian, and other Linux distributions with Docker)

**Script Options:**
```bash
./deploy.sh --check-only   # Only run system checks
./deploy.sh --rebuild      # Force rebuild of images
./deploy.sh --help         # Show all options
```

### Manual Installation

If you prefer manual setup or need more control:

#### Prerequisites

1. **Install Docker and Docker Compose:**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   
   # Add your user to docker group
   sudo usermod -aG docker $USER
   newgrp docker
   
   # Install Docker Compose
   sudo apt install docker-compose -y
   ```

2. **Get an AI API Key:**
   - [Google AI Studio](https://makersuite.google.com/app/apikey) for Gemini (recommended, free tier available)
   - OR [OpenAI API](https://platform.openai.com/api-keys) for GPT

#### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/itaygross7/study_buddy-proj.git
   cd study_buddy-proj
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your settings
   ```
   
   **Required settings in `.env`:**
   ```bash
   # Your AI API key (at least one required)
   GEMINI_API_KEY="your_gemini_api_key_here"
   
   # IMPORTANT: Change this to a secure random string!
   SECRET_KEY="generate-a-secure-random-key-here"
   
   # Your admin email (you'll have full admin access)
   ADMIN_EMAIL="your_email@example.com"
   
   # Optional: Set initial admin password (admin will be created on startup)
   # If not set, you need to sign up with ADMIN_EMAIL to become admin
   ADMIN_PASSWORD="your_secure_admin_password"
   ```
   
   **Generate a secure secret key:**
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

3. **Start the application:**
   ```bash
   docker-compose up -d --build
   ```

4. **Access the app:**
   - Open your browser to `http://your-server-ip:5000`
   - Sign up with your admin email to get admin access
   - Check your email to verify your account (if email is configured)

## Dynamic DNS Support (for Home Servers)

If you have a dynamic IP address (home server, residential connection), the deployment works seamlessly with the included DNS updater script.

### Your Existing Cron Job

The deployment script **does NOT interfere** with your existing `update_dns.sh` cron job. They work together:

- **`update_dns.sh`** (cron job) - Keeps your DNS updated when IP changes
- **`deploy.sh`** - Deploys the application and sets up HTTPS

### Setup DNS Updater (if not already done)

```bash
# Easy setup helper
./scripts/setup-dns-updater.sh
```

Or manually:

```bash
# 1. Edit the script with your credentials
nano scripts/update_dns.sh
# Set: API_KEY, ZONE_ID, DOMAIN

# 2. Make it executable
chmod +x scripts/update_dns.sh

# 3. Add to crontab (runs every 5 minutes)
crontab -e
# Add: */5 * * * * /path/to/study_buddy-proj/scripts/update_dns.sh
```

### How They Work Together

1. **DNS Updater** runs every 5 minutes via cron
   - Detects if your public IP changed
   - Updates DNS A/AAAA records automatically
   - Works with Hostinger API (or modify for other providers)

2. **Deployment** uses the domain from your `.env`
   - Verifies DNS points to your server
   - Sets up HTTPS with Caddy
   - Configures Let's Encrypt SSL

**Result**: Your site is always accessible at your domain, even when IP changes!

---

1. **Install Nginx and Certbot:**
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx -y
   ```

2. **Configure Nginx** (`/etc/nginx/sites-available/studybuddy`):
   ```nginx
   server {
       listen 80;
       server_name studybuddyai.my www.studybuddyai.my;
       
       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. **Enable the site and get SSL certificate:**
   ```bash
   sudo ln -s /etc/nginx/sites-available/studybuddy /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   sudo certbot --nginx -d studybuddyai.my -d www.studybuddyai.my
   ```

4. **Update `.env` for HTTPS:**
   ```bash
   DOMAIN="studybuddyai.my"
   BASE_URL="https://studybuddyai.my"
   SESSION_COOKIE_SECURE=true
   ```

---

## 📧 Email Configuration (Optional but Recommended)

To enable email verification and admin notifications:

1. **Using Gmail:**
   - Enable 2-Factor Authentication on your Google account
   - Generate an App Password: Google Account → Security → App Passwords
   - Add to `.env`:
     ```bash
     MAIL_SERVER="smtp.gmail.com"
     MAIL_PORT=587
     MAIL_USE_TLS=true
     MAIL_USERNAME="your_email@gmail.com"
     MAIL_PASSWORD="your_app_password"
     MAIL_DEFAULT_SENDER="StudyBuddy <your_email@gmail.com>"
     ```

2. **Using other SMTP providers:**
   - Update `MAIL_SERVER` and `MAIL_PORT` accordingly
   - Common options: SendGrid, Mailgun, Amazon SES

---

## 👑 Admin Features

Once logged in with your admin email, you can access:

- **Admin Dashboard** (`/admin/`): View statistics and recent users
- **User Management** (`/admin/users`): View, activate/deactivate, or delete users
- **System Config** (`/admin/config`): Configure:
  - Daily prompt limits per user
  - Maximum file upload size
  - Default number of flashcards/questions
  - Enable/disable specific modules
  - Maintenance mode

---

## 🔧 Management Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app
docker-compose logs -f worker

# Stop all services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# View running containers
docker-compose ps

# Access MongoDB shell
docker exec -it studybuddy_mongo mongosh studybuddy

# Backup MongoDB data
docker exec studybuddy_mongo mongodump --out /backup
docker cp studybuddy_mongo:/backup ./backup
```

---

## 📂 Project Structure

```
study_buddy-proj/
├── app.py              # Main Flask application
├── worker.py           # Background task worker
├── docker-compose.yml  # Docker services configuration
├── Dockerfile          # App container definition
├── .env.example        # Environment template
├── src/
│   ├── api/            # API routes (auth, admin, tools)
│   ├── domain/         # Data models
│   ├── services/       # Business logic & AI clients
│   └── infrastructure/ # Database, config, repositories
├── ui/
│   ├── templates/      # HTML templates
│   ├── static/         # CSS, JS, images
│   └── Avner/          # Avner mascot images
├── sb_utils/           # Shared utilities
└── tests/              # Test suite
```

---

## 🔐 Security Features

- **Password Hashing**: bcrypt with secure salt
- **Session Security**: HTTPOnly, Secure, SameSite cookies
- **Email Verification**: Required before login
- **Admin Alerts**: Email notifications for errors and new users
- **Input Validation**: Pydantic models for all API requests
- **CSRF Protection**: Built into Flask forms
- **Rate Limiting**: Configurable daily prompt limits

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Happy Studying with Avner! 🦫**
