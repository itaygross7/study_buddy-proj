# Complete Production Deployment Guide

This guide walks you through deploying StudyBuddy to your Ubuntu server with HTTPS, Tailscale, and auto-updates.

## Quick Start (One Command!)

```bash
git clone https://github.com/itaygross7/study_buddy-proj.git
cd study_buddy-proj
cp .env.example .env
nano .env  # Configure your settings
./deploy-production.sh
```

See `docs/OAUTH_EMAIL_SETUP.md` for email and OAuth setup.

Happy studying! 🦫
