<div align="center">

# 🛡️ Claude Shield

### Source-Leak Hardening & Environment Audit Skill for Claude Workflows

[![License](https://img.shields.io/badge/license-MIT-2ea44f)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-0078D6)](README.md)
[![Schema](https://img.shields.io/badge/schema-v6.0-5391FE)](scripts/collect_windows_network.ps1)
[![Codex](https://img.shields.io/badge/Codex-skill-111111)](SKILL.md)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-D97757)](SKILL.md)

[简体中文](README.zh-CN.md) · [Skill instructions](SKILL.md) · [Quick Install](#-30-second-quick-start) · [MIT License](LICENSE)

> *"The safest disguise is no disguise. Defeat the strictest AI risk controls using pure network isolation."*

**Don't let `userID` device fingerprints, missing `DISABLE_TELEMETRY`, IPv6 leaks, or HTTP 429 rate limit spikes get your Claude account suspended.**
*No fingerprint spoofing or anti-detect tricks. Secure your environment with clean TUN, DNS, and telemetry isolation.*

</div>

> [!IMPORTANT]
> 💡 **Why is your Claude account repeatedly suspended? — 5 Risk Evaluation Dimensions from 510k-Line Leaked Source Code**
> 
> Account suspension is a **multi-dimensional risk evaluation**. The 5 primary causes ranked by severity:
> 1. 🚨 **Multi-Device Account Sharing (Risk: Critical)**: Source code reveals clients generate a unique device ID (`userID` / `deviceId`) in `~/.claude.json`. When one account appears on multiple Device IDs accompanied by sudden exit IP shifts, OS switching (Windows vs macOS), or timezone mismatches, automatic bans are triggered for credential sharing.
> 2. ⚡ **429 Rate Limit Spikes (Risk: High)**: Monitored by `account_uuid` + `subscription_type` (Pro/Team) + `rate_limit_tier`. Repeated long-context prompt spikes trigger HTTP 429 quota limits, escalating rate limit tiers to full account bans.
> 3. 🕵️ **Fake Tool Injection & Anti-Distillation (Risk: High)**: Source code incorporates `tengu_anti_distill_fake_tool_injection`. When distillation or MITM proxying is suspected, false tool definitions are injected into System Prompts; executing these fake tools flags the session for data harvesting.
> 4. 🤖 **CI Automation Abuse (Risk: Medium)**: Monitored via headless environment flags, non-interactive shells, CI/CD env vars, and token consumption velocity.
> 5. 🛠️ **Client Tampering & Mismatch (Risk: Medium)**: Triggered by client version checksum failures, malformed User-Agents, or anti-detect browser rewrites.
> 
> *This project provides read-only diagnostics & minimal defensible hardening to eliminate real physical network leaks without violating platform Terms of Service.*

> [!CAUTION]
> 💔 **Top 3 Painful Experiences for Claude Users**:
> 1. 💸 **Suspended Right After Paying**: Getting "Your account has been suspended" within days of paying for Pro/Team subscriptions, receiving automated email rejections with lost funds and chat history.
> 2. 🌐 **Hidden Physical Network Leaks**: Believing a green proxy status guarantees safety, while physical ISP DNS queries, WebRTC candidate addresses, or unhandled IPv6 silently reveal domestic broadband identity.
> 3. ⚡ **429 Rate Limit Cascade**: Hitting repeated 429 quota limits during intense coding sessions, where missing `DISABLE_TELEMETRY=1` and fixed `~/.claude.json` Device IDs continuously report local tracking traces until banned.

### 🛡️ Why you need Claude Shield

| Traditional "Naked" or "Spoofed" Setup ❌ | Claude Shield Clean Isolation ✅ |
| :--- | :--- |
| **Device Fingerprint**: `~/.claude.json` persistently exposes a real unique ID | **Device Fingerprint**: 1-click wipe & reset, with easy backup/isolation |
| **Telemetry**: Silent background uploads of all actions & 429 quota errors | **Telemetry**: Injects `DISABLE_TELEMETRY=1` to completely sever reporting |
| **DNS/IPv6**: Proxy looks green, but physical adapter silently leaks location | **DNS/IPv6**: 1-click physical IPv6 disable, full WebRTC leak block |
| **Anti-Detection Strategy**: Spoofing UA/Hardware makes you look like a bot | **Anti-Detection Strategy**: Honest real system, relying purely on strict network isolation |

## ⚡ Core Capabilities Matrix

- 🔍 **Full-Stack Anti-Ban Audit**
  Goes beyond proxy rules (Clash/Mihomo/Sing-Box) to inspect physical adapters, exposing hidden IPv6 bypasses, DNS leaks, and WebRTC real IP exposure.
- 🛡️ **Claude-Specific Environment Hardening**
  Targeted fixes based on the leaked source code. Silently injects `DISABLE_TELEMETRY=1` to sever tracking, securely resets the high-risk `~/.claude.json` device fingerprint, and circumvents 429 rate limit cascades from the ground up.
- 🤖 **AI-Native Integration**
  A cross-platform diagnostic architecture purpose-built for Codex, Cursor, Windsurf, and VS Code. Empower your LLM to read your local network reports and become your personal advanced security expert.
## 🚀 30-Second Quick Start

### 1. Terminal Standalone Mode (Recommended: Zero dependencies)

Run directly in your system terminal for read-only audit & 1-click hardening without needing active AI accounts:

```powershell
# 1. Clone repository
git clone https://github.com/AschoofAlpha/claude-shield.git

# 2. Run read-only audit (Windows)
pwsh -NoProfile -File .\claude-shield\scripts\collect_windows_network.ps1

# 2. Run read-only audit (macOS / Linux)
bash ./claude-shield/scripts/collect_posix_network.sh

# 3. Run 1-click security hardening & fix (Windows)
pwsh -NoProfile -File .\claude-shield\scripts\remediate_windows_network.ps1
```

### 2. AI Agent Integration (Codex / Cursor / Windsurf / VS Code)

If you want an AI Coding Agent to parse your local diagnostic output and provide tailored recommendations:

- **Codex**:
  ```powershell
  New-Item -ItemType Directory -Force "$HOME/.codex/skills" | Out-Null
  git clone https://github.com/AschoofAlpha/claude-shield.git "$HOME/.codex/skills/claude-shield"
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
| Codex | `$claude-shield` | Supported |
| Agent Skills-compatible hosts | Host-specific | Supported layout |
| Other local LLM agents | Load `SKILL.md` and collector JSON | Manual fallback |
| PowerShell | 7.x / Windows PowerShell 5.1 | Self-tested |

## Contributing

Found a false positive or an unsupported Clash Verge layout? Open an issue with a redacted collector result and the exact browser/profile tested. Never post subscription URLs, credentials, complete IP addresses, or account data.

If this project helped you find a real leak—or avoid a destructive “fingerprint fix”—consider giving it a ⭐.

## License

[MIT](LICENSE) © 2026 AschoofAlpha
