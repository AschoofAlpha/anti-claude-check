"""Collector analysis for Claude Shield (AI-facing library).

Runs the read-only collector and turns the snapshot into structured audit
checks. Intended to be imported by an agent skill (Codex / Claude Code),
not invoked as a CLI. No output rendering lives here; agents format the
checks themselves per SKILL.md's Report Format.
"""

import json
import os
import shutil
import subprocess

from .models import AuditCheck
from .resources import resource_path


class CollectorError(RuntimeError):
    """Raised when the platform collector fails."""


def run_legacy_collector(timeout=30):
    """Run the platform collector and return its parsed JSON snapshot.

    Raises CollectorError on missing runtime, non-zero exit, timeout, or
    unparseable output. Never prints or exits the process.
    """
    try:
        if os.name == "nt":
            script_path = resource_path("scripts", "collect_windows_network.ps1")
            executable = shutil.which("pwsh") or shutil.which("powershell.exe")
            if not executable:
                raise CollectorError("PowerShell is not available.")
            command = [executable, "-NoProfile", "-File", str(script_path)]
        else:
            script_path = resource_path("scripts", "collect_posix_network.sh")
            executable = shutil.which("bash")
            if not executable:
                raise CollectorError("bash is not available.")
            command = [executable, str(script_path)]

        result = subprocess.run(command, capture_output=True, timeout=timeout)
        if result.returncode != 0:
            error = result.stderr.decode("utf-8", errors="replace").strip()
            raise CollectorError(f"collector exited with code {result.returncode}: {error}")
        stdout = result.stdout.decode("utf-8-sig", errors="replace")
        start = stdout.find("{")
        if start < 0:
            raise CollectorError("collector returned no JSON object")
        return json.loads(stdout[start:])
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        raise CollectorError(str(exc)) from exc


