import json
from .models import AuditReport, to_dict

def render_terminal(report: AuditReport, show_evidence: bool = False):
    print("=== Anti Claude Check Audit Report ===")
    print(f"Generated At: {report.generated_at}")
    print(f"Platform: {report.platform.os} {report.platform.version}")
    
    if report.score is not None:
        print(f"Local Browser Score: {report.score}/100")
        for name, value in report.score_categories.items():
            print(f"  {name}: {'not scored' if value is None else f'{value}/100'}")

    summary = report.summary
    print("\n[ Summary ]")
    print(f"  Critical: {summary.get('critical', 0)}")
    print(f"  High:     {summary.get('high', 0)}")
    print(f"  Medium:   {summary.get('medium', 0)}")
    print(f"  Low:      {summary.get('low', 0)}")
    print(f"  Info:     {summary.get('info', 0)}")
    print(f"  Errors:   {len(report.errors)}")
    
    print("\n[ Findings ]")
    for check in report.checks:
        if check.status != 'pass' or check.severity in ('critical', 'high'):
            color = "\033[91m" if check.severity in ('critical', 'high') else "\033[93m"
            reset = "\033[0m"
            print(f"{color}[{check.severity.upper()}] {check.title}{reset}")
            print(f"  - Status: {check.status}")
            print(f"  - Explanation: {check.explanation}")
            if check.recommendation:
                print(f"  - Recommendation: {check.recommendation}")
            if show_evidence:
                for item in check.evidence:
                    print(f"  - Evidence: {item.description}: {item.data}")
    
    print("\n[ Privacy ]")
    print(f"  Redaction Enabled: {report.privacy.redaction_enabled}")

def render_json(report: AuditReport) -> str:
    # We dump it with sort_keys to ensure stability
    return json.dumps(to_dict(report), indent=2, sort_keys=True)

def render_markdown(report: AuditReport) -> str:
    lines = []
    lines.append("# Anti Claude Check Audit Report")
    lines.append(f"**Generated At**: {report.generated_at}")
    lines.append(f"**Tool Version**: {report.tool_version}")
    lines.append(f"**Schema Version**: {report.schema_version}")
    if report.score is not None:
        lines.append(f"**Local Browser Score**: {report.score}/100")
        for name, value in report.score_categories.items():
            lines.append(f"- {name}: {'not scored' if value is None else f'{value}/100'}")
    lines.append("")
    lines.append("## Platform")
    lines.append(f"- OS: {report.platform.os}")
    lines.append(f"- Version: {report.platform.version}")
    lines.append(f"- Hostname: {report.platform.hostname}")
    lines.append("")
    lines.append("## Privacy")
    lines.append(f"- Redaction Enabled: {report.privacy.redaction_enabled}")
    lines.append("")
    lines.append("## Summary")
    for k, v in report.summary.items():
        lines.append(f"- **{k.capitalize()}**: {v}")
    lines.append("")
    lines.append("## Checks")
    for check in report.checks:
        lines.append(f"### {check.title}")
        lines.append(f"- **Status**: {check.status}")
        lines.append(f"- **Severity**: {check.severity}")
        lines.append(f"- **Confidence**: {check.confidence}")
        if check.explanation:
            lines.append(f"- **Explanation**: {check.explanation}")
        if check.recommendation:
            lines.append(f"- **Recommendation**: {check.recommendation}")
        lines.append("")
    return "\n".join(lines)
