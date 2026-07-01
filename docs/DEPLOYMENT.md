# StudyBuddy Deployment Guide

Canonical deployment reference for StudyBuddyAI. For script details see [SCRIPTS_GUIDE.md](../SCRIPTS_GUIDE.md).

## Quick start

### Local / home network (testing)

```bash
cp .env.example .env   # first time only — edit API keys
./start-local.sh
```

Access: `http://localhost:5000` or `http://YOUR_IP:5000` (shown by the script).

See [LOCAL_NETWORK_ACCESS.md](LOCAL_NETWORK_ACCESS.md) for phone/tablet access and firewall notes.

### Production (HTTPS + domain)

```bash
cp .env.example .env
nano .env                # DOMAIN, BASE_URL, API keys, SECRET_KEY
./deploy-production.sh
```

See [OAUTH_EMAIL_SETUP.md](OAUTH_EMAIL_SETUP.md) for Google/Apple sign-in and email.

### Quick smoke test

```bash
./deploy-simple.sh
```

---

## Docker Compose (manual)

```bash
docker compose down
docker compose up --build -d
docker compose logs -f web
```

Health check:

```bash
curl http://localhost:5000/health
curl http://localhost:5000/health/detailed
```

---

## CSS / frontend assets

The browser loads compiled `ui/static/css/styles.css`. Source is `ui/static/css/input.css`.

**Docker builds compile CSS automatically** in the Dockerfile. If you deploy without Docker:

```bash
npm install
npm run tailwind:build
```

Verify:

```bash
ls -lh ui/static/css/styles.css
```

---

## Environment

Required in `.env`:

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Session security |
| `MONGO_URI` | MongoDB connection |
| `RABBITMQ_URI` | Task queue |
| `OPENAI_API_KEY` or `GEMINI_API_KEY` | At least one AI provider |

Run `python check_config.py` to validate configuration.

---

## Verify deployment

```bash
./verify-deployment.sh
```

---

## Troubleshooting

| Issue | Action |
|-------|--------|
| Permission / Docker / auto-update failures | `./deploy-hard-restart.sh` — see [HARD_RESTART_GUIDE.md](HARD_RESTART_GUIDE.md) |
| Network access from other devices | [LOCAL_NETWORK_ACCESS.md](LOCAL_NETWORK_ACCESS.md) |
| OAuth / email | [OAUTH_EMAIL_SETUP.md](OAUTH_EMAIL_SETUP.md) |
| General errors | [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) |

---

## Deprecated scripts

Old deploy scripts (`deploy.sh`, `deploy-auto-fix.sh`, `deploy-check-only.sh`) live in `scripts/deprecated/`. Use `deploy-production.sh`, `deploy-simple.sh`, or `start-local.sh` instead.
