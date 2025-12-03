# StudyBuddy Monitoring Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Public Internet                          │
│                                                              │
│  ┌──────────────┐                    ┌──────────────┐      │
│  │ HTTPS Client │────────────────────▶│ Port 443     │      │
│  └──────────────┘                    │ (Caddy)      │      │
│                                       └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │      Docker Network                               │
                    │                          │                         │
                    │  ┌───────────────────────▼──────────────────┐    │
                    │  │  Caddy Reverse Proxy                      │    │
                    │  │  - HTTPS/TLS termination                  │    │
                    │  │  - Let's Encrypt auto-renewal             │    │
                    │  └───────────────────────┬──────────────────┘    │
                    │                          │                         │
                    │  ┌───────────────────────▼──────────────────┐    │
                    │  │  Flask App (studybuddy_app)               │    │
                    │  │  ┌─────────────────────────────────────┐  │    │
                    │  │  │ Health Endpoints:                   │  │    │
                    │  │  │  - /health           (basic)        │  │    │
                    │  │  │  - /health/detailed  (components)   │  │    │
                    │  │  │  - /health/live      (liveness)     │  │    │
                    │  │  │  - /health/ready     (readiness)    │  │    │
                    │  │  └─────────────────────────────────────┘  │    │
                    │  └───────────────────────┬──────────────────┘    │
                    │                          │                         │
                    │  ┌───────────────────────▼──────────────────┐    │
                    │  │  Health Monitor Container                 │    │
                    │  │  ┌─────────────────────────────────────┐  │    │
                    │  │  │ Monitors (every 30s):               │  │    │
                    │  │  │  - App health (/health)             │  │    │
                    │  │  │  - Component health (/health/detail)│  │    │
                    │  │  │  - MongoDB container                │  │    │
                    │  │  │  - RabbitMQ container               │  │    │
                    │  │  │                                      │  │    │
                    │  │  │ Actions on failure (3+ times):      │  │    │
                    │  │  │  - Restart failed component         │  │    │
                    │  │  │  - Log to healthcheck.log           │  │    │
                    │  │  └─────────────────────────────────────┘  │    │
                    │  └──────────────────────────────────────────┘    │
                    │                                                    │
                    │  ┌────────────────────┐  ┌──────────────────┐   │
                    │  │  MongoDB           │  │  RabbitMQ        │   │
                    │  │  - Health checks   │  │  - Health checks │   │
                    │  │  - Persistent data │  │  - Message queue │   │
                    │  └────────────────────┘  └──────────────────┘   │
                    └────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Tailscale Network (Private)                    │
│                                                              │
│  ┌──────────────┐                    ┌──────────────┐      │
│  │ SSH Client   │────────────────────▶│ Port 22      │      │
│  │ (via TS IP)  │                    │ (SSH only)   │      │
│  └──────────────┘                    └──────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Monitoring Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  Health Check Flow                           │
└─────────────────────────────────────────────────────────────┘

1. Health Monitor Container starts
   │
   ├─▶ Every 30 seconds:
   │   │
   │   ├─▶ Check /health endpoint
   │   │   ├─ Success → Reset failure counter
   │   │   └─ Failure → Increment counter
   │   │       └─ If counter ≥ 3 → Restart app
   │   │
   │   ├─▶ Check /health/detailed
   │   │   ├─ Parse component status
   │   │   └─ Log any unhealthy components
   │   │
   │   ├─▶ Check MongoDB container
   │   │   ├─ Success → Reset failure counter
   │   │   └─ Failure → Increment counter
   │   │       └─ If counter ≥ 3 → Restart mongo
   │   │
   │   └─▶ Check RabbitMQ container
   │       ├─ Success → Reset failure counter
   │       └─ Failure → Increment counter
   │           └─ If counter ≥ 3 → Restart rabbitmq
   │
   └─▶ Log all actions to /var/log/studybuddy-healthcheck.log
```

## Component Health Checks

```
┌─────────────────────────────────────────────────────────────┐
│               /health/detailed Response                      │
└─────────────────────────────────────────────────────────────┘

{
  "status": "healthy" | "unhealthy",
  "timestamp": 1733238000,
  "components": {
    "mongodb": {
      "status": "healthy",
      "message": "Connected"
    },
    "rabbitmq": {
      "status": "healthy",
      "message": "Connected"
    },
    "ai_service": {
      "status": "healthy",
      "message": "API keys configured"
    },
    "email_service": {
      "status": "degraded",
      "message": "SMTP not configured (optional)"
    }
  }
}
```

## Manual Operations

```
┌─────────────────────────────────────────────────────────────┐
│                  Manual Management                           │
└─────────────────────────────────────────────────────────────┘

