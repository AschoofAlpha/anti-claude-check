#!/usr/bin/env bash
set -euo pipefail

# claude-shield POSIX Collector Script
# Read-only network and Claude Code environment collection for macOS and Linux

OS_NAME="$(uname -s)"
COLLECTED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# Check Claude Code Environment
CLAUDE_HOME="${HOME}/.claude"
CLAUDE_JSON="${HOME}/.claude.json"

HAS_DISABLE_TELEMETRY=false
if [ -n "${DISABLE_TELEMETRY:-}" ]; then
  HAS_DISABLE_TELEMETRY=true
fi

HAS_USER_ID=false
HAS_DEVICE_ID=false
CONFIG_PRESENT=false
if [ -f "${CLAUDE_JSON}" ]; then
  CONFIG_PRESENT=true
  if grep -q '"userID"' "${CLAUDE_JSON}" 2>/dev/null; then
    HAS_USER_ID=true
  fi
  if grep -q '"deviceId"' "${CLAUDE_JSON}" 2>/dev/null; then
    HAS_DEVICE_ID=true
  fi
fi

TELEMETRY_PRESENT=false
TELEMETRY_COUNT=0
TELEMETRY_SIZE=0
if [ -d "${CLAUDE_HOME}/telemetry" ]; then
  TELEMETRY_PRESENT=true
  TELEMETRY_COUNT=$(find "${CLAUDE_HOME}/telemetry" -type f 2>/dev/null | wc -l | tr -d ' ')
  if [ "${OS_NAME}" = "Darwin" ]; then
    TELEMETRY_SIZE=$(du -sk "${CLAUDE_HOME}/telemetry" 2>/dev/null | awk '{print $1 * 1024}' || echo "0")
  else
    TELEMETRY_SIZE=$(du -sb "${CLAUDE_HOME}/telemetry" 2>/dev/null | awk '{print $1}' || echo "0")
  fi
fi

# Construct JSON
cat <<EOF
{
  "SchemaVersion": 6,
  "CollectedAt": "${COLLECTED_AT}",
  "System": {
    "OperatingSystem": "${OS_NAME}",
    "Kernel": "$(uname -r)",
    "HostName": "$(hostname)",
    "ProxyEnvironmentVariables": [
      { "Name": "HTTP_PROXY", "Present": $([ -n "${HTTP_PROXY:-}" ] && echo "true" || echo "false") },
      { "Name": "HTTPS_PROXY", "Present": $([ -n "${HTTPS_PROXY:-}" ] && echo "true" || echo "false") },
      { "Name": "ALL_PROXY", "Present": $([ -n "${ALL_PROXY:-}" ] && echo "true" || echo "false") },
      { "Name": "NO_PROXY", "Present": $([ -n "${NO_PROXY:-}" ] && echo "true" || echo "false") }
    ]
  },
  "ClaudeCode": {
    "DisableTelemetryActive": ${HAS_DISABLE_TELEMETRY},
    "ConfigFilePresent": ${CONFIG_PRESENT},
    "HasUserIdFingerprint": ${HAS_USER_ID},
    "HasDeviceIdFingerprint": ${HAS_DEVICE_ID},
    "TelemetryDirPresent": ${TELEMETRY_PRESENT},
    "TelemetryFileCount": ${TELEMETRY_COUNT},
    "TelemetrySizeBytes": ${TELEMETRY_SIZE},
    "CloudProviders": {
      "UseBedrock": $([ -n "${CLAUDE_CODE_USE_BEDROCK:-}" ] && echo "true" || echo "false"),
      "UseVertex": $([ -n "${CLAUDE_CODE_USE_VERTEX:-}" ] && echo "true" || echo "false"),
      "HasAnthropicApiKey": $([ -n "${ANTHROPIC_API_KEY:-}" ] && echo "true" || echo "false")
    }
  }
}
EOF
