import argparse
import json
import datetime
import subprocess
import sys
import os

from .remediation.planner import generate_plan, print_dry_run
from .remediation.transaction import Transaction, TransactionError
from .remediation.rollback import perform_rollback
from .redaction import Redactor
from .models import AuditReport, PlatformInfo, PrivacyMetadata, AuditCheck, ToolError
from .schema import validate_report, SchemaValidationError, SUPPORTED_MAJOR_VERSION
from .reporting import render_terminal, render_json, render_markdown
from . import __version__

EXIT_SUCCESS = 0
EXIT_MEDIUM_RISK = 1
EXIT_HIGH_RISK = 2
EXIT_USAGE_ERROR = 3
EXIT_COLLECTOR_FAILED = 4
EXIT_SCHEMA_ERROR = 5
EXIT_PERMISSION_ERROR = 6
EXIT_TX_ERROR = 7

def run_legacy_collector(timeout=30):
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'collect_windows_network.ps1'))
    if os.name == 'nt' and os.path.exists(script_path):
        try:
            result = subprocess.run(
                ['pwsh', '-NoProfile', '-File', script_path],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if result.returncode != 0:
                print(f"Collector failed with code {result.returncode}", file=sys.stderr)
                sys.exit(EXIT_COLLECTOR_FAILED)
            try:
                # Discard non-json lines before {
                stdout = result.stdout
                start = stdout.find('{')
                if start != -1:
                    stdout = stdout[start:]
                return json.loads(stdout)
            except json.JSONDecodeError:
                print("Collector returned invalid JSON", file=sys.stderr)
                sys.exit(EXIT_COLLECTOR_FAILED)
        except subprocess.TimeoutExpired:
            print("Collector timed out", file=sys.stderr)
            sys.exit(EXIT_COLLECTOR_FAILED)
    # Mock for posix right now
    return {"System": {"Hostname": "mock", "OSVersion": "mock"}}

def cmd_audit(args):
    raw_data = run_legacy_collector()
    
    redactor = Redactor()
    redacted_data = redactor.scan_and_redact(raw_data)
    
    # Process redacted_data to build our AuditReport model
    # Mocking check parsing for Phase 2
    checks = []
    summary = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
    
    # Example check
    has_telemetry = redacted_data.get('ClaudeCode', {}).get('DisableTelemetryActive', False)
    if has_telemetry:
        checks.append(AuditCheck(
            id="telemetry.active",
            title="Telemetry is active",
            category="privacy",
            status="fail",
            severity="medium",
            confidence="confirmed",
            explanation="Telemetry appears to be active."
        ))
        summary['medium'] += 1
    else:
        checks.append(AuditCheck(
            id="telemetry.active",
            title="Telemetry is active",
            category="privacy",
            status="pass",
            severity="info",
            confidence="confirmed"
        ))
        summary['info'] += 1
        
    hostname = redacted_data.get('System', {}).get('Hostname', 'unknown')
    
    report = AuditReport(
        schema_version=f"{SUPPORTED_MAJOR_VERSION}.0.0",
        tool_version=__version__,
        generated_at=datetime.datetime.utcnow().isoformat() + "Z",
        platform=PlatformInfo(os=os.name, version="unknown", hostname=hostname),
        privacy=PrivacyMetadata(redaction_enabled=True, salt_used=True),
        checks=checks,
        summary=summary,
        errors=[]
    )
    
    if args.online and args.offline:
        print("Error: --online and --offline are mutually exclusive.", file=sys.stderr)
        sys.exit(EXIT_USAGE_ERROR)

    if args.online and not args.yes:
        if not sys.stdout.isatty():
            print("Online probes require --yes in non-interactive environments.", file=sys.stderr)
            sys.exit(EXIT_USAGE_ERROR)
        print("WARNING: Online probes will access external endpoints to observe network egress.")
        print("Information sent: Claude Shield sends a minimal HTTPS request to an explicitly listed endpoint to observe connectivity and egress behavior. It does not upload local diagnostic reports, configuration files, credentials, or raw system information.")
        ans = input("Proceed with online probes? [y/N]: ")
        if ans.lower() != 'y':
            print("Aborted.")
            sys.exit(EXIT_USAGE_ERROR)

    if args.online:
        from .probes.base import run_probes
        probe_results = run_probes(args.probe_endpoint, args.probe_timeout)
        for p in probe_results:
            checks.append(p)
            if p.status == 'pass':
                summary['info'] += 1
            else:
                summary['medium'] += 1
                
    if args.credentials:
        from .checks.credentials import run_credential_scan
        cred_check = run_credential_scan(os.getcwd())
        checks.append(cred_check)
        if cred_check.severity in summary:
            summary[cred_check.severity] += 1
            
    if getattr(args, 'git', False) or getattr(args, 'git_history_depth', 0) > 0:
        from .checks.git_security import run_git_security_check
        git_check = run_git_security_check(os.getcwd(), getattr(args, 'git_history_depth', 0))
        checks.append(git_check)
        if git_check.severity in summary:
            summary[git_check.severity] += 1
            
    if getattr(args, 'wsl', False):
        from .checks.wsl import check_wsl
        wsl_check = check_wsl()
        checks.append(wsl_check)
        if wsl_check.severity in summary:
            summary[wsl_check.severity] += 1
            
    if getattr(args, 'docker', False):
        from .checks.docker import check_docker
        dock_check = check_docker()
        checks.append(dock_check)
        if dock_check.severity in summary:
            summary[dock_check.severity] += 1
            
    if getattr(args, 'browser_report', None):
        from .browser_import import import_browser_report
        try:
            b_report = import_browser_report(args.browser_report)
            for c in b_report.checks:
                checks.append(c)
                if c.severity in summary:
                    summary[c.severity] += 1
        except Exception as e:
            print(f"Browser report import failed: {e}", file=sys.stderr)
            sys.exit(EXIT_USAGE_ERROR)
            
    # Validate report before output
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
        render_terminal(report)
        
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
            if not getattr(args, 'no_launch', True):
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
            # Alias for transaction rollback
            try:
                perform_rollback(args.transaction_id)
            except TransactionError as e:
                print(f"Restore failed: {e}", file=sys.stderr)
                sys.exit(EXIT_TX_ERROR)
                
        elif args.profile_cmd == 'audit':
            from .browser.launcher import launch_profile
            import tempfile
            try:
                # Create a temporary dummy html file to open
                with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
                    f.write(b"<html><body><h1>Audit Mode</h1><p>Please perform browser checks manually.</p></body></html>")
                    audit_html = f.name
                    
                launch_profile(args.profile_id, getattr(args, 'browser_path', None), False, [f"file://{audit_html}"])
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
            tx = Transaction()
            tx.save_plan(plan)
            if not getattr(args, 'dry_run', False):
                print(f"\nSaved plan to transaction {tx.tx_id}")
            else:
                # If it's just a dry run, don't persist it. (But planner doesn't hurt to save.)
                pass
                
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
    parser = argparse.ArgumentParser(description="Claude Shield CLI")
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
    rollback_parser.add_argument("transaction_id", nargs="?", help="ID of transaction to rollback")
    
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
    prof_create.add_argument("--no-launch", action="store_true")
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
        print(f"Claude Shield v{__version__}")
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
