#!/bin/bash
# =============================================================================
# StudyBuddy Network Access Helper
# =============================================================================
# This script helps enable network access to StudyBuddy from other computers
# It detects the firewall and opens port 5000 for development access
# =============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Detect if running as root
if [[ $EUID -eq 0 ]]; then
    SUDO=""
else
    SUDO="sudo"
fi

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_error() { echo -e "${RED}[✗]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $*"; }

show_banner() {
    clear
    echo -e "${GREEN}"
    cat << "EOF"
   _   _      _                      _      
  | \ | | ___| |___      _____  _ __| | __  
  |  \| |/ _ \ __\ \ /\ / / _ \| '__| |/ /  
  | |\  |  __/ |_ \ V  V / (_) | |  |   <   
  |_| \_|\___|\__| \_/\_/ \___/|_|  |_|\_\  
                                             
   _                             
  / \   ___ ___ ___  ___ ___     
 / _ \ / __/ __/ _ \/ __/ __|    
/ ___ \ (_| (_|  __/\__ \__ \    
/_/   \_\___\___\___||___/___/   
                                 
EOF
    echo -e "${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  StudyBuddy Network Access Helper${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo ""
}

get_server_ip() {
    # Try to get the main network IP (not localhost)
    local ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [[ -z "$ip" ]]; then
        ip=$(ip addr show | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | cut -d/ -f1 | head -1)
    fi
    echo "$ip"
}

check_app_running() {
    log_info "Checking if StudyBuddy is running..."
    
    if command -v docker &> /dev/null; then
        if docker ps | grep -q studybuddy_app; then
            log_success "StudyBuddy app container is running"
            return 0
        else
            log_warning "StudyBuddy app container is not running"
            log_info "Start it with: docker compose up -d"
            return 1
        fi
    else
        log_warning "Docker not found, skipping app check"
        return 0
    fi
}

check_port_listening() {
    log_info "Checking if port 5000 is listening..."
    
    if command -v netstat &> /dev/null; then
        if netstat -tuln 2>/dev/null | grep -q ":5000 "; then
            log_success "Port 5000 is listening"
            return 0
        fi
    elif command -v ss &> /dev/null; then
        if ss -tuln 2>/dev/null | grep -q ":5000 "; then
            log_success "Port 5000 is listening"
            return 0
        fi
    fi
    
    log_warning "Port 5000 is not listening"
    return 1
}

configure_ufw() {
    log_info "Configuring UFW firewall..."
    
    # Check if UFW is installed
    if ! command -v ufw &> /dev/null; then
        log_warning "UFW not installed"
        return 1
    fi
    
    # Check if UFW is active
    local ufw_status=$($SUDO ufw status 2>/dev/null | head -1)
    if ! echo "$ufw_status" | grep -q "Status: active"; then
        log_info "UFW is not active, no need to configure"
        return 0
    fi
    
    log_info "UFW is active, adding rule for port 5000..."
    
    # Add rule for port 5000
    if $SUDO ufw allow 5000/tcp comment 'StudyBuddy Development' 2>/dev/null; then
        log_success "Port 5000 added to UFW rules"
        
        # Show current rules
        echo ""
        log_info "Current UFW rules:"
        $SUDO ufw status numbered | grep 5000
        echo ""
        return 0
    else
        log_error "Failed to add UFW rule"
        return 1
    fi
}

configure_firewalld() {
    log_info "Configuring firewalld..."
    
    # Check if firewalld is installed
    if ! command -v firewall-cmd &> /dev/null; then
        log_warning "firewalld not installed"
        return 1
    fi
    
    # Check if firewalld is running
    if ! $SUDO firewall-cmd --state 2>/dev/null | grep -q "running"; then
        log_info "firewalld is not running, no need to configure"
        return 0
    fi
    
    log_info "firewalld is running, adding rule for port 5000..."
    
    # Add rule for port 5000
    if $SUDO firewall-cmd --permanent --add-port=5000/tcp 2>/dev/null; then
        $SUDO firewall-cmd --reload 2>/dev/null
        log_success "Port 5000 added to firewalld rules"
        
        # Show current rules
        echo ""
        log_info "Current firewalld ports:"
        $SUDO firewall-cmd --list-ports | grep 5000 || echo "  (port 5000 rule added but not visible in this output)"
        echo ""
        return 0
    else
        log_error "Failed to add firewalld rule"
        return 1
    fi
}

configure_iptables() {
    log_info "Checking iptables..."
    
    if ! command -v iptables &> /dev/null; then
        log_warning "iptables not installed"
        return 1
    fi
    
    # Check if port 5000 is already allowed
    if $SUDO iptables -L INPUT -n 2>/dev/null | grep -q "dpt:5000"; then
        log_success "Port 5000 is already allowed in iptables"
        return 0
    fi
    
    log_info "Adding iptables rule for port 5000..."
    
    if $SUDO iptables -A INPUT -p tcp --dport 5000 -j ACCEPT 2>/dev/null; then
        log_success "Port 5000 added to iptables rules"
        
        # Try to save the rules
        if command -v netfilter-persistent &> /dev/null; then
            if $SUDO netfilter-persistent save 2>/dev/null; then
                log_success "iptables rules saved with netfilter-persistent"
            else
                log_warning "Failed to save with netfilter-persistent"
            fi
        elif command -v iptables-save &> /dev/null; then
            # Create directory if it doesn't exist
            $SUDO mkdir -p /etc/iptables 2>/dev/null
            # Save rules to a temporary file first, then move
            if $SUDO iptables-save > /tmp/iptables-rules.v4 2>/dev/null; then
                if $SUDO mv /tmp/iptables-rules.v4 /etc/iptables/rules.v4 2>/dev/null; then
                    log_success "iptables rules saved"
                else
                    log_warning "Could not save iptables rules to /etc/iptables/rules.v4"
                    log_warning "Rule will be lost on reboot"
                fi
            else
                log_warning "Could not save iptables rules"
                log_warning "Rule will be lost on reboot"
            fi
        else
            log_warning "Could not save iptables rules permanently"
            log_warning "Rule will be lost on reboot"
        fi
        return 0
    else
        log_error "Failed to add iptables rule"
        return 1
    fi
}

detect_and_configure_firewall() {
    log_info "Detecting firewall configuration..."
    
    local configured=false
    
    # Try UFW first (most common on Ubuntu)
    if command -v ufw &> /dev/null; then
        if configure_ufw; then
            configured=true
        fi
    fi
    
    # Try firewalld (CentOS/RHEL/Fedora)
    if command -v firewall-cmd &> /dev/null && [[ "$configured" == false ]]; then
        if configure_firewalld; then
            configured=true
        fi
    fi
    
    # Try iptables as fallback
    if command -v iptables &> /dev/null && [[ "$configured" == false ]]; then
        if configure_iptables; then
            configured=true
        fi
    fi
    
    if [[ "$configured" == false ]]; then
        log_info "No common firewall detected or configuration not needed"
        log_info "Your system might not have a firewall enabled"
    fi
}

show_access_info() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  Access Information${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo ""
    
    local server_ip=$(get_server_ip)
    
    if [[ -n "$server_ip" ]]; then
        log_success "Your server's IP address: ${GREEN}$server_ip${NC}"
        echo ""
        log_info "Access your app from another computer:"
        echo ""
        echo -e "  ${GREEN}http://$server_ip:5000${NC}"
        echo ""
    else
        log_warning "Could not determine server IP address"
        log_info "Find your IP with: hostname -I"
    fi
    
    echo -e "${YELLOW}⚠️  Security Notice:${NC}"
    echo -e "  Port 5000 uses HTTP (not HTTPS) - traffic is not encrypted"
    echo -e "  Only use this for development/testing on trusted networks"
    echo ""
    echo -e "  For production, use: ${GREEN}./deploy-production.sh${NC}"
    echo -e "  This sets up HTTPS with Let's Encrypt on ports 80/443"
    echo ""
}

test_local_access() {
    log_info "Testing local access..."
    
    if command -v curl &> /dev/null; then
        if curl -s -f http://localhost:5000/health > /dev/null 2>&1; then
            log_success "App is accessible locally"
            return 0
        else
            log_warning "App is not responding on localhost:5000"
            log_info "Make sure the app is running: docker compose ps"
            return 1
        fi
    else
        log_warning "curl not installed, skipping local test"
        return 0
    fi
}

main() {
    show_banner
    
    # Step 1: Check if app is running
    check_app_running
    echo ""
    
    # Step 2: Check if port is listening
    check_port_listening
    echo ""
    
    # Step 3: Test local access
    test_local_access
    echo ""
    
    # Step 4: Configure firewall
    detect_and_configure_firewall
    echo ""
    
    # Step 5: Show access information
    show_access_info
    
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Done!${NC} Your app should now be accessible from other computers."
    echo ""
    log_info "Troubleshooting tips:"
    echo "  - Verify app is running: ${GREEN}docker compose ps${NC}"
    echo "  - View app logs: ${GREEN}docker compose logs -f app${NC}"
    echo "  - Test locally: ${GREEN}curl http://localhost:5000/health${NC}"
    echo "  - Check firewall: ${GREEN}sudo ufw status${NC}"
    echo ""
    log_info "For more help, see: ${GREEN}docs/NETWORK_ACCESS.md${NC}"
    echo ""
}

# Run main function
main
