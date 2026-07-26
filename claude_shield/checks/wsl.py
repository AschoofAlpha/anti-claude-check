import subprocess
from ..models import AuditCheck, Evidence

def check_wsl() -> AuditCheck:
    status = "skipped"
    severity = "info"
    explanation = "WSL is not installed or not responding."
    evidence = []
    
    try:
        result = subprocess.run(['wsl.exe', '-l', '-v'], capture_output=True, timeout=5)
        if result.returncode == 0:
            status = "pass"
            explanation = "WSL is installed. No active distributions found."
            
            # WSL outputs UTF-16LE
            text = result.stdout.decode('utf-16le', errors='ignore').strip()
            lines = text.splitlines()[1:] # Skip header
            distros = []
            running = False
            for line in lines:
                if not line.strip():
                    continue
                # Split by 2 or more spaces to handle spaces in names
                import re
                parts = re.split(r'\s{2,}', line.strip())
                if len(parts) >= 3:
                    is_default = line.startswith('*')
                    name = parts[0].strip('* ')
                    state = parts[1].strip()
                    version = parts[2].strip()
                    
                    distros.append({"state": state, "version": version, "is_default": is_default})
                    if state.lower() == "running":
                        running = True
                        
            if distros:
                versions_detected = list(set(d['version'] for d in distros))
                running_count = sum(1 for d in distros if d['state'].lower() == 'running')
                evidence.append(Evidence(type="wsl_info", description="WSL environment summary", data={
                    "installed": True,
                    "distribution_count": len(distros),
                    "running_distribution_count": running_count,
                    "versions_detected": versions_detected
                }))
                if running:
                    explanation = "WSL is installed and has running distributions."
                else:
                    explanation = "WSL is installed but no distributions are running."
    except Exception:
        pass
        
    return AuditCheck(
        id="virtualization.wsl",
        title="WSL Environment Observation",
        category="system",
        status=status,
        severity=severity,
        confidence="confirmed",
        evidence=evidence,
        explanation=explanation
    )
