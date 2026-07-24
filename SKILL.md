---
name: claude-shield
description: Audit and repair a local Windows, macOS, Linux, Clash Verge/Mihomo, Sing-Box, Google Chrome, and Microsoft Edge setup for service mode, routing, DNS, WebRTC, IPv6, IP reputation, timezone, language, Claude Code DISABLE_TELEMETRY, ~/.claude.json device fingerprints, 429 rate limit log risks, and minimal privacy-hardening recommendations without fingerprint spoofing or platform-evasion guidance.
---

# Claude Shield (克劳德安全盾)

Audit privacy leaks, contradictory network signals, and Claude Code telemetry/device ID risks without trying to defeat platform safeguards. Prefer stable, ordinary browser behavior and the smallest defensible configuration change.

## Safety Boundary

- Work read-only by default. Ask before changing proxy, DNS, browser, or operating-system settings.
- Never elevate silently. Before an administrator-required change, show the exact scope, obtain approval, and ask the user to relaunch the controlling app or terminal as Administrator.
- Do not help spoof identity or browser fingerprints, bypass bot or fraud controls, evade regional restrictions, or support multi-account abuse.
- Do not recommend anti-detect browsers for risk-control evasion.
- Do not collect or expose cookies, passwords, subscription URLs, proxy credentials, payment details, or fabricated identity and billing data.
- Redact usernames, node names, IP addresses, and other sensitive identifiers before publishing reports.

## Triage External Tools

Do not install, execute, or copy a third-party repository merely because it appears in an audit. Inspect its stated purpose first, then classify it:

