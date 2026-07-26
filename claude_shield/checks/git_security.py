import subprocess
from pathlib import Path
from ..models import AuditCheck, Evidence

def run_git_security_check(workspace: str, history_depth: int = 0) -> AuditCheck:
    findings = []
    status = "pass"
    severity = "info"
    
    workspace_path = Path(workspace).resolve()
    git_dir = workspace_path / '.git'
    
    if not git_dir.exists():
        return AuditCheck(
            id="security.git.config",
            title="Git Security Configuration",
            category="security",
            status="skipped",
            severity="info",
            confidence="confirmed",
            explanation="Not a Git repository."
        )
        
    # Check .gitignore
    gitignore = workspace_path / '.gitignore'
    if not gitignore.exists():
        findings.append({"issue": "Missing .gitignore", "risk": "medium"})
        status = "warning"
        severity = "medium"
    else:
        content = gitignore.read_text(encoding='utf-8', errors='ignore')
        if '.env' not in content:
            findings.append({"issue": ".env not in .gitignore", "risk": "medium"})
            status = "warning"
            severity = "medium"
            
    # Set safe git env
    import os
    env = os.environ.copy()
    env['GIT_PAGER'] = 'cat'
    env['PAGER'] = 'cat'
    env['GIT_EXTERNAL_DIFF'] = ''
    env['GIT_TERMINAL_PROMPT'] = '0'

    # Check staged files for credentials (lightweight)
    try:
        result = subprocess.run(
            ['git', '--no-pager', 'diff', '--no-ext-diff', '--cached', '-G', '(?i)(api_key|password|secret|token)', '--'],
            capture_output=True,
            text=True,
            cwd=workspace,
            env=env,
            timeout=5
        )
        # Limit string length processed
        if result.stdout.strip()[:1024]:
            findings.append({"issue": "Staged files contain suspected secrets", "risk": "high"})
            status = "fail"
            severity = "high"
    except Exception:
        pass
        
    # Check history if requested
    if history_depth > 0:
        try:
            result = subprocess.run(
                ['git', '--no-pager', 'log', f'-n{history_depth}', '--no-ext-diff', '-p', '-G', '(?i)(api_key|password|secret|token)', '--'],
                capture_output=True,
                text=True,
                cwd=workspace,
                env=env,
                timeout=10
            )
            # Limit string length processed
            if result.stdout.strip()[:1024]:
                findings.append({"issue": f"Secrets suspected in recent {history_depth} commits", "risk": "high"})
                status = "fail"
                severity = "high"
        except Exception:
            pass

    explanation = "Git configuration appears safe."
    if findings:
        explanation = f"Found {len(findings)} Git security issues."

    evidence = [Evidence(type="git_issue", description=f['issue'], data=f) for f in findings]
    
    return AuditCheck(
        id="security.git.config",
        title="Git Security Configuration",
        category="security",
        status=status,
        severity=severity,
        confidence="possible" if findings else "confirmed",
        evidence=evidence,
        explanation=explanation
    )
