#!/usr/bin/env bash
# Claude-Shield POSIX Remediation & Hardening (macOS/Linux)

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}  Claude-Shield POSIX Remediation & Hardening${NC}"
echo -e "${CYAN}====================================================${NC}"
echo ""

REMEDIATIONS_APPLIED=0

# Helper for prompting
prompt_confirm() {
    read -r -p "$1 [y/N] " response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            true
            ;;
        *)
            false
            ;;
    esac
}

# 1. Disable Telemetry
if prompt_confirm "Set DISABLE_TELEMETRY=1 in ~/.bashrc and ~/.zshrc?"; then
    for profile in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.bash_profile"; do
        if [ -f "$profile" ]; then
            if ! grep -q "export DISABLE_TELEMETRY=1" "$profile"; then
                echo -e "\nexport DISABLE_TELEMETRY=1" >> "$profile"
                echo -e "${GREEN}[+ SUCCESS] Added DISABLE_TELEMETRY=1 to $profile${NC}"
                ((REMEDIATIONS_APPLIED++))
            else
                echo -e "${YELLOW}[i] DISABLE_TELEMETRY=1 already exists in $profile${NC}"
            fi
        fi
    done
fi

# 2. Reset Device Fingerprint in ~/.claude.json
CLAUDE_JSON="$HOME/.claude.json"
if [ -f "$CLAUDE_JSON" ]; then
    if prompt_confirm "Backup ~/.claude.json and reset userID/deviceId fingerprint?"; then
        cp "$CLAUDE_JSON" "$CLAUDE_JSON.bak"
        echo -e "${YELLOW}[i] Created backup at $CLAUDE_JSON.bak${NC}"
        
        # Use python to safely modify JSON
        if command -v python3 &>/dev/null; then
            python3 -c "
import json, os
path = os.path.expanduser('~/.claude.json')
try:
    with open(path, 'r') as f: data = json.load(f)
    modified = False
    if 'userID' in data:
        del data['userID']
        modified = True
    if 'deviceId' in data:
        del data['deviceId']
        modified = True
    if modified:
        with open(path, 'w') as f: json.dump(data, f, indent=2)
        print('${GREEN}[+ SUCCESS] Reset device fingerprint fields in ~/.claude.json${NC}')
    else:
        print('${YELLOW}[i] No userID or deviceId found in ~/.claude.json${NC}')
except Exception as e:
    print(f'${RED}[- ERROR] Failed to parse/write json: {e}${NC}')
"
            ((REMEDIATIONS_APPLIED++))
        else
            echo -e "${RED}[- ERROR] Python3 is required to safely modify JSON. Please edit manually.${NC}"
        fi
    fi
fi

# 3. Clear Telemetry Cache
TELEMETRY_DIR="$HOME/.claude/telemetry"
if [ -d "$TELEMETRY_DIR" ]; then
    if prompt_confirm "Clear telemetry cache in ~/.claude/telemetry/?"; then
        rm -rf "$TELEMETRY_DIR"/*
        echo -e "${GREEN}[+ SUCCESS] Cleared cached telemetry files from $TELEMETRY_DIR${NC}"
        ((REMEDIATIONS_APPLIED++))
    fi
fi

# 4. Disable Physical IPv6
if prompt_confirm "Disable IPv6 on physical network adapters? (Requires sudo)"; then
    if [ "$(uname)" == "Darwin" ]; then
        # macOS
        # Get active physical interfaces (e.g. en0)
        INTERFACES=$(networksetup -listallhardwareports | awk '/Hardware Port: (Wi-Fi|Ethernet)/ {getline; print $2}')
        for IFACE in $INTERFACES; do
            sudo networksetup -setv6off "$IFACE" 2>/dev/null || echo -e "${RED}[- ERROR] Failed to disable IPv6 on $IFACE. It may already be disabled or require different permissions.${NC}"
            echo -e "${GREEN}[+ SUCCESS] Disabled IPv6 on macOS physical adapter: $IFACE${NC}"
            ((REMEDIATIONS_APPLIED++))
        done
    elif [ "$(uname)" == "Linux" ]; then
        # Linux
        if sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1 >/dev/null 2>&1 && sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1 >/dev/null 2>&1; then
            echo -e "${GREEN}[+ SUCCESS] Disabled IPv6 system-wide on Linux (sysctl)${NC}"
            ((REMEDIATIONS_APPLIED++))
            echo -e "${YELLOW}[i] Note: To make this persistent across reboots, add these to /etc/sysctl.conf${NC}"
        else
            echo -e "${RED}[- ERROR] Failed to disable IPv6 via sysctl. Are you running as root/sudo?${NC}"
        fi
    fi
fi

echo ""
echo -e "${CYAN}Remediation complete. Total actions taken: $REMEDIATIONS_APPLIED${NC}"