Restart Application:
  ./scripts/restart-app.sh [component] [--rebuild]
  │
  ├─▶ Detects systemd or docker compose
  ├─▶ Restarts service/container
  ├─▶ Waits for startup
  └─▶ Runs health check

Test API Endpoints:
  ./scripts/test-api-endpoints.sh
  │
  ├─▶ Tests health check endpoints
  ├─▶ Tests UI routes (/, /auth/login, etc)
  ├─▶ Tests API routes (/api/avner/*, /webhook/*)
  ├─▶ Tests error handling (404s)
  └─▶ Reports pass/fail summary

Manual Health Check:
  curl http://localhost:5000/health/detailed
  │
  └─▶ Returns component-level health status
```

## Systemd Integration

```
┌─────────────────────────────────────────────────────────────┐
│              Systemd Service Architecture                    │
└─────────────────────────────────────────────────────────────┘

studybuddy.service
  │
  ├─▶ Starts: docker compose up -d --build
  ├─▶ Stops: docker compose down
  ├─▶ Restart: on-failure (10s delay)
  ├─▶ Resources: CPU 95%, RAM 4G
  │
  └─▶ All containers:
      ├─ studybuddy_app
      ├─ studybuddy_worker
      ├─ studybuddy_mongo
      ├─ studybuddy_rabbitmq
      ├─ studybuddy_caddy
      └─ studybuddy_healthcheck

studybuddy-healthcheck.service (optional)
  │
  ├─▶ Starts: ./scripts/health-monitor.sh
  ├─▶ Restart: always (10s delay)
  └─▶ Requires: studybuddy.service
```

## Firewall Configuration

```
┌─────────────────────────────────────────────────────────────┐
│                   UFW Firewall Rules                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────┬──────────────┬─────────────────────┐
│ Port                │ Allow From   │ Purpose             │
├─────────────────────┼──────────────┼─────────────────────┤
│ 22 (SSH)            │ Tailscale    │ Server management   │
│ 80 (HTTP)           │ Anywhere     │ Let's Encrypt       │
│ 443 (HTTPS)         │ Anywhere     │ Web application     │
│ 41641 (UDP)         │ Anywhere     │ Tailscale           │
└─────────────────────┴──────────────┴─────────────────────┘

Default policy: Deny incoming, Allow outgoing
```

## Auto-Update Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  Auto-Update Process                         │
└─────────────────────────────────────────────────────────────┘

GitHub Push to main
  │
  ├─▶ Triggers webhook (if configured)
  │   └─▶ POST /webhook/update (with HMAC signature)
  │
  └─▶ scripts/auto-update.sh
      │
      ├─▶ 1. Stash local changes
      ├─▶ 2. Fetch from origin
      ├─▶ 3. Check for updates
      ├─▶ 4. Backup .env file
      ├─▶ 5. Pull changes
      ├─▶ 6. Restore .env
      ├─▶ 7. Rebuild if needed
      ├─▶ 8. Restart application
      │   └─▶ systemctl restart studybuddy
      │       OR
      │       docker compose up -d
      ├─▶ 9. Wait for healthy
      └─▶ 10. Verify with health check
```

## Key Features

### Health Monitoring
- ✅ Continuous monitoring (30s intervals)
- ✅ Component-level health checks
- ✅ Automatic restart on failure
- ✅ Configurable thresholds
- ✅ Comprehensive logging

### Restart Options
- ✅ Manual restart script
- ✅ Component-specific restart
- ✅ Rebuild option
- ✅ Post-restart verification
- ✅ Systemd integration

### API Testing
- ✅ All endpoints tested
- ✅ Health checks verified
- ✅ UI routes validated
- ✅ API routes checked
- ✅ Error handling confirmed

### Security
- ✅ SSH via Tailscale only
- ✅ HTTPS for web traffic
- ✅ Firewall configured
- ✅ Webhook signature verification
- ✅ Resource limits

### Reliability
- ✅ Auto-restart on failure
- ✅ Health checks at multiple levels
- ✅ Automatic updates
- ✅ Rollback on error
- ✅ Persistent monitoring
