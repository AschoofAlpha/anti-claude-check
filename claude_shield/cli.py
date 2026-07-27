import argparse
import json
import datetime
import subprocess
import sys
import os
import shutil
from pathlib import Path

from .remediation.planner import generate_plan, print_dry_run
from .remediation.transaction import Transaction, TransactionError
from .remediation.rollback import perform_rollback
from .redaction import Redactor
from .models import AuditReport, PlatformInfo, PrivacyMetadata, AuditCheck, ToolError
from .schema import validate_report, SchemaValidationError, SUPPORTED_MAJOR_VERSION
from .reporting import render_terminal, render_json, render_markdown
from . import __version__
from .resources import resource_path

EXIT_SUCCESS = 0
EXIT_MEDIUM_RISK = 1
EXIT_HIGH_RISK = 2
EXIT_USAGE_ERROR = 3
EXIT_COLLECTOR_FAILED = 4
EXIT_SCHEMA_ERROR = 5
EXIT_PERMISSION_ERROR = 6
EXIT_TX_ERROR = 7

def run_legacy_collector(timeout=30):
    try:
        if os.name == "nt":
            script_path = resource_path("scripts", "collect_windows_network.ps1")
            executable = shutil.which("pwsh") or shutil.which("powershell.exe")
            if not executable:
                raise RuntimeError("PowerShell is not available.")
            command = [executable, "-NoProfile", "-File", str(script_path)]
        else:
            script_path = resource_path("scripts", "collect_posix_network.sh")
            executable = shutil.which("bash")
            if not executable:
                raise RuntimeError("bash is not available.")
            command = [executable, str(script_path)]

        result = subprocess.run(command, capture_output=True, timeout=timeout)
        if result.returncode != 0:
            error = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"collector exited with code {result.returncode}: {error}")
        stdout = result.stdout.decode("utf-8-sig", errors="replace")
        start = stdout.find("{")
        if start < 0:
            raise RuntimeError("collector returned no JSON object")
        return json.loads(stdout[start:])
    except (FileNotFoundError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print(f"Collector failed: {exc}", file=sys.stderr)
        sys.exit(EXIT_COLLECTOR_FAILED)


def _collector_checks(data, include_recommendations=False):
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

def cmd_audit(args):
    if args.online and args.offline:
        print("Error: --online and --offline are mutually exclusive.", file=sys.stderr)
        sys.exit(EXIT_USAGE_ERROR)

    if getattr(args, "deep", False):
        args.credentials = args.git = args.wsl = args.docker = True

    raw_data = run_legacy_collector()
    redactor = Redactor()
    redacted_data = redactor.scan_and_redact(raw_data)
    checks = _collector_checks(redacted_data, getattr(args, "suggest_remediation", False))

    if args.online and not args.yes:
        if not sys.stdout.isatty():
            print("Online probes require --yes in non-interactive environments.", file=sys.stderr)
            sys.exit(EXIT_USAGE_ERROR)
        print("WARNING: Online probes will access external endpoints to observe network egress.")
        print("Information sent: Anti Claude Check sends a minimal HTTPS request to an explicitly listed endpoint to observe connectivity and egress behavior. It does not upload local diagnostic reports, configuration files, credentials, or raw system information.")
        ans = input("Proceed with online probes? [y/N]: ")
        if ans.lower() != 'y':
            print("Aborted.")
            sys.exit(EXIT_USAGE_ERROR)

    if args.online:
        from .probes.base import run_probes
        probe_results = run_probes(args.probe_endpoint, args.probe_timeout)
        for p in probe_results:
            checks.append(p)
                
    if args.credentials:
        from .checks.credentials import run_credential_scan
        cred_check = run_credential_scan(os.getcwd())
        checks.append(cred_check)
            
    if getattr(args, 'git', False) or getattr(args, 'git_history_depth', 0) > 0:
        from .checks.git_security import run_git_security_check
        git_check = run_git_security_check(os.getcwd(), getattr(args, 'git_history_depth', 0))
        checks.append(git_check)
            
    if getattr(args, 'wsl', False):
        from .checks.wsl import check_wsl
        wsl_check = check_wsl()
        checks.append(wsl_check)
            
    if getattr(args, 'docker', False):
        from .checks.docker import check_docker
        dock_check = check_docker()
        checks.append(dock_check)
            
    browser_score = None
    browser_score_categories = {}
    if getattr(args, 'browser_report', None):
        from .browser_import import import_browser_report
        try:
            b_report = import_browser_report(args.browser_report)
            checks.extend(b_report.checks)
            browser_score = b_report.score
            browser_score_categories = b_report.score_categories
        except Exception as e:
            print(f"Browser report import failed: {e}", file=sys.stderr)
            sys.exit(EXIT_USAGE_ERROR)
            
    summary = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
    for check in checks:
        summary[check.severity] += 1
    system = redacted_data.get("System", {})
    hostname = system.get("Hostname", system.get("HostName", "unknown"))
    report = AuditReport(
        schema_version=f"{SUPPORTED_MAJOR_VERSION}.0.0",
        tool_version=__version__,
        generated_at=datetime.datetime.utcnow().isoformat() + "Z",
        platform=PlatformInfo(os=os.name, version="unknown", hostname=hostname),
        privacy=PrivacyMetadata(redaction_enabled=True, salt_used=True),
        checks=checks,
        summary=summary,
        errors=[],
        score=browser_score,
        score_categories=browser_score_categories,
    )

    report_dict = render_json(report)
    try:
        validate_report(json.loads(report_dict))
    except SchemaValidationError as e:
        print(f"Report validation failed: {e}", file=sys.stderr)
        sys.exit(EXIT_SCHEMA_ERROR)
        
    if getattr(args, 'format', 'terminal') == 'json':
        print(report_dict)
    elif getattr(args, 'format', 'terminal') == 'markdown':
        print(render_markdown(report))
    else:
        render_terminal(report, getattr(args, "verbose", False))
        
    if summary['critical'] > 0 or summary['high'] > 0:
        sys.exit(EXIT_HIGH_RISK)
    elif summary['medium'] > 0:
        sys.exit(EXIT_MEDIUM_RISK)
    else:
        sys.exit(EXIT_SUCCESS)

def cmd_credentials(args):
    from .checks.credentials import run_credential_scan
    if args.cred_cmd == 'scan':
        path = args.path or os.getcwd()
        check = run_credential_scan(path)
        print(f"Status: {check.status}, Severity: {check.severity}")
        print(f"Explanation: {check.explanation}")
        for ev in check.evidence:
            print(f" - {ev.description}: {ev.data['path']}:{ev.data['line']} ({ev.data['risk']})")
    else:
        print("Invalid credentials command.")
        sys.exit(EXIT_USAGE_ERROR)
        
def cmd_browser(args):
    from .browser_import import import_browser_report
    if args.browser_cmd == 'import':
        try:
            report = import_browser_report(args.path)
            print(f"Imported report with {len(report.checks)} checks.")
            render_terminal(report)
        except Exception as e:
            print(f"Import failed: {e}", file=sys.stderr)
            sys.exit(EXIT_USAGE_ERROR)
    elif args.browser_cmd == 'profile':
        if not hasattr(args, 'profile_cmd') or not args.profile_cmd:
            print("Missing browser profile subcommand.")
            sys.exit(EXIT_USAGE_ERROR)
            
        if args.profile_cmd == 'create':
            from .browser.discovery import detect_browser
            from .browser.profile import create_profile
            info = detect_browser(getattr(args, 'browser_path', None))
            if not info['detected']:
                print("Could not find a safe Chrome/Chromium executable.", file=sys.stderr)
                sys.exit(EXIT_USAGE_ERROR)
            pid = create_profile(info)
            print(f"Created clean profile: {pid}")
            if getattr(args, 'launch', False):
                from .browser.launcher import launch_profile
                launch_profile(pid, getattr(args, 'browser_path', None), getattr(args, 'disable_extensions', False))
                print("Browser launched.")
                
        elif args.profile_cmd == 'list':
            from .browser.profile import list_profiles
            profiles = list_profiles()
            if not profiles:
                print("No profiles found.")
            else:
                for p in profiles:
                    in_use = " [IN USE]" if p['in_use'] else ""
                    print(f"- {p['profile_id']} (Status: {p['status']}){in_use}")
                    
        elif args.profile_cmd == 'inspect':
            from .browser.inspection import inspect_profile, calculate_risk
            try:
                report = inspect_profile(args.profile_id)
                risk = calculate_risk(report)
                print(f"Risk Level: {risk}")
                print(json.dumps(report, indent=2))
            except Exception as e:
                print(f"Inspect failed: {e}", file=sys.stderr)
                sys.exit(EXIT_USAGE_ERROR)
                
        elif args.profile_cmd == 'launch':
            from .browser.launcher import launch_profile
            try:
                launch_profile(args.profile_id, getattr(args, 'browser_path', None), getattr(args, 'disable_extensions', False))
                print("Browser launched.")
            except Exception as e:
                print(f"Launch failed: {e}", file=sys.stderr)
                sys.exit(EXIT_USAGE_ERROR)
                
        elif args.profile_cmd == 'reset':
            from .browser.profile import reset_profile
            try:
                # We should ask for confirmation if not --yes
                if not getattr(args, 'yes', False):
                    ans = input(f"Are you sure you want to reset profile {args.profile_id}? [y/N]: ")
                    if ans.lower() != 'y':
                        print("Aborted.")
                        sys.exit(0)
                old_path, new_id = reset_profile(args.profile_id)
                print(f"Profile reset. Old data quarantined to {old_path}")
            except Exception as e:
                print(f"Reset failed: {e}", file=sys.stderr)
                sys.exit(EXIT_USAGE_ERROR)
                
        elif args.profile_cmd == 'quarantine':
            from .browser.profile import quarantine_profile
            try:
                quarantine_profile(args.profile_id)
                print("Profile quarantined.")
            except Exception as e:
                print(f"Quarantine failed: {e}", file=sys.stderr)
                sys.exit(EXIT_USAGE_ERROR)
                
        elif args.profile_cmd == 'delete':
            # Phase 5A.5 specific: we alias delete to quarantine for now, or just implement basic quarantine
            from .browser.profile import quarantine_profile
            try:
                if not getattr(args, 'yes', False):
                    ans = input(f"Are you sure you want to delete profile {args.profile_id}? [y/N]: ")
                    if ans.lower() != 'y':
                        print("Aborted.")
                        sys.exit(0)
                quarantine_profile(args.profile_id)
                print("Profile deleted (moved to quarantine).")
            except Exception as e:
                print(f"Delete failed: {e}", file=sys.stderr)
                sys.exit(EXIT_USAGE_ERROR)
                
        elif args.profile_cmd == 'restore':
            try:
                Transaction(args.transaction_id).rollback()
                print(f"Transaction {args.transaction_id} rolled back successfully.")
            except TransactionError as e:
                print(f"Restore failed: {e}", file=sys.stderr)
                sys.exit(EXIT_TX_ERROR)
                
        elif args.profile_cmd == 'audit':
            from .browser.launcher import launch_profile
            import tempfile
            try:
                audit_html = resource_path("assets", "browser-audit.html").resolve()
                launch_profile(args.profile_id, getattr(args, 'browser_path', None), False, [audit_html.as_uri()])
                print("Browser launched for audit.")
            except Exception as e:
                print(f"Audit launch failed: {e}", file=sys.stderr)
                sys.exit(EXIT_USAGE_ERROR)
    else:
        print("Invalid browser command.")
        sys.exit(EXIT_USAGE_ERROR)

def cmd_doctor(args):
    print("Doctor: Checking environment...")
    print(f"Python: {sys.version}")
    print(f"Platform: {os.name}")
    sys.exit(EXIT_SUCCESS)

def cmd_explain(args):
    print(f"Explaining check: {args.check_id}")
    sys.exit(EXIT_SUCCESS)

def cmd_history(args):
    print("History:")
    tx_dir = Path.home() / '.claude-shield' / 'transactions'
    if tx_dir.exists():
        for tx in tx_dir.iterdir():
            print(f"- {tx.name}")
    sys.exit(EXIT_SUCCESS)

def cmd_remediate(args):
    if not hasattr(args, 'rem_cmd') or not args.rem_cmd:
        print("Missing remediate subcommand (plan, apply, verify)")
        sys.exit(EXIT_USAGE_ERROR)
        
    import json
    from .remediation.planner import generate_plan, print_dry_run
    from .remediation.transaction import Transaction
    
    if args.rem_cmd == 'plan':
        mock_checks = []
        if getattr(args, 'check', None):
            mock_checks.append({"risk_type": args.check, "target": getattr(args, 'workspace', '.gitignore')})
        else:
            mock_checks.append({"risk_type": "missing_gitignore", "target": ".gitignore"})
            
        plan = generate_plan(mock_checks)
        print_dry_run(plan, getattr(args, 'format', 'terminal'))
        
        if plan.get("actions"):
            if not getattr(args, 'dry_run', False):
                tx = Transaction()
                tx.save_plan(plan)
                print(f"\nSaved plan to transaction {tx.tx_id}")
                
    elif args.rem_cmd == 'apply':
        tx = Transaction(args.plan_id)
        plan = tx.load_plan()
        if not plan:
            print("No plan found in transaction.", file=sys.stderr)
            sys.exit(EXIT_USAGE_ERROR)
            
        if not getattr(args, 'yes', False):
            ans = input(f"Are you sure you want to apply plan {args.plan_id}? [y/N]: ")
            if ans.lower() != 'y':
                print("Aborted.")
                sys.exit(0)
        
        try:
            tx.apply(plan)
            print(f"Plan {args.plan_id} applied successfully.")
        except Exception as e:
            print(f"Apply failed: {e}", file=sys.stderr)
            sys.exit(EXIT_TX_ERROR)
            
    elif args.rem_cmd == 'verify':
        tx = Transaction(args.transaction_id)
        results = tx.verify()
        print(json.dumps(results, indent=2))
        
def cmd_rollback(args):
    from .remediation.transaction import Transaction
    tx = Transaction(args.transaction_id)
    try:
        tx.rollback()
        print(f"Transaction {args.transaction_id} rolled back successfully.")
    except Exception as e:
        print(f"Rollback failed: {e}", file=sys.stderr)
        sys.exit(EXIT_TX_ERROR)

def cmd_probes(args):
    from .probes.endpoints import get_all_endpoints
    if args.probes_cmd == 'list':
        for ep in get_all_endpoints():
            print(f"- {ep['id']}: {ep['url']} (IPv4: {ep['supports_ipv4']}, IPv6: {ep['supports_ipv6']})")
    elif args.probes_cmd == 'explain':
        for ep in get_all_endpoints():
            if ep['id'] == args.endpoint_id:
                print(f"Endpoint: {ep['id']}")
                print(f"URL: {ep['url']}")
                print(f"Purpose: {ep['purpose']}")
                print(f"IPv4 Support: {ep['supports_ipv4']}")
                print(f"IPv6 Support: {ep['supports_ipv6']}")
                sys.exit(0)
        print("Endpoint not found.")
        sys.exit(EXIT_USAGE_ERROR)
    else:
        print("Invalid probes command.")
        sys.exit(EXIT_USAGE_ERROR)

def main():
    parser = argparse.ArgumentParser(description="Anti Claude Check CLI")
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    subparsers = parser.add_subparsers(dest="command")
    
    audit_parser = subparsers.add_parser("audit", help="Run audit")
    audit_parser.add_argument("--deep", action="store_true")
    audit_parser.add_argument("--online", action="store_true")
    audit_parser.add_argument("--offline", action="store_true")
    audit_parser.add_argument("--yes", action="store_true", help="Skip online confirmation")
    audit_parser.add_argument("--probe-endpoint", type=str, help="Custom HTTPS endpoint")
    audit_parser.add_argument("--probe-timeout", type=int, default=5, help="Probe timeout in seconds")
    audit_parser.add_argument("--format", choices=["terminal", "json", "markdown"], default="terminal", help="Output format")
    audit_parser.add_argument("--suggest-remediation", action="store_true", help="Suggest remediation actions")
    audit_parser.add_argument("--verbose", action="store_true")
    
    audit_parser.add_argument("--credentials", action="store_true")
    audit_parser.add_argument("--git", action="store_true")
    audit_parser.add_argument("--git-history-depth", type=int, default=0)
    audit_parser.add_argument("--wsl", action="store_true")
    audit_parser.add_argument("--docker", action="store_true")
    audit_parser.add_argument("--browser-report", type=str)
    
    doctor_parser = subparsers.add_parser("doctor", help="Check environment")
    
    explain_parser = subparsers.add_parser("explain", help="Explain a specific check")
    explain_parser.add_argument("check_id")
    
    history_parser = subparsers.add_parser("history", help="Show remediation history")
    
    remediate_parser = subparsers.add_parser("remediate", help="Run remediation")
    rem_sub = remediate_parser.add_subparsers(dest="rem_cmd")
    
    plan_parser = rem_sub.add_parser("plan")
    plan_parser.add_argument("--check", type=str)
    plan_parser.add_argument("--workspace", type=str)
    plan_parser.add_argument("--format", type=str, choices=["terminal", "json"], default="terminal")
    plan_parser.add_argument("--dry-run", action="store_true")
    
    apply_parser = rem_sub.add_parser("apply")
    apply_parser.add_argument("plan_id", type=str)
    apply_parser.add_argument("--yes", action="store_true")
    
    verify_parser = rem_sub.add_parser("verify")
    verify_parser.add_argument("transaction_id", type=str)
    
    rollback_parser = subparsers.add_parser("rollback", help="Rollback a transaction")
    rollback_parser.add_argument("transaction_id", help="ID of transaction to rollback")
    
    probes_parser = subparsers.add_parser("probes", help="Manage online probes")
    probes_subparsers = probes_parser.add_subparsers(dest="probes_cmd")
    probes_subparsers.add_parser("list", help="List available probe endpoints")
    explain_probes = probes_subparsers.add_parser("explain", help="Explain a probe endpoint")
    explain_probes.add_argument("endpoint_id", type=str)
    
    cred_parser = subparsers.add_parser("credentials", help="Manage credentials")
    cred_sub = cred_parser.add_subparsers(dest="cred_cmd")
    cred_scan = cred_sub.add_parser("scan")
    cred_scan.add_argument("path", nargs="?", help="Path to scan")
    
    browser_parser = subparsers.add_parser("browser", help="Manage browser")
    browser_sub = browser_parser.add_subparsers(dest="browser_cmd")
    
    browser_imp = browser_sub.add_parser("import")
    browser_imp.add_argument("path", help="Path to JSON report")
    
    browser_prof = browser_sub.add_parser("profile")
    prof_sub = browser_prof.add_subparsers(dest="profile_cmd")
    
    prof_create = prof_sub.add_parser("create")
    prof_create.add_argument("--browser-path", type=str)
    prof_create.add_argument("--launch", action="store_true", help="Launch the profile after creation")
    prof_create.add_argument("--disable-extensions", action="store_true")
    
    prof_list = prof_sub.add_parser("list")
    
    prof_inspect = prof_sub.add_parser("inspect")
    prof_inspect.add_argument("profile_id", type=str)
    
    prof_launch = prof_sub.add_parser("launch")
    prof_launch.add_argument("profile_id", type=str)
    prof_launch.add_argument("--browser-path", type=str)
    prof_launch.add_argument("--disable-extensions", action="store_true")
    
    prof_audit = prof_sub.add_parser("audit")
    prof_audit.add_argument("profile_id", type=str)
    prof_audit.add_argument("--browser-path", type=str)
    
    prof_reset = prof_sub.add_parser("reset")
    prof_reset.add_argument("profile_id", type=str)
    prof_reset.add_argument("--yes", action="store_true")
    
    prof_quarantine = prof_sub.add_parser("quarantine")
    prof_quarantine.add_argument("profile_id", type=str)
    
    prof_delete = prof_sub.add_parser("delete")
    prof_delete.add_argument("profile_id", type=str)
    prof_delete.add_argument("--yes", action="store_true")
    
    prof_restore = prof_sub.add_parser("restore")
    prof_restore.add_argument("transaction_id", type=str)
    
    args = parser.parse_args()
    
    if getattr(args, 'version', False):
        import platform
        print(f"Anti Claude Check v{__version__}")
        print(f"Schema Version: {SUPPORTED_MAJOR_VERSION}.0.0")
        print(f"Python: {platform.python_version()}")
        print(f"Platform: {platform.system()} {platform.release()}")
        sys.exit(EXIT_SUCCESS)
    
    if args.command == "audit":
        cmd_audit(args)
    elif args.command == "doctor":
        cmd_doctor(args)
    elif args.command == "explain":
        cmd_explain(args)
    elif args.command == "history":
        cmd_history(args)
    elif args.command == "remediate":
        cmd_remediate(args)
    elif args.command == "rollback":
        cmd_rollback(args)
    elif args.command == "probes":
        cmd_probes(args)
    elif args.command == "credentials":
        cmd_credentials(args)
    elif args.command == "browser":
        cmd_browser(args)
    else:
        parser.print_help()
        sys.exit(EXIT_USAGE_ERROR)
