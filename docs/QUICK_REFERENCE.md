# Quick Reference: Deployment Scripts

## One-line deploy

```bash
./deploy-production.sh    # production with HTTPS
./deploy-simple.sh          # quick local test
./start-local.sh            # home network access
```

## Common commands

| Command | Purpose |
|---------|---------|
| `./deploy-production.sh` | Production deploy with checks |
| `./deploy-simple.sh` | Simple Docker Compose up |
| `./start-local.sh` | Local network testing |
| `./deploy-hard-restart.sh` | Emergency restart + permission fixes |
| `./scripts/pre-deploy-check.sh` | Run checks manually |

## What gets checked

- Docker and Docker Compose
- Ports (5000, 27017, 5672, 15672)
- Network and DNS
- `.env` configuration
- Disk space and memory
- Docker network health

## Deprecated

Old scripts are in `scripts/deprecated/`. See [SCRIPTS_GUIDE.md](../SCRIPTS_GUIDE.md).

## Health and logs

```bash
curl http://localhost:5000/health
docker compose logs -f web
docker compose logs -f worker
```

## Full guides

- [DEPLOYMENT.md](DEPLOYMENT.md)
- [SCRIPTS_GUIDE.md](../SCRIPTS_GUIDE.md)
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
