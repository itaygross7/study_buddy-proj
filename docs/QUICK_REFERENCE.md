# Quick Reference: Deployment Scripts

## 🚀 One-Line Deploy
```bash
./deploy.sh
```

## Common Commands

| Command | Purpose |
|---------|---------|
| `./deploy.sh` | Deploy with all checks |
| `./deploy.sh --check-only` | Only run system checks |
| `./deploy.sh --rebuild` | Force rebuild images |
| `./deploy.sh --clean` | Fresh start (deletes data!) |
| `./scripts/pre-deploy-check.sh` | Run checks manually |

## What Gets Checked

✅ Docker & Docker Compose  
✅ Ports (5000, 27017, 5672, 15672)  
✅ Network & DNS  
✅ .env configuration  
✅ Disk space & memory  
✅ Docker network health  

## Required .env Variables

```bash
SECRET_KEY="..."           # Generate: python3 -c "import secrets; print(secrets.token_hex(32))"
ADMIN_EMAIL="..."         # Your email
GEMINI_API_KEY="..."      # Or OPENAI_API_KEY
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port in use | `sudo lsof -i :5000` then stop service |
| Docker not running | `sudo systemctl start docker` |
| Out of disk | `docker system prune -a` |
| .env missing | `cp .env.example .env` |

## After Deployment

```bash
# Check status
docker compose ps

# View logs
docker compose logs -f app

# Test health
curl http://localhost:5000/health

# Stop services
docker compose down
```

## Access Points

- **App**: http://localhost:5000
- **RabbitMQ UI**: http://localhost:15672

## Documentation

- Full guide: `docs/DEPLOYMENT_SCRIPTS.md`
- Deployment: `docs/DEPLOYMENT.md`
- Main README: `README.md`
