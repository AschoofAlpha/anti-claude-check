#!/usr/bin/env bash

set -e

if command -v python3 &>/dev/null; then
    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
    if [ $? -eq 0 ]; then
        python3 -m claude_shield "$@"
        exit $?
    fi
fi

# Fallback when Python is not available
echo -e "\033[0;33m[- WARNING] Python 3 not detected or version too low. Limited local audit mode active.\033[0m"
echo -e "\033[0;90m[i] The following features will be skipped: Advanced redaction, Dry Run, Transaction/Rollback manifests, Credential scanning.\033[0m"

COMMAND="${1:-audit}"

if [ "$COMMAND" = "audit" ]; then
    bash "$(dirname "$0")/scripts/collect_posix_network.sh"
elif [ "$COMMAND" = "remediate" ]; then
    echo -e "\033[0;31m[- ERROR] Remediation without Python is unsupported because of lack of rollback and dry-run safety mechanisms. Please install Python 3.\033[0m"
    exit 1
else
    echo -e "\033[0;31m[- ERROR] Command '$COMMAND' is unsupported in fallback mode.\033[0m"
    exit 1
fi
