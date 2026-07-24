<div align="center">

# 🛡️ Claude Shield

### Source-Leak Hardening & Environment Audit Skill for Claude Workflows

[![License](https://img.shields.io/badge/license-MIT-2ea44f)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-0078D6)](README.md)
[![Schema](https://img.shields.io/badge/schema-v6.0-5391FE)](scripts/collect_windows_network.ps1)
[![Codex](https://img.shields.io/badge/Codex-skill-111111)](SKILL.md)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-D97757)](SKILL.md)

[简体中文](README.zh-CN.md) · [Skill instructions](SKILL.md) · [Quick Install](#30-second-install) · [MIT License](LICENSE)

**Don't let `userID` device fingerprints, missing `DISABLE_TELEMETRY`, IPv6 leaks, or HTTP 429 rate limit spikes get your Claude account suspended.**
*No fingerprint spoofing or anti-detect tricks. Secure your environment with clean TUN, DNS, and telemetry isolation.*

</div>

> [!IMPORTANT]
> 💡 **Why accounts get suspended**: Analysis of the 510k-line leaked Claude Code source code reveals multi-dimensional risk evaluation: Multi-device sharing (Very High) > 429 Rate Limit spikes (High) > Anti-distillation fake tool injection (High) > CI Automation abuse (Medium) > Client tampering (Medium). This project provides read-only audit & minimal defensible hardening without bypassing platform terms or bot controls.

> [!CAUTION]
> 💔 **Top 3 painful experiences for Claude users**:
> 1. 💸 **Suspended right after paying**: Getting "Your account has been suspended" within days of paying for Pro/Team subscriptions, with zero support response.
> 2. 🌐 **Hidden network leaks**: Believing a green proxy node status means safety, while physical ISP DNS, WebRTC candidates, or unhandled IPv6 silently expose real location metadata.
> 3. ⚡ **429 Rate limit cascade**: Hitting repeated 429 quota limits during intense coding sessions, followed by device ID fingerprinting via `~/.claude.json` and telemetry log bans.

## Why this exists

Proxy health is more than an IP address. A setup can show the expected exit while DNS, WebRTC, IPv6, an automatic policy group, or a second browser still exposes a different path. Detector scores can also mistake harmless signals—fonts, RTT, TCP/IP inference, or proxy-owned IPv6—for leaks.

`claude-shield` combines local evidence, Mihomo/Sing-Box runtime state, browser checks, and Claude Code telemetry metrics to separate confirmed leaks from detector noise, then recommends the smallest defensible fix.

## What it checks

| Layer | Coverage |
| --- | --- |
| Clash Verge / Mihomo / Sing-Box | Service mode, system proxy, TUN, `strict-route`, stack, LAN access, runtime policy selection |
| DNS and routing | Mihomo DNS, fake-IP, `any:53`, `respect-rules`, physical-interface bypass, cross-site exits |
| IPv6 and WebRTC | Physical IPv6, Teredo, tunnel IPv6, ICE candidates, Chrome/Edge policy and extension state |
| Browser consistency | Bundled local probe for active-profile languages, timezone, WebGL/GPU (SwiftShader CPU rendering fallback detection), automation state, reduced hardware values |
| Claude Code source-leak audit | `DISABLE_TELEMETRY` env var, `~/.claude.json` device fingerprint `userID` reset, `telemetry` cache folder monitoring, 429 log spike analysis |
| Multi-client & Cross-platform | Windows (`pwsh`) / macOS & Linux (`collect_posix_network.sh`), detects Sing-Box, V2RayN, Xray |

## 🚀 30-Second Quick Start

### 1. Terminal Standalone Mode (Recommended: Zero dependencies)

Run directly in your system terminal for read-only audit & 1-click hardening without needing active AI accounts:

```powershell
# 1. Clone repository
git clone https://github.com/AschoofAlpha/anti-claude-check.git

# 2. Run read-only audit (Windows)
pwsh -NoProfile -File .\anti-claude-check\scripts\collect_windows_network.ps1

# 2. Run read-only audit (macOS / Linux)
bash ./anti-claude-check/scripts/collect_posix_network.sh

# 3. Run 1-click security hardening & fix (Windows)
pwsh -NoProfile -File .\anti-claude-check\scripts\remediate_windows_network.ps1
```

### 2. AI Agent Integration (Codex / Cursor / Windsurf / VS Code / Claude Code)

If you want an AI Coding Agent to parse your local diagnostic output and provide tailored recommendations:

- **Codex**:
  ```powershell
  New-Item -ItemType Directory -Force "$HOME/.codex/skills" | Out-Null
  git clone https://github.com/AschoofAlpha/anti-claude-check.git "$HOME/.codex/skills/claude-shield"
  ```
  Invoke with `$claude-shield` in conversation.

- **Cursor / Windsurf / VS Code (Agent Skills Hosts)**:
  Clone or add repository as Git Submodule into `.agent/skills/claude-shield` preserving `SKILL.md`.

- **Other LLM Hosts**:
  Load `SKILL.md` as system instructions and paste collector JSON to the model.

## Run the read-only collector

From the skill directory:

```powershell
pwsh -NoProfile -File .\scripts\collect_windows_network.ps1
```

Windows PowerShell 5.1 is also supported:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\collect_windows_network.ps1
```

The collector uses local Windows and browser state, reads Mihomo runtime selection through its HTTP controller or named pipe when available, and emits JSON. Redact usernames, node names, addresses, and other identifiers before posting output publicly.

## Run the local browser probe

Open [`assets/browser-audit.html`](assets/browser-audit.html) in the Chrome profile you normally use, choose English or Simplified Chinese, click **Run audit**, then repeat in Edge. The page has no external dependencies and changes no browser values. It displays a heuristic score, category bars, prioritized findings, and local recommendations. The selected language also applies to the LLM summary and PNG report. When WebRTC testing is enabled, it sends one discovery request to Google's public STUN server; all results remain in the page.

The screen shows raw ICE addresses for local comparison. **Copy report for LLM**, **Download redacted JSON**, and **Download PNG report** replace each address with a classification before sharing. Paste the copied block into Codex, Claude Code, or another LLM using this skill to receive the evidence table and recommendations. The score does not predict Claude approval, and the probe does not determine public IP, DNS resolver ownership, or the real Accept-Language request header, so keep the live network tests in the workflow.

## How it works

1. Capture a read-only local snapshot.
2. Run the bundled browser probe separately in the normal Chrome and Edge profiles.
3. Verify both browsers with live DNS, public IP, IPv4/IPv6, Accept-Language, and detector checks.
4. Label evidence as `verified`, `inferred`, or `manual check required`.
5. Separate `must fix`, `optional consistency`, and `leave alone` findings.
6. Apply one approved change at a time and re-test.

## What it deliberately does not do

- No Canvas, WebGL, UA, locale, timezone, or WebRTC fingerprint spoofing.
- No automation concealment, anti-bot bypass, CAPTCHA avoidance, or multi-account tooling.
- No fabricated identity, residence, billing, tax, or payment information.
- No blind copying of third-party Mihomo configurations or anti-detect browser code.
- No promise that any configuration prevents account review or suspension.

## Compatibility

| Host | Invocation | Status |
| --- | --- | --- |
| Codex | `$anti-claude-check` | Supported |
| Claude Code | `/anti-claude-check` | Supported and discovery-tested |
| Agent Skills-compatible hosts | Host-specific | Supported layout |
| Other local LLM agents | Load `SKILL.md` and collector JSON | Manual fallback |
| PowerShell | 7.x / Windows PowerShell 5.1 | Self-tested |

## Contributing

Found a false positive or an unsupported Clash Verge layout? Open an issue with a redacted collector result and the exact browser/profile tested. Never post subscription URLs, credentials, complete IP addresses, or account data.

If this project helped you find a real leak—or avoid a destructive “fingerprint fix”—consider giving it a ⭐.

## License

[MIT](LICENSE) © 2026 AschoofAlpha
