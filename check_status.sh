#!/usr/bin/env bash

# Simple StudyBuddy status dashboard
# Usage: ./check_status.sh [TAIL_LINES]
# Default tail lines = 40

TAIL_LINES="${1:-40}"

print_section() {
  echo
  echo "============================================================"
  echo "== $1"
  echo "============================================================"
}

# --- Docker containers ---
print_section "DOCKER CONTAINERS (studybuddy*)"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "studybuddy|study_buddy_proj" || echo "No studybuddy containers found"

# --- App health (simple) ---
print_section "APP HEALTH (/health)"
if curl -fsS "http://localhost:5000/health" >/tmp/sb_health_simple.json 2>/dev/null; then
  cat /tmp/sb_health_simple.json
  echo
else
  echo "Failed to reach http://localhost:5000/health"
fi

# --- App health (detailed) ---
print_section "APP HEALTH DETAILED (/health/detailed)"
if curl -fsS "http://localhost:5000/health/detailed" >/tmp/sb_health_detailed.json 2>/dev/null; then
  if command -v jq >/dev/null 2>&1; then
    jq . /tmp/sb_health_detailed.json
  else
    echo "(jq not installed, showing raw JSON)"
    cat /tmp/sb_health_detailed.json
  fi
  echo
else
  echo "Failed to reach http://localhost:5000/health/detailed"
fi

# --- Worker logs ---
print_section "WORKER LOGS (last ${TAIL_LINES} lines)"
if docker ps -a --format '{{.Names}}' | grep -q '^studybuddy_worker$'; then
  docker logs --tail "$TAIL_LINES" studybuddy_worker 2>&1 || echo "Failed to read worker logs"
else
  echo "Container 'studybuddy_worker' not found"
fi

# --- Health monitor logs ---
print_section "HEALTH MONITOR LOGS (last ${TAIL_LINES} lines)"
if docker ps -a --format '{{.Names}}' | grep -q '^studybuddy_health_monitor$'; then
  docker logs --tail "$TAIL_LINES" studybuddy_health_monitor 2>&1 || echo "Failed to read health monitor logs"
else
  echo "Container 'studybuddy_health_monitor' not found"
fi

echo
echo "✅ check_status.sh finished."
