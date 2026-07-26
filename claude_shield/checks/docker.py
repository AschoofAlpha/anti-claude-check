import subprocess
import json
from ..models import AuditCheck, Evidence

def check_docker() -> AuditCheck:
    status = "skipped"
    severity = "info"
    explanation = "Docker CLI not found or daemon not running."
    evidence = []
    
    try:
        result = subprocess.run(['docker', 'info', '--format', '{{json .}}'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            status = "pass"
            explanation = "Docker daemon is accessible."
            try:
                info = json.loads(result.stdout)
                evidence.append(Evidence(type="docker_info", description="Docker system info", data={
                    "ContainersRunning": info.get("ContainersRunning"),
                    "ContainersTotal": info.get("Containers"),
                    "ServerVersion": info.get("ServerVersion"),
                    "OperatingSystem": info.get("OperatingSystem"),
                    "Architecture": info.get("Architecture"),
                    "HTTPProxy": bool(info.get("HttpProxy")),
                    "HTTPSProxy": bool(info.get("HttpsProxy"))
                }))
            except json.JSONDecodeError:
                pass
                
            # Check context
            ctx_res = subprocess.run(['docker', 'context', 'ls', '--format', '{{json .}}'], capture_output=True, text=True, timeout=5)
            if ctx_res.returncode == 0:
                contexts = []
                import hashlib
                from ..redaction import Redactor
                redactor = Redactor()
                for line in ctx_res.stdout.splitlines():
                    try:
                        ctx_info = json.loads(line)
                        raw_name = ctx_info.get("Name", "")
                        safe_name = raw_name if raw_name == "default" else f"custom_{hashlib.md5(raw_name.encode()).hexdigest()[:8]}"
                        contexts.append({
                            "Name": safe_name,
                            "Current": ctx_info.get("Current", False),
                            "DockerEndpoint": "unix://redacted" if "unix://" in ctx_info.get("DockerEndpoint", "") else "tcp://redacted"
                        })
                    except json.JSONDecodeError:
                        pass
                evidence.append(Evidence(type="docker_contexts", description="Docker contexts", data=contexts))
                
    except Exception:
        pass
        
    return AuditCheck(
        id="virtualization.docker",
        title="Docker Environment Observation",
        category="system",
        status=status,
        severity=severity,
        confidence="confirmed",
        evidence=evidence,
        explanation=explanation
    )
