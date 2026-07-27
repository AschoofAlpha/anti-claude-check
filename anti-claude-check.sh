#!/usr/bin/env bash
set -euo pipefail

if command -v python3 >/dev/null 2>&1; then
  exec python3 -m claude_shield "$@"
fi

if [ "${1:-audit}" != "audit" ]; then
  printf '%s\n' "Command '${1:-}' requires Python 3.8 or newer." >&2
  exit 1
fi

exec bash "$(dirname "$0")/scripts/collect_posix_network.sh"
