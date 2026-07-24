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

> *"The safest way to stay connected is to be honest about your own network."*

**Don't let hidden device trackers, accidental IP leaks, or rapid-fire request errors get your Claude account suspended out of nowhere.**
*Say no to risky "anti-detect" browser spoofing—secure your workspace with pure, clean network isolation.*

</div>

> [!IMPORTANT]
> 💡 **Why do Claude accounts get suspended? —— Uncovering the 5 Risk Truths from 510k Lines of Leaked Code**
> 
> Account suspensions aren't random; they are based on a multi-dimensional scoring system. Here are the core triggers (ranked by severity):
> 1. 🚨 **Account Sharing & Multi-Device Hopping (Critical Risk)**: Claude secretly generates a persistent "Device ID" on your local machine. If your account bounces across multiple IDs, countries, or operating systems in a short period, the system flags it as "account sharing/selling" and bans it instantly.
> 2. ⚡ **Abusing Rate Limits (High Risk)**: Official servers strictly monitor request frequencies. Firing off massive prompts too fast and repeatedly hitting HTTP 429 "Too Many Requests" errors will flag your account for resource abuse and eventual suspension.
> 3. 🕵️ **"Model Distillation" & Fake Tool Traps (High Risk)**: The source code contains hidden "anti-distillation" traps. If the server suspects your traffic is being intercepted or used to train competitor AI models, it silently injects fake tools into the prompt. If your automation script takes the bait, you're flagged.
> 4. 🤖 **Careless Automation (Medium Risk)**: The system checks if a real human is behind the screen. Running in headless cloud servers, non-interactive shells, or consuming tokens at superhuman speeds will trigger alarms.
> 5. 🛠️ **Clumsy Fingerprint Spoofing (Medium Risk)**: Many users try to outsmart the system using "anti-detect browsers" to fake their User-Agent or hardware. When Claude's validation checks see through these sloppy disguises, it serves as direct proof of suspicious behavior.
> 
> *This project provides read-only diagnostics & minimal defensible hardening to eliminate real physical network leaks without violating platform Terms of Service.*

> [!CAUTION]
> 💔 **The Top 3 Painful Experiences for Claude Users**:
> 1. 💸 **Suspended Right After Paying**: You just paid for a Pro/Team subscription, only to wake up three days later to a "Your account has been suspended" screen. Appeals are met with automated bot replies, and both your money and chat history are gone forever.
> 2. 🌐 **The Illusion of a "Green" Proxy**: You think you're safe because your proxy app shows a stable connection. Little do you know, your physical network adapter's DNS, unhandled IPv6 traffic, or WebRTC loopholes are silently leaking your real domestic ISP identity in the background.
> 3. ⚡ **Banned in the Middle of Coding**: While deeply immersed in coding with Claude Code, missing background blockers allow your local tracking traces and persistent Device ID to be continuously uploaded. Hit the rate limit just a few times, and your entire account gets dragged into the ban-zone.

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
