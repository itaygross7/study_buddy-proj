#!/bin/bash
# =============================================================================
# Dynamic DNS Update Script for StudyBuddyAI
# =============================================================================
# Updates DNS A and AAAA records when public IP changes.
# Works with Hostinger API - modify for other providers as needed.
#
# Usage:
#   1. Copy this script to your server: /opt/studybuddy/scripts/update_dns.sh
#   2. Update API_KEY and ZONE_ID with your Hostinger credentials
#   3. Make executable: chmod +x update_dns.sh
#   4. Add to crontab: */5 * * * * /opt/studybuddy/scripts/update_dns.sh
#
# =============================================================================

# Configuration - UPDATE THESE VALUES
API_KEY="YOUR_HOSTINGER_API_KEY"
ZONE_ID="YOUR_HOSTINGER_ZONE_ID"
DOMAIN="studybuddyai.my"
RECORD_NAME="@"

# State and log files
STATE_DIR="/var/lib/update_dns"
LOG_FILE="/var/log/update_dns.log"

# Create directories if they don't exist
mkdir -p "$STATE_DIR"
touch "$LOG_FILE"

LAST_IPV4_FILE="$STATE_DIR/last_ipv4"
LAST_IPV6_FILE="$STATE_DIR/last_ipv6"

# =============================================================================
# Helper Functions
# =============================================================================

log() {
    local level="$1"
    shift
    local msg="$*"
    local timestamp
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[$timestamp] [$level] $msg" | tee -a "$LOG_FILE"
}

get_public_ipv4() {
    # Try multiple services for reliability
    curl -4 -s --connect-timeout 5 https://ipv4.icanhazip.com 2>/dev/null | tr -d '[:space:]' ||
    curl -4 -s --connect-timeout 5 https://api.ipify.org 2>/dev/null | tr -d '[:space:]' ||
    curl -4 -s --connect-timeout 5 https://ifconfig.me 2>/dev/null | tr -d '[:space:]'
}

get_public_ipv6() {
    curl -6 -s --connect-timeout 5 https://ipv6.icanhazip.com 2>/dev/null | tr -d '[:space:]' ||
    curl -6 -s --connect-timeout 5 https://api6.ipify.org 2>/dev/null | tr -d '[:space:]'
}

update_record() {
    local type="$1"
    local value="$2"
    local name="$3"

    if [[ -z "$value" ]]; then
        log "WARN" "Missing value for $type record"
        return 1
    fi

    # Validate IP format with proper octet range checking
    if [[ "$type" == "A" ]]; then
        local IFS='.'
        read -ra octets <<< "$value"
        if [[ ${#octets[@]} -ne 4 ]]; then
            log "ERROR" "Invalid IPv4 format: $value"
            return 1
        fi
        for octet in "${octets[@]}"; do
            if ! [[ "$octet" =~ ^[0-9]+$ ]] || [[ "$octet" -lt 0 ]] || [[ "$octet" -gt 255 ]]; then
                log "ERROR" "Invalid IPv4 octet in: $value"
                return 1
            fi
        done
    fi

    local http_code
    local response
    local temp_file
    temp_file=$(mktemp)
    
    http_code=$(curl -sS -w "%{http_code}" -o "$temp_file" \
        -X PUT "https://api.hostinger.com/v1/dns-zones/${ZONE_ID}/records/${type}" \
        --connect-timeout 10 \
        --max-time 30 \
        -H "Authorization: Bearer ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d "{
              \"name\": \"${name}\",
              \"value\": \"${value}\",
              \"ttl\": 300
            }" 2>&1)

    local exit_code=$?
    response=$(cat "$temp_file")
    rm -f "$temp_file"
    
    if [[ $exit_code -ne 0 ]]; then
        log "ERROR" "Failed to update $type record (exit $exit_code)"
        log "ERROR" "Response: ${response}"
        return $exit_code
    fi

    # Check HTTP status code (2xx = success)
    if [[ ! "$http_code" =~ ^2[0-9][0-9]$ ]]; then
        log "ERROR" "API returned HTTP $http_code: ${response}"
        return 1
    fi

    log "INFO" "Updated $type record to $value"
    log "DEBUG" "Response: ${response}"
    return 0
}

# =============================================================================
# Main Script
# =============================================================================

log "INFO" "===== DNS update start for ${DOMAIN} ====="

# Get current IPs
CURRENT_IPV4="$(get_public_ipv4)"
CURRENT_IPV6="$(get_public_ipv6)"

log "INFO" "Detected IPv4: ${CURRENT_IPV4:-none}"
log "INFO" "Detected IPv6: ${CURRENT_IPV6:-none}"

# Read last known IPs
LAST_IPV4=""
LAST_IPV6=""

[[ -f "$LAST_IPV4_FILE" ]] && LAST_IPV4="$(cat "$LAST_IPV4_FILE" 2>/dev/null)"
[[ -f "$LAST_IPV6_FILE" ]] && LAST_IPV6="$(cat "$LAST_IPV6_FILE" 2>/dev/null)"

log "DEBUG" "Last IPv4: ${LAST_IPV4:-none}"
log "DEBUG" "Last IPv6: ${LAST_IPV6:-none}"

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
else
    log "WARN" "No public IPv4 detected, skipping A record"
fi

# Update IPv6 (AAAA record) - Optional
if [[ -n "$CURRENT_IPV6" ]]; then
    if [[ "$CURRENT_IPV6" != "$LAST_IPV6" ]]; then
        log "INFO" "IPv6 changed: '${LAST_IPV6:-none}' -> '$CURRENT_IPV6'"
        if update_record "AAAA" "$CURRENT_IPV6" "$RECORD_NAME"; then
            echo "$CURRENT_IPV6" > "$LAST_IPV6_FILE"
        fi
    else
        log "INFO" "IPv6 unchanged ($CURRENT_IPV6), no AAAA update"
    fi
else
    log "WARN" "No public IPv6 detected, skipping AAAA record"
fi

log "INFO" "===== DNS update finished for ${DOMAIN} ====="
exit 0