def analyze_snapshot(data, include_recommendations=False):
    """Turn a collector snapshot into a list of AuditCheck objects.

    System-level checks run even when no Mihomo config is present. Returns
    a plain list; agents decide how to present it.
    """
    checks = []

    def add(check_id, title, category, status, severity, explanation, recommendation=""):
        checks.append(AuditCheck(
            id=check_id,
            title=title,
            category=category,
            status=status,
            severity=severity,
            confidence="confirmed" if status in ("pass", "fail", "warning") else "unknown",
            explanation=explanation,
            recommendation=recommendation if include_recommendations else "",
        ))

    claude = data.get("ClaudeCode", {})
    privacy_controls = (
        ("privacy.telemetry", "Claude Code metrics telemetry", "DisableTelemetryVars", "DisableTelemetryActive", "DISABLE_TELEMETRY"),
        ("privacy.errors", "Claude Code error reporting", "DisableErrorReportingVars", "DisableErrorReportingActive", "DISABLE_ERROR_REPORTING"),
        ("privacy.nonessential", "Claude Code non-essential traffic", "DisableNonessentialTrafficVars", "DisableNonessentialTrafficActive", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"),
    )
    broad_values = claude.get("DisableNonessentialTrafficVars", [])
    broad_active = any(
        str(item.get("Value", "")).strip() == "1"
        for item in broad_values
        if isinstance(item, dict)
    ) if broad_values else claude.get("DisableNonessentialTrafficActive") is True
    for check_id, title, values_key, active_key, variable in privacy_controls:
        values = claude.get(values_key, [])
        direct_active = any(
            str(item.get("Value", "")).strip() == "1"
            for item in values
            if isinstance(item, dict)
        ) if values else claude.get(active_key) is True
        active = direct_active or broad_active and variable != "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"
        explanation = (
            f"{variable}=1 is active."
            if direct_active else
            "Covered by CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1."
            if active else
            f"{variable}=1 was not verified."
        )
        add(
            check_id,
            title,
            "privacy",
            "pass" if active else "unknown",
            "info",
            explanation,
            f"Set {variable}=1 only if that documented opt-out matches the user's privacy preference.",
        )

    # System-level network and locale checks (run even when no Mihomo config is present)
    system = data.get("System")
    if isinstance(system, dict):
        # Service mode: process, service, and mixed-port listener
        proc_running = system.get("MihomoProcessRunning")
        service_active = system.get("ServiceModeActive")
        mixed_listening = system.get("MixedPortListening")
        if proc_running is not None:
            parts = []
            if proc_running:
                parts.append("process running")
            if service_active:
                parts.append("service mode active")
            if mixed_listening:
                parts.append("mixed-port listener present")
            if proc_running and service_active and mixed_listening:
                status, sev, expl = "pass", "info", "Observed " + ", ".join(parts) + "."
            elif not parts:
                status, sev, expl = "unknown", "info", "No Mihomo process, service, or mixed-port listener observed; confirm whether a proxy client is expected."
            else:
                status, sev, expl = "warning", "low", "Partial service state: " + ", ".join(parts) + "."
            add("network.service", "Mihomo service mode", "network", status, sev, expl,
                "Confirm the intended service mode and mixed-port listener in the active proxy client.")

        # Teredo state
        teredo = system.get("Teredo")
        if isinstance(teredo, dict):
            teredo_disabled = not teredo.get("Available") or bool(teredo.get("Disabled"))
            add("network.teredo", "Teredo state", "network",
                "pass" if teredo_disabled else "warning",
                "info" if teredo_disabled else "low",
                "Teredo is disabled." if teredo_disabled
                else f"Teredo is available ({teredo.get('Type', 'unknown')}) and not disabled; confirm it cannot expose a physical-uplink route.",
                "Do not disable the Mihomo/tunnel adapter; address Teredo only if it demonstrably bypasses the proxy.")

        # Physical adapter IPv6 bindings
        bindings = system.get("ActiveAdapterIPv6Bindings")
        if isinstance(bindings, list):
            physical_enabled = [b for b in bindings
                                if isinstance(b, dict) and b.get("Classification") == "Physical" and b.get("Enabled")]
            add("network.ipv6_binding", "Physical adapter IPv6 binding", "network",
                "pass" if not physical_enabled else "warning",
                "info" if not physical_enabled else "low",
                "No physical adapter exposes enabled IPv6." if not physical_enabled
                else f"{len(physical_enabled)} physical adapter(s) have IPv6 enabled; confirm no physical-uplink bypass.",
                "Adjust IPv6 only when it demonstrably bypasses the proxy; do not disable the tunnel adapter.")

        # Local DNS servers: flag physical-ISP IPv4 resolvers that could bypass the tunnel
        dns_servers = system.get("LocalDnsServers")
        if isinstance(dns_servers, list) and dns_servers:
            physical_ipv4 = []
            for entry in dns_servers:
                if not isinstance(entry, dict):
                    continue
                iface = str(entry.get("Interface", ""))
                # Skip tunnel/virtual/loopback interfaces; keep physical uplinks (WLAN, Ethernet, ????)
                if any(t in iface.lower() for t in ("sstap", "tun", "tap", "vpn", "openvpn", "virtual", "loopback", "hyper-v")):
                    continue
                family = entry.get("Family")
                servers = entry.get("Servers") or []
                if family in (2, "2", "ipv4") and servers:
                    for srv in servers:
                        if srv and not srv.startswith("127.") and not srv.startswith("198.18."):
                            physical_ipv4.append(f"{iface}:{srv}")
            if physical_ipv4:
                add("network.dns_physical_resolver", "Physical-ISP DNS resolver", "network",
                    "warning", "low",
                    f"Physical adapter DNS resolver(s) present: {', '.join(dict.fromkeys(physical_ipv4))}.",
                    "With fake-IP and port-53 hijacking active these are usually inert, but confirm a live test shows no physical-ISP resolver.")
            else:
                add("network.dns_physical_resolver", "Physical-ISP DNS resolver", "network",
                    "pass", "info",
                    "No physical-ISP IPv4 resolver observed; tunnel or loopback resolvers only.",
                    "")

        # Environment proxy variables (existence only — values are never revealed)
        env_proxies = system.get("ProxyEnvironmentVariables")
        if isinstance(env_proxies, list):
            present = sorted({p.get("Name") for p in env_proxies
                              if isinstance(p, dict) and p.get("Present")})
            if present:
                add("network.env_proxy", "Environment proxy variables", "network",
                    "unknown", "info",
                    f"Proxy environment variables present: {', '.join(present)}.",
                    "Explain whether each is intentional; values are never revealed.")
            else:
                add("network.env_proxy", "Environment proxy variables", "network",
                    "pass", "info",
                    "No proxy environment variables are set.",
                    "")

        # Windows locale consistency
        culture = system.get("Culture")
        ui_culture = system.get("UICulture")
        sys_locale = system.get("SystemLocale")
        langs = system.get("UserLanguageList")
        primary_lang = langs[0] if isinstance(langs, list) and langs else None
        locale_set = {c for c in (culture, ui_culture, sys_locale) if c}
        mismatches = []
        if len(locale_set) > 1:
            mismatches.append("Culture/UICulture/SystemLocale differ")
        if primary_lang and culture and not primary_lang.lower().startswith(culture.split("-")[0].lower()):
            mismatches.append("primary user language differs from culture")
        if mismatches:
            add("system.locale", "Windows locale consistency", "system",
                "warning", "info",
                "; ".join(mismatches) + ".",
                "Only change values that reflect genuine long-term use.")
        elif locale_set:
            add("system.locale", "Windows locale consistency", "system",
                "pass", "info",
                f"Locale is consistent (culture {culture}).",
                "")
        else:
            add("system.locale", "Windows locale consistency", "system",
                "unknown", "info",
                "Locale information is incomplete.",
                "")

    mihomo = data.get("Mihomo")
    if not isinstance(mihomo, dict) or not (mihomo.get("AppConfigPresent") or mihomo.get("RuntimeConfigPresent")):
        add("network.mihomo", "Mihomo configuration", "network", "unknown", "info", "No Mihomo runtime configuration was available for automatic interpretation.")
        return checks

    expected = [
        ("Mode", "Rule", "network.mode", "Rule mode"),
        ("AllowLan", False, "network.allow_lan", "LAN access disabled"),
        ("TunEnabled", True, "network.tun", "TUN enabled"),
        ("StrictRoute", True, "network.strict_route", "Strict routing enabled"),
        ("DnsEnabled", True, "network.dns", "Mihomo DNS enabled"),
        ("DnsMode", "fake-ip", "network.dns_mode", "Fake-IP DNS mode"),
        ("DnsHijackAny53", True, "network.dns_hijack", "DNS port 53 hijacking"),
    ]
    for key, wanted, check_id, title in expected:
        value = mihomo.get(key)
        matches = str(value).lower() == str(wanted).lower() if value is not None else None
        status = "pass" if matches else "unknown" if matches is None else "warning"
        add(
            check_id,
            title,
            "network",
            status,
            "info" if status != "warning" else "low",
            f"Observed {key}={value!r}." if value is not None else f"{key} requires manual confirmation.",
            "Confirm the setting in the active proxy client before changing it.",
        )

    # DNS respect-rules: must be enabled so fake-IP resolution honors rule routing
    respect_rules = mihomo.get("DnsRespectRules")
    if respect_rules is not None:
        status = "pass" if respect_rules else "warning"
        add("network.dns_respect_rules", "DNS respect-rules", "network", status,
            "info" if status == "pass" else "low",
            f"Observed DnsRespectRules={respect_rules!r}.",
            "Enable respect-rules so DNS resolution follows rule routing instead of bypassing the proxy.")

    # DNS IPv6: report consistency with the IPv6 toggle, do not judge alone
    dns_ipv6 = mihomo.get("DnsIPv6")
    ipv6 = mihomo.get("IPv6")
    if dns_ipv6 is not None:
        consistent = (dns_ipv6 == ipv6) if ipv6 is not None else None
        status = "pass" if consistent else "unknown" if consistent is None else "warning"
        add("network.dns_ipv6", "DNS IPv6 consistency", "network", status,
            "info" if status != "warning" else "low",
            f"Observed DnsIPv6={dns_ipv6!r}, IPv6={ipv6!r}."
            if ipv6 is not None else f"Observed DnsIPv6={dns_ipv6!r}.",
            "Confirm whether IPv6 DNS resolution is intended given the IPv6 routing toggle.")

    # Encrypted DNS upstreams: presence of DoH/DoT upstreams
    upstreams = mihomo.get("EncryptedDnsUpstreams")
    if upstreams is not None:
        hosts = sorted({u.get("Host", "") for u in upstreams if isinstance(u, dict) and u.get("Host")})
        status = "pass" if hosts else "warning"
        add("network.dns_encrypted", "Encrypted DNS upstreams", "network", status,
            "info" if status == "pass" else "low",
            f"Encrypted upstreams present: {', '.join(hosts)}." if hosts
            else "No encrypted DNS upstreams are configured.",
            "Prefer DoH/DoT upstreams so DNS lookups stay encrypted and consistent with the exit.")

    # TUN stack: informational, note non-gvisor stacks
    tun_stack = mihomo.get("TunStack")
    if tun_stack is not None:
        recommended = str(tun_stack).lower() == "gvisor"
        add("network.tun_stack", "TUN stack", "network",
            "pass" if recommended else "info",
            "info",
            f"Observed TunStack={tun_stack!r}.",
            "gvisor is the commonly proven stack on Windows; other stacks may still work but warrant verification.")

    # Policy group: no automatic selectors in the selection chain
    policy = mihomo.get("PolicyGroups")
    if isinstance(policy, dict):
        runtime_groups = policy.get("RuntimeGroups")
        assessment = policy.get("SelectionAssessment")
        if isinstance(runtime_groups, list) and runtime_groups:
            auto = [g for g in runtime_groups
                    if isinstance(g, dict) and g.get("UsesAutomaticSelection")]
            chain_auto = []
            for g in runtime_groups:
                if not isinstance(g, dict):
                    continue
                chain = g.get("SelectionChain") or []
                for link in chain:
                    if not isinstance(link, dict):
                        continue
                    ltype = str(link.get("Type", "")).lower()
                    if ltype in ("url-test", "fallback", "load-balance", "smart", "urltest"):
                        chain_auto.append(f"{g.get('Name', '?')}->{link.get('Name', '?')}({link.get('Type')})")
            fixed = assessment == "FixedSelection"
            status = "pass" if (fixed and not auto and not chain_auto) else "warning"
            explanation = f"Policy selection is fixed ({assessment!r}) with no automatic selectors."
            if auto or chain_auto:
                explanation = f"Automatic selector(s) present: {', '.join(chain_auto or [a.get('Name', '?') for a in auto])}."
            add("network.policy_group", "Policy group selection", "network", status,
                "info" if status == "pass" else "low",
                explanation,
                "Pin the sensitive service group to a fixed manual selection; automatic selectors can change the exit unpredictably.")
        else:
            add("network.policy_group", "Policy group selection", "network", "unknown", "info",
                "Policy group runtime selection is unavailable; verify the selected group in the Clash Verge UI.")

    return checks


def summarize(checks):
    """Count checks by severity. Returns a dict with the standard keys."""
    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for check in checks:
        summary[check.severity] = summary.get(check.severity, 0) + 1
    return summary


def run_full_audit(probe_timeout=5, include_recommendations=False):
    """One-call audit: run the collector, redact, analyze, and run online probes.

    Returns a dict with ``checks`` (list[AuditCheck], local analysis first,
    then probe results), ``summary`` (severity counts), and ``snapshot``
    (redacted collector JSON for the agent's report context).

    Online probes contact public endpoints to observe egress; callers
    should present that tradeoff before invoking this when interactive.
    """
    from .redaction import Redactor
    from .probes.base import run_probes

    snapshot = run_legacy_collector()
    redacted = Redactor().scan_and_redact(snapshot)
    checks = analyze_snapshot(redacted, include_recommendations=include_recommendations)
    try:
        probe_results = run_probes(None, timeout=probe_timeout)
        checks.extend(probe_results)
    except Exception as exc:  # probes are best-effort; never fail the audit
        checks.append(AuditCheck(
            id="network.egress.probe_error",
            title="Online probe failure",
            category="network",
            status="unknown",
            severity="info",
            confidence="unknown",
            explanation=f"Online probes could not run: {exc}",
        ))
    return {
        "checks": checks,
        "summary": summarize(checks),
        "snapshot": redacted,
    }
