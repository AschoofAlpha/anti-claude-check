<div align="center">

# 反 Claude 检查

### Privacy and environment-consistency audit for legitimate Claude workflows

![License](https://img.shields.io/badge/license-MIT-2ea44f)
![Platform](https://img.shields.io/badge/platform-Windows-0078D6)
![PowerShell](https://img.shields.io/badge/PowerShell-5.1%20%7C%207-5391FE)
![Codex](https://img.shields.io/badge/Codex-skill-111111)
![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-D97757)

[简体中文](README.zh-CN.md) · [Skill instructions](SKILL.md) · [MIT License](LICENSE)

**One skill to audit Windows, Clash Verge/Mihomo, Chrome, and Edge—without fingerprint spoofing or anti-detect tricks.**

</div>

> [!IMPORTANT]
> This project finds real privacy leaks and contradictory environment signals. It does not bypass Claude reviews, bot controls, CAPTCHAs, regional restrictions, or platform safeguards.

## Why this exists

Proxy health is more than an IP address. A setup can show the expected exit while DNS, WebRTC, IPv6, an automatic policy group, or a second browser still exposes a different path. Detector scores can also mistake harmless signals—fonts, RTT, TCP/IP inference, or proxy-owned IPv6—for leaks.

`anti-claude-check` combines the local evidence and browser checks needed to separate confirmed leaks from detector noise, then recommends the smallest defensible fix.

## What it checks

| Layer | Coverage |
| --- | --- |
| Clash Verge/Mihomo | Service mode, system proxy, TUN, `strict-route`, stack, LAN access, runtime policy selection |
| DNS and routing | Mihomo DNS, fake-IP, `any:53`, `respect-rules`, physical-interface bypass, cross-site exits |
| IPv6 and WebRTC | Physical IPv6, Teredo, tunnel IPv6, ICE candidates, Chrome/Edge policy and extension state |
| Browser consistency | Bundled local probe for active-profile languages, timezone, WebGL/GPU, automation state, reduced hardware values, and ICE candidates |
| Claude Code source-leak audit | `DISABLE_TELEMETRY` env var, `~/.claude.json` device fingerprint `userID` reset, `telemetry` cache folder monitoring, cloud provider gateways, and 5 primary suspension risk triggers |
| Detector reports | ChaIP/BrowserLeaks-style IP reputation, ASN, RTT, TCP/IP inference, fingerprint contradictions |
| Local adaptation | Non-default paths, profiles, adapters, policy-group names, and genuine long-term US/Japan usage |

## 30-second install

### Codex

```powershell
New-Item -ItemType Directory -Force "$HOME/.codex/skills" | Out-Null
git clone https://github.com/AschoofAlpha/anti-claude-check.git "$HOME/.codex/skills/anti-claude-check"
```

Invoke with `$anti-claude-check` or ask a matching privacy-audit question.

### Claude Code

```powershell
New-Item -ItemType Directory -Force "$HOME/.claude/skills" | Out-Null
git clone https://github.com/AschoofAlpha/anti-claude-check.git "$HOME/.claude/skills/anti-claude-check"
```

Invoke with `/anti-claude-check`.

Other Agent Skills hosts can preserve the repository layout and load `SKILL.md`. Other local LLM agents can load `SKILL.md` as instructions and analyze the collector's JSON output.

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
