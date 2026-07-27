#!/usr/bin/env bash
set -euo pipefail

# Anti Claude Check POSIX Collector Script
# Limited read-only OS, proxy-environment, and Claude Code privacy-control summary

OS_NAME="$(uname -s)"
COLLECTED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

HAS_DISABLE_TELEMETRY=false
if [ "${DISABLE_TELEMETRY:-}" = "1" ]; then
  HAS_DISABLE_TELEMETRY=true
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
    "DisableErrorReportingActive": $([ "${DISABLE_ERROR_REPORTING:-}" = "1" ] && echo "true" || echo "false"),
    "DisableNonessentialTrafficActive": $([ "${CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC:-}" = "1" ] && echo "true" || echo "false"),
    "CloudProviders": {
      "UseBedrock": $([ -n "${CLAUDE_CODE_USE_BEDROCK:-}" ] && echo "true" || echo "false"),
      "UseVertex": $([ -n "${CLAUDE_CODE_USE_VERTEX:-}" ] && echo "true" || echo "false"),
      "HasAnthropicApiKey": $([ -n "${ANTHROPIC_API_KEY:-}" ] && echo "true" || echo "false")
    }
  }
}
EOF