- Exclude [Camoufox](https://github.com/daijro/camoufox), [CloakBrowser](https://github.com/CloakHQ/cloakbrowser), and [browser-profiles](https://github.com/aitofy-dev/browser-profiles) from the workflow. Their documented features include anti-detect behavior, automation concealment, or fingerprint spoofing. Never use them to evade bot, fraud, or platform controls.
- If one of those tools is already present, report it as a high-impact diagnostic confounder. Do not uninstall it without approval; establish a clean baseline in ordinary Chrome or Edge before drawing fingerprint conclusions.
- Use [BrowserLeaks.io](https://github.com/residentialproxies/browserleaks.io) only as an optional secondary IP, DNS, and WebRTC test. Inspect its network requests and data handling before self-hosting, and never treat its privacy score as proof.
- Use the [minimal WebRTC detection gist](https://gist.github.com/ricco020/9c8eaab4eb901dd254205bf59b49e104) only as a supplementary manual check. Its single-STUN, candidate-parsing result is heuristic; compare any exposed address with the intended exit and confirm in both Chrome and Edge.
- Treat [vargalott/mihomo](https://github.com/vargalott/mihomo) as configuration inspiration for TUN, `strict-route`, gvisor, and fake-IP concepts, not as a drop-in profile. It targets a specific dual-gateway censorship-circumvention setup; never copy its routes, ports, blanket blocks, placeholders, or credentials without mapping them to the local runtime.

Keep the bundled collector, `assets/browser-audit.html`, and live network checks as the primary workflow. Do not vendor these repositories or add them as dependencies.

## Host Compatibility

Use the directory containing this `SKILL.md` as `<skill-root>`. Resolve bundled files from that directory rather than from the current project or shell working directory.

- **Codex:** install the folder as `$CODEX_HOME/skills/claude-shield` or `~/.codex/skills/claude-shield`, then invoke `$claude-shield` or ask a matching audit question.
- **Claude Code:** install the folder as `~/.claude/skills/claude-shield` for personal use or `.claude/skills/claude-shield` for a project, then invoke `/claude-shield` or ask a matching question. Claude Code may resolve bundled files through `${CLAUDE_SKILL_DIR}`.
- **Other Agent Skills hosts:** preserve `SKILL.md`, `scripts/`, `assets/`, and their relative layout. Ignore `agents/openai.yaml` when the host does not use OpenAI interface metadata.
- **Other LLM agents:** load `SKILL.md` as instructions and run `<skill-root>/scripts/collect_windows_network.ps1` (or `<skill-root>/scripts/collect_posix_network.sh` on macOS/Linux). If the agent cannot execute local commands, ask the user to run the collector and provide its JSON output.

On Windows hosts, prefer `pwsh`; fall back to `powershell.exe` 5.1. On macOS or Linux hosts, run `scripts/collect_posix_network.sh`.
To apply approved remediations interactively, run `<skill-root>/scripts/remediate_windows_network.ps1` on Windows, or `<skill-root>/scripts/remediate_posix_network.sh` on macOS/Linux.

## Audit Workflow

1. Establish the intended exit country or region and whether it is temporary or long-term.
2. On Windows, resolve `<skill-root>/scripts/collect_windows_network.ps1` and run it to collect a local snapshot (or `scripts/collect_posix_network.sh` on macOS/Linux). Pass `-ConfigDir` for a non-default Clash Verge installation and `-PolicyGroupPattern` for locally named service groups. Do not dump complete Mihomo configuration or subscription files, and redact the snapshot before sharing it.
3. Review actual services, process and listener state, physical versus tunnel adapters, DNS configuration, proxy environment variables, Windows locale, browser profiles, extensions, policies, and Mihomo policy groups.
4. Open `<skill-root>/assets/browser-audit.html` in the Google Chrome and Microsoft Edge profiles the user normally uses. Use its English or Simplified Chinese interface, run it separately in each browser, review its heuristic score and findings, and optionally export a localized redacted PNG or copy the `CLAUDE_SHIELD_BROWSER_REPORT_V1` block into the current LLM. Then inspect public IP reputation, unique-hostname DNS results, IPv4/IPv6, cross-site exits, the observed Accept-Language header, and the detector's fingerprint report. The local page does not replace external IP, DNS, or header tests.
5. Label every result `verified`, `inferred`, or `manual check required`. Never turn missing data into a pass.
6. Compare every signal with the intended exit rather than treating a detector's score as proof.
7. Classify findings as `must fix`, `optional consistency`, or `leave alone`.
8. Recommend the minimum local change, obtain approval, apply it, and run one verification pass.

## Adapt to the Local Computer

- Discover paths, profiles, services, adapters, and supported settings before recommending a change. Do not assume the default profile, port, interface name, or installation directory.
- Use `LastUsedProfile` as a lead, then confirm which Chrome or Edge profile the user actually uses. Profile-specific extensions and languages do not apply to every profile.
- Treat `Physical`, `TunnelOrVpn`, and `VirtualOrOther` adapter classifications as evidence, not authority. Ask for confirmation when a vendor-specific adapter is unclear.
- Never disable IPv6 on an adapter classified as a tunnel or VPN. Only propose changing an active physical adapter after confirming it is the real uplink and obtaining approval.
- Let the collector query Mihomo's local HTTP controller or Windows named pipe with a read-only `GET /proxies` request. If neither transport is reachable, report `ManualCheckRequired` and verify the selected policy group in Clash Verge. Do not infer a fixed node from the static YAML list.
- If a browser field, extension state, managed policy, or runtime header cannot be read reliably, require a browser UI or live test instead of editing speculative files.

## Required Coverage

Use the snapshot and live browser tests together:

| Area | Local evidence | Completion rule |
| --- | --- | --- |
| Service mode | Matching Windows service state, Mihomo process, mixed-port listener | Service is running and the expected listener exists |
| Routing | Rule mode, system proxy, TUN, `strict-route`, stack, LAN access | Required values are verified in runtime-relevant configuration |
| IPv6 and Teredo | Teredo state plus classified active adapter bindings | No physical-uplink bypass; do not disable the Mihomo/tunnel adapter |
| DNS | `respect-rules`, fake-IP, `any:53`, DNS IPv6, local resolvers, encrypted upstream hosts | A unique-hostname browser test shows no physical-ISP resolver; static settings alone do not pass |
| Policy group | Rule reference, group type, HTTP or named-pipe controller selection chain | Intended service group is selected and the chain contains no URL-test, fallback, load-balance, smart, or other automatic selector; otherwise verify in the UI |
| Windows locale | Timezone, culture, UI culture, user language list, system locale, home location | Explain mismatches; only change values that reflect genuine long-term use |
| Chrome and Edge | Last-used profile, preferences, process `--lang`, managed WebRTC policy, extension state | Confirm the active profile and validate `navigator.languages`, Accept-Language, and WebRTC in each browser |
| Environment proxies | Presence of process, user, or machine `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, or `NO_PROXY` | Explain whether each is intentional; do not reveal its value |
| IP reputation | Country, ASN, provider type, proxy flags, abuse indicators, and blacklist claims from the supplied report | Separate confirmed routing facts from database opinions; corroborate severe claims when possible |
| Cross-site routing | Observed exit country, ASN, and IP grouping for each tested site | Protected sites follow the intended group; intentional direct routes are documented; physical-ISP exits are failures |
| Browser fingerprint | Detector values plus local OS, processor count, memory, GPU, and resolution context | Explain contradictions and confidence without prescribing spoofing or anti-detect tools |
| Claude Code telemetry | DisableTelemetry env var, ~/.claude.json userID field, ~/.claude/telemetry cache size, Bedrock/Vertex API configuration | Telemetry is disabled or managed; device fingerprint is clean; no multi-device sharing |

## Claude Code Telemetry & Account Suspension Risk Audit

Audit local Claude Code / CLI settings and explain account risk factors using findings from reverse-engineered client source code:

### 5 Primary Suspension Risk Factors (Ranked by Severity)

1. **Account Sharing (Very High Risk)**: Single account (`account_uuid`) accessed across multiple `Device ID`s, accompanied by conflicting IPs, operating systems, or timezones.
2. **Rate Limit Escalation (High Risk)**: Aggregated usage by `account_uuid` + `subscription_type` + `rate_limit_tier`. Repeatedly hitting limits triggers HTTP 429 errors which escalate to account bans.
3. **Content & Anti-Distillation (High Risk)**: Automated content fingerprinting and detection of fake tool injection patterns or model distillation attempts.
4. **Automation Abuse (Medium Risk)**: Combination of headless/CI execution environment, non-interactive shell execution, SDK entry point detection, and abnormal token consumption velocity.
5. **Client Tampering (Medium Risk)**: Mismatched client version fingerprints, modified binary headers, or malformed User-Agent strings.

### Telemetry & Device ID Audit Rules

Use the collector's `ClaudeCode` section to audit local status:

- **Telemetry Disablement (`DISABLE_TELEMETRY`)**: Verify whether `$env:DISABLE_TELEMETRY` is set to `1` across Process, User, or Machine environment variables. Recommend setting `$env:DISABLE_TELEMETRY=1` to disable local telemetry collection.
- **Device Fingerprint Reset (`~/.claude.json`)**: Check if `~/.claude.json` contains a `userID` or `deviceId` identifier. If account sharing or multi-device ambiguity occurred, recommend deleting the `userID` field to reset the local device fingerprint.
- **Telemetry Cache Cleanup (`~/.claude/telemetry/`)**: Inspect the local telemetry cache directory `$HOME\.claude\telemetry\`. Recommend clearing this directory if cached events have accumulated.
- **Managed Enterprise Gateways**: Note whether Bedrock or Vertex API overrides (`CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`) are active, as these official enterprise endpoints automatically disable client telemetry analysis.
- **Single Account Operational Baseline**: Advise strict adherence to 1 account = 1 user = 1 primary device/IP setup without sharing credentials across different locations.

## Interpret Results

Use these rules when reviewing ChaIP, BrowserLeaks, or similar reports:

| Signal | Pass | Investigate or fix |
| --- | --- | --- |
| WebRTC | No candidate is exposed, or all public candidates match the intended proxy exit | A local or public address reveals a different physical network |
| DNS | Resolvers are reputable and geographically consistent with the exit | A physical-ISP resolver or a contradictory country appears |
| IPv6 | No IPv6 is exposed, or the visible IPv6 belongs to the same proxy egress | A physical-ISP IPv6 bypasses the proxy |
| Timezone | Reasonably consistent with long-term use and the intended region | A persistent, unexplained mismatch; treat as consistency, not a leak |
| Language | A plausible primary locale with ordinary secondary preferences | A surprising primary locale; do not treat extra languages as proof of abuse |
| TCP/IP and RTT | Record as low-confidence context | Do not chase inferred OS or latency labels unless corroborated by a real leak |
| IP reputation | Region and ASN are plausible; no corroborated severe abuse or blacklist signal | Conflicting proxy flags or severe abuse claims across multiple current sources |
| Cross-site routing | Sites follow their declared rule groups without exposing the physical ISP | A protected site exits through the physical ISP or an unintended country |
| Browser fingerprint | Browser claims are plausible for the local OS and hardware; privacy-reduced values are explained | Impossible high-confidence combinations or unexplained headless, software-rendering, or automation signals |

Do not call a long list of Google or Cloudflare anycast DNS servers a leak merely because the list is long. Do not call a proxy-owned IPv6 a local IPv6 leak when its geography and ASN align with the intended exit. Treat installed fonts as weak historical residue; do not uninstall system fonts merely to improve a fingerprint score.

## Review IP Reputation

- Record geolocation, ASN, organization, residential/datacenter/mobile classification, proxy or VPN labels, abuse scores, and blacklist claims from the supplied report.
- Treat country and ASN as routing evidence. Treat residential, proxy, risk, and abuse labels as vendor opinions that may be stale or contradictory.
- Corroborate a severe reputation claim with another current source when practical. Do not require every database to agree or require a residential label for a healthy route.
- Recommend contacting the provider or choosing another legitimate endpoint only when reputation causes a real reliability or access problem. Do not use reputation work to misrepresent identity, residence, billing, or eligibility.

## Review Cross-Site Routing

- Group tested sites by observed exit country, ASN, and IP without publishing the raw addresses.
- Compare each result with the user's actual Mihomo rule and policy group. A different exit can be correct for an intentionally direct or separately routed category.
- Mark a protected site using the physical ISP, an unintended country, or an unexpected automatic selector as `must fix`.
- Treat a fetch failure, CDN variation, or blocked probe as `unknown`, not as a leak. Re-test a small representative set after a rule change instead of forcing every site through one route.

## Interpret Browser Fingerprints

Compare the detector report with `System.DeviceContext` and the active Chrome or Edge profile:

- Check UA and UA-CH platform claims against the local OS and browser version. Give TCP/IP OS inference lower confidence than browser-provided values.
- Compare WebGL vendor and renderer with the installed GPU context, while accounting for integrated/discrete GPU switching, remote desktop, virtualization, and software rendering.
- Treat canvas and audio hashes as stability indicators with no correct country-specific value. Do not try to make Chrome and Edge hashes identical.
- Treat `hardwareConcurrency` and `deviceMemory` as browser-reduced values; they need not equal the exact processor count or installed RAM.
- Explain screen-size differences using DPI scaling, window size, multiple displays, or remote sessions before calling them inconsistent.
- Treat fonts, language, timezone, touch points, and media capabilities as contextual signals. Extra fonts or secondary languages are not proof of abuse.
- Investigate unexpected values through ordinary browser extensions, enterprise policies, GPU acceleration, remote sessions, or profile state. Never recommend Canvas/WebGL/UA rewriting, anti-detect browsers, or automation-evasion patches.

## Cross-Check Chrome and Edge

Use the collector's `Browsers` result to check whether Chrome and Edge have local profiles and any extension whose manifest or localized description mentions WebRTC or RTC leaks. Treat this as a heuristic inventory, not proof that an extension is enabled or effective. Use `assets/browser-audit.html` to collect the same browser-provided fields and ICE candidates in both active profiles without spoofing them.

- Open `chrome://extensions` and `edge://extensions` to confirm whether each reported extension is enabled in the active profile.
- Treat `LikelyEnabled` as requiring UI confirmation. An absent stored `state` with no disable reason is not conclusive.
- Inspect Chrome's managed `WebRtcIPHandling` and `WebRtcIPHandlingUrl` values and Edge's `WebRtcIPHandlingUrl` or related WebRTC policy values when present. Do not create a managed policy unless a confirmed leak justifies it and the user approves.
- Run the bundled browser audit in both browsers. Keep raw ICE addresses local; use its redacted copy or download when sharing results. Record exposed candidates and whether they match the intended exit.
- If no WebRTC leak appears, leave extensions alone; do not install a WebRTC extension merely to improve a score.
- If only one browser leaks, compare that browser's extension state, permissions, profile, and policy before changing the system-wide proxy.
- If an extension is present but the test still leaks, report it as ineffective or misconfigured rather than assuming installation equals protection.

Redact browser profile names and extension IDs before sharing the report publicly. Prefer TUN and routing fixes for confirmed network bypasses; an extra extension creates another component to maintain and can change the browser's observable surface.

## Recommend a Coherent Region

When several long-term signals conflict, offer one of these two consistency targets. Present it as optional operational consistency, not a way to evade platform review. Only change values that match the user's genuine usage; never alter identity, billing, tax, or payment information.

| Target | Exit and DNS | Timezone | Primary browser language |
| --- | --- | --- | --- |
| United States | Stable US exit; DNS routed through the tunnel and aligned with that exit | Match the exit's actual US time zone; the US has multiple time zones | `en-US`, retaining legitimate secondary languages |
| Japan | Stable Japan exit; DNS routed through the tunnel and aligned with Japan | `Asia/Tokyo` | `ja-JP`, retaining legitimate secondary languages |

For either target, prevent physical-network WebRTC, DNS, or IPv6 bypasses. Do not spoof browser geolocation, remove system fonts, or rewrite unrelated OS settings. If the user frequently switches countries, recommend leaving timezone and language truthful rather than repeatedly changing them.

## Apply Approved Changes

Follow this sequence, incorporating lessons from prior Windows and Clash Verge remediation:

1. Capture the read-only snapshot and identify the single confirmed mismatch.
2. Prefer Clash Verge controls for mode, TUN, service mode, DNS, IPv6, and LAN access because the app can regenerate runtime YAML.
3. Show the proposed change, affected setting or file, expected effect, and rollback before editing.
4. Ask for explicit approval. If the change touches the service, TUN adapter, system DNS, IPv6 binding, Teredo, firewall, protected files, or system timezone, require the controlling app or terminal to be running as Administrator before continuing. Do not elevate for ordinary browser-language changes.
5. Back up only a file that must be edited directly. Never copy or display `profiles.yaml`, subscription URLs, or the full configuration.
6. Preserve rule mode and system proxy when they already work. For the established full-tunnel baseline, verify TUN, service mode, `strict-route`, gvisor, fake-IP, `any:53`, `respect-rules`, LAN disabled, and the intended IPv6 behavior instead of rewriting the whole configuration.
7. When a physical IPv6 bypass is confirmed, disable only the verified physical uplink and Teredo; leave Mihomo and other required tunnel adapters intact.
8. Fully exit the target browser before changing profile preferences. Reopen the same profile and verify preferences, process language, `navigator.languages`, Accept-Language, extension state, and WebRTC behavior.
9. Confirm the service-specific Mihomo group is referenced by rules and pinned to the intended manual selection. If runtime selection cannot be read, stop for a Clash Verge UI check.
10. Change one layer at a time, restart only the affected app or service, and verify runtime state rather than trusting a UI checkbox.
11. Re-run the local collector and one Chrome and Edge browser test pass. Roll back if a confirmed leak appears or routing breaks.

Remember that Clash Verge UI state and generated Mihomo runtime configuration may live in different files. A listener can be owned by `verge-mihomo`; process-name checks should include it. After changing Chrome or Edge language order, fully restart that browser and inspect `navigator.languages`. A matching proxy-provided IPv6 is not evidence that the local IPv6 binding was re-enabled.

## Mihomo Baseline for Full-Tunnel Leak Prevention

When the goal is a Windows full-tunnel setup, check this baseline without assuming every environment must be identical:

- Use rule mode with system proxy, service mode, and TUN enabled.
- Enable `strict-route`; use the stable TUN stack already proven on the machine, commonly `gvisor`.
- Enable Mihomo DNS with `fake-ip` and `any:53` hijacking.
- Keep local IPv6 and Teredo disabled when the selected route does not deliberately support them.
- Disable LAN access unless it is explicitly required.
- Pin sensitive service traffic to a deliberate, stable policy group instead of automatic node selection.

Distinguish local interface settings from public egress behavior. A local IPv6-disabled setting can coexist with a proxy-provided IPv6 at the remote endpoint.

## Generic Baseline for Non-Clash Proxies

If the user employs a proxy core other than Mihomo (e.g., Xray, Sing-Box native, Surge, Quantumult X):
- Do not attempt to read or write Clash-specific YAML configurations.
- Verify if the client supports a true TUN (virtual network interface) mode. If it only supports system proxy (HTTP/SOCKS), warn the user that DNS and WebRTC leaks are highly probable unless strict browser extensions are used.
- For DNS, recommend enabling the client's equivalent of `fake-ip` or overriding system DNS to the TUN interface.
- **Use OS-Level Probes to Verify Isolation (macOS Example)**: Since you cannot read their proprietary config files, verify the actual OS network state:
  - Run `ifconfig | grep -E "utun|tun"` to ensure a virtual network interface is active.
  - Run `scutil --dns` to verify if DNS resolution is hijacked (look for `nameserver[0] : 198.18.0.2` or similar fake-ip ranges, and ensure no domestic ISP resolvers leak in the primary resolver array).
  - Run `netstat -nr -f inet | grep -e "default" -e "0/1" -e "128.0/1"` to verify if the default route or a fake-ip route points to the `utun` interface.
- Rely on OS-level remediation (e.g., `remediate_windows_network.ps1` / `remediate_posix_network.sh`) to disable telemetry and physical IPv6, and instruct the user to manually configure their specific proxy client according to the physical isolation principles.

## Report Format

When the user supplies an `CLAUDE_SHIELD_BROWSER_REPORT_V1` block, parse its redacted evidence and display the page's overall and category scores before the evidence table. Treat the scores as transparent local heuristics, not independent proof. Explain each flagged item in the context of the collector and live tests; never convert an unknown public WebRTC candidate into a confirmed leak without comparing it with the intended exit.

Return a compact evidence table with these columns: `signal`, `status`, `confidence`, `evidence`, and `action`. Follow it with exactly three short sections:

1. `Must fix` for confirmed leaks or route failures.
2. `Optional consistency` for timezone, primary language, or other non-leak mismatches.
3. `Leave alone` for noisy detector claims and signals already aligned.

State uncertainty explicitly. Reputation scores, fingerprint hashes, TCP/IP inference, and RTT are not standalone proof of proxy use or abuse. Never promise that a configuration will prevent account review, suspension, or platform detection.

## Verification

Re-run public tests after a node, network, browser, or configuration change. Use a fresh unique hostname for DNS so cached answers do not hide the active resolver path. A healthy result is internally consistent and free of confirmed bypasses; it does not need every heuristic detector to show green. Do not mark the audit complete while any required item is `ManualCheckRequired`.
