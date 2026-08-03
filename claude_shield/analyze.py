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
    return checks


def summarize(checks):
    """Count checks by severity. Returns a dict with the standard keys."""
    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for check in checks:
        summary[check.severity] = summary.get(check.severity, 0) + 1
    return summary
